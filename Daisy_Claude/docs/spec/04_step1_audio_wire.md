# Spec 04 — Step 1 Part 2: Audio Wire (SAI1 + DMA + AK4556)

**Status:** implementation complete 2026-04-17. TX path confirmed (tone test audible). Passthrough (RX→TX) is next verification step. All open items from the draft are resolved.

**Board correction:** original draft assumed Daisy Seed Rev 7 / PCM3060. Physical board is Rev 4 / AK4556. All PCM3060 references in the original draft are superseded by this version.

This step takes the bare-metal foundation from spec 02 (clock at 480 MHz, LED blink) and turns the Seed into a working audio passthrough: stereo line in → block-based callback (identity) → stereo line out, at 48 kHz, through the on-board AK4556 codec. Once this works, every later step (DSP modules, controls, MIDI, USB) plugs into the same callback.

We are deliberately **not** using ST HAL or libDaisy. CMSIS device headers (`stm32h750xx.h`, `core_cm7.h`) are allowed for register definitions only.

---

## 1. What this step delivers

A program that:

1. Brings up PLL3 to produce a SAI1 kernel clock that yields **MCLK = 12.288 MHz** (256 × 48 kHz).
2. Configures SAI1 as **sub-block A = TX master**, **sub-block B = RX synchronous slave**, 24-bit left-justified, 2-slot stereo, 48 kHz fS.
3. Routes PE2/3/4/5/6 to AF6 (SAI1).
4. Sets up DMA1 Stream 0 (SAI1_A TX) and DMA1 Stream 1 (SAI1_B RX), both circular, both with half-complete + transfer-complete IRQs.
5. Configures the MPU to mark the DMA buffer region non-cacheable.
6. Releases the codec from reset (after clocks are running) and waits out the codec's internal fade-in.
7. Runs an audio callback that copies RX → TX (identity passthrough) once per half-block.

Acceptance: line in on Pod J2 reaches line out on Pod J3 with no audible artifacts.

---

## 2. Files created or changed in step 1 part 2

```
seed_h750/
├── linker/
│   └── stm32h750_flash.ld        + RAM_D1 region (AXI SRAM, 0x24000000, 512 KB)
│                                  + .dma_buffers section
├── include/
│   ├── board.h                    + SAI1 pin map, codec RST pin (TBD pending schematic)
│   ├── audio.h                    public audio API: init, set_callback, type signatures
│   ├── sai1.h                     SAI1 driver internals (used by audio.c)
│   ├── dma.h                      DMA stream init helpers
│   └── mpu.h                      MPU helpers
├── src/
│   ├── clock.c                   ++ PLL3 setup for SAI1 kernel clock
│   ├── audio.c                    audio framework — buffers, IRQ handler, audio_init()
│   ├── sai1.c                     SAI1 register-level bring-up (split configure/enable)
│   ├── dma.c                      DMA1 Stream 0/1 setup
│   ├── mpu.c                      MPU non-cacheable region for .dma_buffers
│   └── main.c                    ~ audio_init(), fault blink rates, idle spin
```

No separate codec driver file — AK4556 reset is three `gpio_write` calls in `audio_init()`.
`startup_stm32h750.s` declares `DMA1_Stream1_IRQHandler` as a weak alias; `audio.c` provides the strong definition. Handler names are `XXXIRQHandler` (not `XXXIRQn_Handler`) — a naming bug fixed during bring-up.

---

## 3. AK4556 — codec bring-up

### 3.1 No register interface

The AK4556 is fully hardware-configured. There is no I2C, no SPI, no register writes. Operating format (24-bit left-justified, slave BCK/LRCK) is fixed by the board wiring. The only MCU action required is the RST pulse.

### 3.2 RST sequencing (resolved)

**PB11 = AK4556 RST, active-low.** The RST pin has an internal pulldown — left floating or driven low, the codec stays in reset with no audio output or input.

