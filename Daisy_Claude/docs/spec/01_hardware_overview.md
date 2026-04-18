# Spec 01 — Hardware Overview (Daisy Seed Rev 4 + Pod Rev 5)

**Status:** corrected 2026-04-17. Original (2026-04-12) incorrectly identified the board as Rev 7 with a PCM3060 codec. Physical board says "Rev 4"; confirmed by libDaisy `CheckBoardVersion()` logic and by empirical bring-up (PB11=reset, not deemphasis).

This document captures every hardware fact the firmware needs to know. Derived from Daisy Seed Rev 4 datasheet, Daisy Pod Rev 5 schematic, Daisy Pod databrief, and cross-referenced against libDaisy source for values not in the public schematic.

Sources (files in `hardware/`):
- `seed/ES_Daisy_Seed_Rev7.pdf` — public (reduced) schematic
- `seed/Daisy_Seed_datasheet.pdf` v1.2.0
- `seed/Seed_pinout.csv` — header pin → STM32 pin map
- `pod/ES_Daisy_Pod_Rev5.pdf` — Pod schematic
- `pod/Pod_databrief.pdf` — Pod pinout diagram
- `libdaisy_ref/system.cpp` — cross-reference for PLL values

---

## 1. MCU

- **Part:** STM32H750IBK6 (single-core Cortex-M7, 1 MB flash — but Daisy Seed only uses 128 KB and boots from external QSPI flash for larger programs)
- **Package:** UFBGA176+25
- **HSE crystal:** **16 MHz** (not shown in reduced schematic; confirmed by back-solving libDaisy's PLL ratios: for 480 MHz sysclk at PLLM=4/PLLN=240/PLLP=2, HSE must be 16 MHz)
- **LSE crystal:** presence unknown — not needed for step 1

---

## 2. Clock tree targets (to be implemented in step 2)

| Domain | Source | Target |
|---|---|---|
| SYSCLK | PLL1P | 480 MHz |
| CPU / AXI / AHB3 | SYSCLK | 480 MHz |
| HCLK (AHB1/2/4) | HCLK_DIV2 | 240 MHz |
| APB1 / APB2 / APB3 / APB4 | /2 | 120 MHz (timers 240 MHz) |
| SAI1 kernel | PLL3P | ~49 MHz → divided to ~12.29 MHz MCLK (48 kHz × 256) |

Required settings for 480 MHz operation:
- `PWR_D3CR.VOS = 0b11` (VOS0)
- Wait `PWR_D3CR.VOSRDY` before clock switch
- Flash ACR latency = 4 WS, programming delay = 0b10
- `SCB_EnableICache()`, `SCB_EnableDCache()` (standard M7 bring-up)

PLL1 parameters (HSE=16 MHz, target 480 MHz):
- PLLM=4 → PLL1 input 4 MHz (VCIRANGE_2 = 2–4 MHz)
- PLLN=240 → VCO 960 MHz (VCOWIDE = 192–960 MHz)
- PLLP=2 → SYSCLK 480 MHz
- PLLQ=5 → 192 MHz (spare)
- PLLR=2 → 480 MHz (spare)

PLL3 parameters (for SAI1, from libDaisy — known to drift ~0.03%, acceptable for step 1):
- PLLM=6 → 2.667 MHz
- PLLN=295 → VCO 786.67 MHz
- PLLP=16 → 49.17 MHz kernel → SAI MCKDIV gives MCLK ~12.29 MHz → Fs ≈ 48.016 kHz

Future optimization: retune PLL3 (possibly with FRACN) for exact 48000 Hz.

---

## 3. On-board audio codec — AK4556

- **Part:** AKM AK4556 (24-bit stereo ADC + DAC)
- **Control:** **hardware-configured, no I2C, no SPI**. All operating parameters are fixed by the board wiring; the only MCU interaction is the RST pin.
- **Format:** 24-bit left-justified (MSB-justified), slave for both ADC and DAC (STM32 is the BCK/LRCK master)
- **RST pin:** active-low. Has internal pulldown. **Must be pulsed** at startup: HIGH → 1 ms → LOW → 1 ms → HIGH. This is the exact sequence from libDaisy `Ak4556::Init()`. Driving it low (or leaving it floating) holds the codec in reset — no audio either direction.
- **Analog supply:** 4.5 V from on-board LDO
- **Digital supply:** 3.3 V filtered from Seed's `+3V3_D`

### SAI1 pin wiring (STM32 side)

These pins are **not** exposed on the Seed's 2×20 header; they are routed internally from the STM32H750 to the AK4556.

| STM32 Pin | Alt. function | AK4556 pin | Role |
|---|---|---|---|
| PE2 | SAI1_MCLK_A | MCLK      | Master clock |
| PE3 | SAI1_SD_B   | SDOUT      | ADC → MCU data (sub-block B, RX slave sync with A) |
| PE4 | SAI1_FS_A   | LRCK       | Frame sync |
| PE5 | SAI1_SCK_A  | BICK       | Bit clock |
| PE6 | SAI1_SD_A   | SDIN       | MCU → DAC data (sub-block A, TX master) |
| PB11 | GPIO out   | RST (active-low) | Codec reset — pulse HIGH→LOW→HIGH at startup |

### SAI1 operating mode

- Sub-block A: **TX master**, generates MCLK / BCK / FS, I²S protocol MSB-justified, 24-bit slot.
- Sub-block B: **RX slave synchronous with A** — shares BCK and FS from A, no independent clocks.
- Frame: 2 slots × 32 bits (24-bit audio left-justified in 32-bit slots), FS pulse = 1 full frame.
- MCLK divider chosen so MCLK ≈ 256 × Fs.
- This matches `SAI_I2S_MSBJUSTIFIED` + `SAI_PROTOCOL_DATASIZE_24BIT` in libDaisy.

### DMA

DMA1 Stream 0 (TX, SAI1_A, DMAMUX req 87) and DMA1 Stream 1 (RX, SAI1_B, DMAMUX req 88). Circular mode, 32-bit word transfers, direct mode (no FIFO). Stream 1 HT+TC IRQs pace the audio callback.

---

## 4. Daisy Seed — header pin map (relevant subset)

From `Seed_pinout.csv`. Full 40-pin table is in that file; the firmware only needs the pins it actually uses.

| Seed pin | Daisy name | STM32 pin | Used in wire program? |
|---|---|---|---|
| 16 | — | internal codec IN L | yes (analog jack → codec) |
| 17 | — | internal codec IN R | yes |
| 18 | — | internal codec OUT L | yes |
| 19 | — | internal codec OUT R | yes |
| 20 | — | AGND | yes (tie to DGND) |
| 21 | — | +3V3_A (output) | — |
| 38 | — | +3V3_D (output) | — |
| 39 | — | VIN (5–17 V) | yes |
| 40 | — | DGND | yes |

### Hidden (non-header) pins used

| STM32 pin | Function | Notes |
|---|---|---|
| PC7 | User LED (red) | Active-high, 1k series to GND |
| PB11 | AK4556 RST (active-low) | Output, pulse HIGH→LOW→HIGH at startup per libDaisy `Ak4556::Init()`. **Do not drive low** — holds codec in reset. |
| PE2..PE6 | SAI1 → AK4556 | See §3 |

### Other STM32 pins of interest (not used in wire program but documented for future steps)

SDRAM (FMC), QSPI flash, SDMMC, USB OTG FS/HS, and all header GPIO are omitted here — they don't matter until later steps. The full map lives in `seed/Seed_pinout.csv`.

---

## 5. Daisy Pod — peripheral map

The Pod is a passive carrier board for the audio path: J2/J3/J4 are just wired to Seed pins 16–19 and GND. No MCU-visible logic between jacks and codec.

### Audio jacks

| Jack | Pod label | Signal path |
|---|---|---|
| J2 | LINE IN   | TRS tip/ring → Seed pins 16/17 → AK4556 L/R IN |
| J3 | LINE OUT  | Seed pins 18/19 → TRS tip/ring (direct) |
| J4 | PHONES    | Seed pins 18/19 → HP volume pot → TPA6110 amp (1.5× gain) → TRS |
| J1 | MIDI IN   | 3.5 mm TRS MIDI → opto front-end → USART1_RX (PB7) |

### Controls (not used in wire program)

Documented for later steps. All active-low, pulled to GND when pressed / fully ccw / off.

| Pod control | Daisy name | STM32 pin | Type |
|---|---|---|---|
| SW1 (tactile) | D27 | PG9  | button, active-low |
| SW2 (tactile) | D28 | PA2  | button, active-low |
| POT_1         | D21 / A6 | PC4 | ADC, 0..3V3_A |
| POT_2         | D15 / A0 | PC0 | ADC, 0..3V3_A |
| ENC_A         | D26 | PD11 | quadrature |
| ENC_B         | D25 | PA0  | quadrature |
| ENC_CLICK     | D13 | PB6  | button, active-low |
| LED_1_R       | D20 | PC1  | common-anode RGB, **active-low** via 1k |
| LED_1_G       | D19 | PA6  | " |
| LED_1_B       | D18 | PA7  | " |
| LED_2_R       | D17 | PB1  | " |
| LED_2_G       | D24 | PA1  | " |
| LED_2_B       | D23 | PA4  | " |
| MIDI_IN       | D14 | PB7  | USART1_RX |

---

## 6. Power

- **VIN:** 5–17 V into pin 39; OR-diode with USB VBUS. Either source powers the Seed.
- **UNREGULATED_VCC:** output of the OR-diode stage.
- **+3V3_D:** TPS6217N buck from UNREGULATED_VCC (2.2 µH inductor, 47 k/15 k feedback divider → 3.3 V).
- **+3V3_A:** LP2985 LDO from UNREGULATED_VCC, filtered through 5R1 + 10 µF/1 µF/4.7 µF network.
- **5 V:** generated on-board (FB1 ferrite on output of LP2985 stage — actually this is the 3V3A rail; true 5 V for codec analog comes from a separate on-board regulator not visible on the reduced schematic).

**Required per datasheet:** AGND (pin 20) must be tied to DGND (pin 40) in every application. Not optional.

---

## 7. Voltage tolerance (per datasheet table 1)

- VIN: 5–17 V absolute.
- GPIO: **most pins 5V-tolerant**, except these which are 3V3-only:
  - PB1 (Seed pin 24 / A2)
  - PA7 (Seed pin 25 / A3)
  - PC4 (Seed pin 28 / A6)
  - PA5 (Seed pin 29 / A7)
  - PA4 (Seed pin 30 / A8)
- Audio inputs: AC-coupled, ±1.8 V range, 3.6 Vpp ≈ 1 Vrms typical.
- Audio outputs: 100 Ω source impedance.

---

## 8. Things NOT covered in this doc (deliberately)

- SDRAM (FMC) bring-up — deferred to a later step
- QSPI flash programming / XIP — deferred
- USB OTG — deferred
- SDMMC / FatFS — deferred
- Pod peripherals (switches, pots, encoder, LEDs, MIDI) — deferred
- Voltage scaling / power-gating details beyond what's needed for 480 MHz sysclk

These will get their own spec documents when we reach them.