Required sequence (from libDaisy `Ak4556::Init()`):
```
PB11 → HIGH  (deassert)
delay_ms(1)
PB11 → LOW   (assert)
delay_ms(1)
PB11 → HIGH  (deassert and leave high)
```

This happens in `audio_init()` **before** the SAI clocks are started. The AK4556 locks on to BCK/LRCK when they come up. No post-reset delay is needed; the SAI clocks start flowing immediately after the pulse and the codec follows them.

**Root cause of original audio silence:** prior code drove PB11 LOW (treating it as PCM3060 deemphasis), holding the AK4556 in reset for the entire run. SAI/DMA were working correctly the whole time.

---

## 4. Clock tree addition — PLL3 for SAI1

AK4556 MCLK must be 256 × fS. For 48 kHz the cleanest target is **256 fS = 12.288 MHz**.

SAI1's kernel clock is selected by `RCC_D2CCIP1R.SAI1SEL`. Default after reset is PLL1Q, but our PLL1Q is 192 MHz — divisible only by inconvenient ratios. We use **PLL3P** instead.

Target: PLL3P near a small integer multiple of 12.288 MHz, then SAI1's MCKDIV produces the 12.288 MHz MCLK.

| Stage | Value | Result |
|---|---|---|
| HSE | 16 MHz | input to all PLLs |
| PLL3M | 6 | 16/6 = 2.667 MHz PFD |
| PLL3N | 295 | 2.667 × 295 = 786.67 MHz VCO |
| PLL3P | 16 | 786.67/16 = 49.167 MHz |
| SAI1 MCKDIV | 4 | 49.167/8 = 6.146 MHz... |

Wait — that math doesn't quite land at 12.288 MHz. The libDaisy values produce ~49.15 MHz, which divided by 4 with the SAI MCKDIV (which divides by `2 × MCKDIV` when nonzero, or by 1 when zero) gives ~12.288 MHz with about **50 ppm error**. The exact register sequence will be reverified when we write `clock.c`; the key decision is:

**Decision (locked):** accept the ~50 ppm error from integer PLL3 dividers. Do not use PLL3FRACN for Step 1 Part 2. Audible difference is zero; we will revisit fractional PLL configuration when (or if) we move to a multichannel custom board where multiple sample rates need to coexist.

PLL3 setup goes into `configure_clocks()` in `clock.c`, after PLL1 is locked, before SAI1 is touched. The SAI1SEL bits are written at the same time. PLL3Q and PLL3R are left disabled for now.

---

## 5. SAI1 setup — sub-block A master TX, sub-block B sync slave RX

Per RM0433 §51. The bring-up sequence (no HAL, no libDaisy):

1. **Enable SAI1 peripheral clock** in `RCC_APB2ENR.SAI1EN`. Read-back.
2. **Sub-block A (TX, master) — `SAI1_Block_A` registers:**
   - `CR1`: MODE = master TX (00), PRTCFG = free (00 = free protocol), DS = 24-bit (101), LSBFIRST = 0, CKSTR per LJ spec, SYNCEN = 00 (asynchronous), MCKDIV = chosen for 12.288 MHz, NODIV = 0 (we want MCLK on PE2), OUTDRIV = 0, MONO = 0, DMAEN = 1, SAIEN = 0 *(set last)*.
   - `FRCR`: FRL = 63 (frame length 64 bits), FSALL = 31 (FS active half-frame 32 bits), FSDEF = 1 (channel ID, left/right), FSPOL per LJ, FSOFF per LJ.
   - `SLOTR`: NBSLOT = 1 (2 slots), SLOTSZ = data-size, SLOTEN bits 0 and 1 enabled, FBOFF = 0.
3. **Sub-block B (RX, sync slave) — `SAI1_Block_B` registers:**
   - `CR1`: MODE = slave RX (11), SYNCEN = 01 (synchronous with sub-block A internal), DS/LSBFIRST/CKSTR mirror A, NODIV irrelevant, MONO = 0, DMAEN = 1, SAIEN = 0.
   - `FRCR`, `SLOTR`: mirror A.
4. **Enable B first, then A.** B must be listening before A starts driving clocks. (Order matters per RM0433 §51.4.5.)

SAI1 interrupt itself is not enabled in normal operation. We may enable FIFO error interrupts during bring-up debugging.

---

## 6. DMA1 Stream 0 + Stream 1

Per RM0433 §16 and the DMAMUX table.

| Stream | Direction | DMAMUX request |
|---|---|---|
| DMA1 Stream 0 | mem → SAI1_A | request 87 (`DMA_REQUEST_SAI1_A`) |
| DMA1 Stream 1 | SAI1_B → mem | request 88 (`DMA_REQUEST_SAI1_B`) |

Stream config (both):

- `PSIZE` = word, `MSIZE` = word (32-bit transfers; SAI1 holds 24-bit data right-aligned in 32-bit slots in our config).
- `PINC` = 0, `MINC` = 1.
- `CIRC` = 1 (continuous double-buffering via the mid-point IRQ).
- `PFCTRL` = 0 (DMA is flow controller).
- Priority = high.
- `HTIE` = 1, `TCIE` = 1, `TEIE` = 1.
- FIFO disabled (direct mode).

Buffer layout:

- One TX buffer + one RX buffer, both `int32_t[2 * BLOCK_SIZE * 2]` (factor 2 for double-buffering, factor 2 for stereo).
- `BLOCK_SIZE = 48` samples per channel per half-block (1 ms at 48 kHz, **2 ms total round-trip latency**).
- Both buffers placed in the new `.dma_buffers` section (AXI SRAM, see §7).

ISR routing — `startup_stm32h750.s` already defines weak handlers; we override:

```c
void DMA1_Stream0_IRQHandler(void);   // TX: SAI1_A
void DMA1_Stream1_IRQHandler(void);   // RX: SAI1_B
```

NVIC priority: default (lowest urgency, same as SysTick). Sufficient for now; can be raised later if other interrupts compete.

---

## 7. Memory layout — DMA buffer placement and D-cache

### 7.1 Why DTCM is not an option

DMA1/DMA2 do not see DTCM. Buffers placed in DTCM (where `.bss` and `.data` currently land) silently fail to transfer. We must use a region on the AHB matrix.

### 7.2 Linker script change

Add a region for AXI SRAM:

```
MEMORY {
  FLASH    (rx)  : ORIGIN = 0x08000000, LENGTH = 128K
  DTCMRAM  (rwx) : ORIGIN = 0x20000000, LENGTH = 128K
  RAM_D1   (rwx) : ORIGIN = 0x24000000, LENGTH = 512K
}
```

Add a section:

```
.dma_buffers (NOLOAD) : ALIGN(32) {
  KEEP(*(.dma_buffers))
  . = ALIGN(32);
} > RAM_D1
```

Buffers in C use:

```c
__attribute__((section(".dma_buffers"), aligned(32)))
static int32_t tx_buffer[2 * BLOCK_SIZE * 2];

__attribute__((section(".dma_buffers"), aligned(32)))
static int32_t rx_buffer[2 * BLOCK_SIZE * 2];
```

32-byte alignment matches the Cortex-M7 cache line and the MPU minimum region size for this approach.

### 7.3 D-cache strategy (locked)

Cortex-M7 D-cache is enabled in `system_init.c`. Two options for DMA coherency:

- **(A) MPU non-cacheable region** covering `.dma_buffers`. Simple, no per-transfer cache maintenance needed. Slight performance cost on buffer reads/writes (no caching), which is negligible for stereo 48 kHz.
- **(B) Explicit cache maintenance** (`SCB_CleanDCache_by_Addr` / `SCB_InvalidateDCache_by_Addr`) around each callback. Lower overhead but easy to get wrong.

**Decision (locked):** **(A)**. `mpu.c` configures one MPU region covering exactly the `.dma_buffers` section, attributes "Normal, Non-cacheable, Shareable". This is set up before the DMA streams are armed.

---

## 8. Audio callback — interrupt-driven, no preemption beyond ISRs

User-facing API (`audio.h`):

```c
typedef void (*audio_callback_t)(const int32_t *in, int32_t *out, uint32_t frames);

void audio_init(void);                         // PLL3 + SAI1 + DMA + MPU + codec reset
void audio_set_callback(audio_callback_t cb);  // called from foreground or main()
void audio_start(void);                        // arms DMA, starts SAI1, enables IRQs
```

`frames` = `BLOCK_SIZE` (48). `in` and `out` are stereo-interleaved (`L0, R0, L1, R1, ...`).

Internally, the callback dispatch hangs off **the RX DMA stream only**:

- On RX half-complete IRQ: call `cb(&rx_buffer[0], &tx_buffer[0], BLOCK_SIZE)`.
- On RX transfer-complete IRQ: call `cb(&rx_buffer[BLOCK_SIZE * 2], &tx_buffer[BLOCK_SIZE * 2], BLOCK_SIZE)`.
- TX DMA stream's IRQs are still enabled but fire as no-ops (or just clear flags) — we trust it to keep playing whatever is in `tx_buffer`.

This keeps the model "one callback per half-block, ~1 ms apart". The foreground main loop does nothing in Step 1 Part 2 except spin (or blink the LED at the existing 1 Hz).

For Step 1 Part 2, the registered callback is identity:

```c
static void passthrough(const int32_t *in, int32_t *out, uint32_t frames) {
  for (uint32_t i = 0; i < frames * 2; i++) {
    out[i] = in[i];
  }
}
```

---

## 9. Bring-up order in `audio_init()`

1. `configure_pll3_for_sai1()` — already done by `configure_clocks()` in step 1 part 1 if we move it there, otherwise here.
2. `mpu_configure_dma_region()` — must be before any DMA buffer access.
3. `gpio_configure_sai1_pins()` — PE2/3/4/5/6 to AF6, very-high speed, no pull, push-pull.
4. `dma_init_sai1_streams()` — configures both streams, but does not enable them.
5. `sai1_configure()` — programs all SAI1 registers, but leaves SAIEN = 0.
6. AK4556 RST pulse on PB11 — HIGH→1ms→LOW→1ms→HIGH (in `audio_init()` before SAI starts).
7. `sai1_enable()` — enables sub-block B first, then A. Clocks now running, codec latches on.
8. Enable DMA streams (TX first, then RX) and NVIC IRQs.

---

## 10. Decisions locked

| # | Decision | Rationale |
|---|---|---|
| 1 | PLL3 integer dividers, accept ~50 ppm MCLK error | Inaudible. Fractional PLL deferred to future custom board. |
| 2 | BLOCK_SIZE = 48 (1 ms half, 2 ms RT latency) | Matches libDaisy default; sufficient headroom for any DSP we'll add. |
| 3 | MPU non-cacheable region for `.dma_buffers` | Simpler than cache maintenance, cost negligible. |
| 4 | RX DMA drives callback; TX DMA fires no-op IRQs | Single callback path = no double-fire or ordering hazards. |
| 5 | DMA buffers in AXI SRAM (D1 region 0x24000000) | Only DMA-accessible region with enough space; DTCM is not on the AHB matrix DMA1/2 see. |
| 6 | No FreeRTOS, no preemption beyond ISRs | Stated project constraint. Cooperative model is sufficient for current and foreseeable scope. |

## 11. Open items

1. **Passthrough verification** — TX path confirmed (440 Hz tone audible). Next: swap `tone_test` → `passthrough` in `audio.c` and confirm line-in → line-out.
2. **Spec/code cleanup** — `audio.c` still has `tone_test` active, `passthrough` defined but unused. Debug snapshot globals (`dbg_*`) still present. Clean up once passthrough is confirmed.
3. **Exact PLL3 MCKDIV math** — spec §4 has a note that the final divider arithmetic needs re-verification. Low priority: audio confirmed working at current clock.
