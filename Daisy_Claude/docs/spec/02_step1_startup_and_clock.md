# Spec 02 — Step 1: Startup, Clock Tree, and LED Blink

**Status:** frozen 2026-04-12. Decisions in §14 locked: CMSIS `stm32h750xx.h` permitted, upload via SWD from STM32CubeIDE, code runs from internal flash at 0x08000000. Zero dynamic allocation (see `CLAUDE.md` hard rule).

This is the first step with actual code. The goal is the narrowest useful slice that proves we can build, flash, run, and debug a hand-written bare-metal program on the Daisy Seed Rev 7. No audio yet — that comes in step 2. The acceptance criterion is a blinking LED, but the code we write here is the foundation that every subsequent step will build on, so it must be *right*, not just *working*.

---

## 1. What this step delivers

A program that:

1. Boots from internal flash at 0x08000000 (the STM32H750's on-chip 128 KB bank), loaded via SWD through STM32CubeIDE.
2. Configures the clock tree: HSE 16 MHz → PLL1 → SYSCLK = 480 MHz, with VOS0 and flash latency 4.
3. Initializes the Cortex-M7 I-cache and D-cache.
4. Enables GPIOC, configures PC7 as push-pull output.
5. Sets up SysTick as a 1 ms tick.
6. Enters a foreground loop that toggles PC7 at ~1 Hz using SysTick.

That's it. No SAI, no DMA, no SDRAM, no QSPI, no MPU regions (defer to step 3 or later), no USB, no UART. Anything beyond the above is out of scope and goes into its own spec.

---

## 2. Files created in step 1

```
Daisy_Claude/
├── Makefile                       top-level build
├── linker/
│   └── stm32h750_flash.ld         linker script, FLASH (0x08000000) + DTCMRAM (0x20000000)
├── include/
│   └── board.h                    pin assignments (PC7 only for now)
├── src/
│   ├── startup_stm32h750.s        vector table, reset handler, default handlers
│   ├── system_init.c              SystemInit() — called from reset handler before main()
│   ├── clock.c                    ConfigureClocks() — PLL1, PWR, FLASH, bus dividers
│   ├── clock.h
│   ├── gpio.c                     tiny GPIO helpers (set mode, set/clear/toggle)
│   ├── gpio.h
│   ├── systick.c                  1 ms tick
│   ├── systick.h
│   └── main.c                     the blink loop
└── docs/
    └── spec/
        ├── 01_hardware_overview.md
        └── 02_step1_startup_and_clock.md    (this file)
```

Total: ~10 hand-written files, probably ~600 lines. No generated code, no vendor files beyond (maybe) CMSIS headers.

---

## 3. CMSIS headers — LOCKED: use `stm32h750xx.h`

We use ST's CMSIS device header `stm32h750xx.h` and the CMSIS-Core header `core_cm7.h` (plus its transitive dependencies: `cmsis_gcc.h`, `cmsis_version.h`, `cmsis_compiler.h`). These headers contain **register struct definitions, bit-field masks, and a small set of always-inline helpers** (cache enable, NVIC, etc.). No HAL. No CubeMX-generated code. No vendor `.c` files beyond what we write ourselves.

Headers live alongside libDaisy at:
```
../DaisyExamples/libDaisy/Drivers/CMSIS/Device/ST/STM32H7xx/Include/stm32h750xx.h
../DaisyExamples/libDaisy/Drivers/CMSIS/Include/core_cm7.h
```

The Makefile adds these two directories to `-I`. We do not copy the headers into this repo — that way a CMSIS update is a matter of changing the include path, not diffing vendored copies.

One project-specific wart: the ST CMSIS header by default expects a `#define STM32H750xx` macro so it knows which chip you mean. We pass that on the compile line (`-DSTM32H750xx`). It also wants `HSE_VALUE` defined; we set that to `16000000` on the compile line, confirmed by §1 of spec 01.

---

## 4. Startup file — `startup_stm32h750.s`

Hand-written ARM Cortex-M7 startup in GNU assembler syntax. Structure:

```
.section .isr_vector
    .word _estack                   initial MSP (from linker script)
    .word Reset_Handler             reset vector
    .word NMI_Handler
    .word HardFault_Handler
    .word MemManage_Handler
    .word BusFault_Handler
    .word UsageFault_Handler
    ...                             reserved + remaining Cortex-M exceptions
    .word SVC_Handler
    .word DebugMon_Handler
    .word PendSV_Handler
    .word SysTick_Handler
    ...                             150+ device-specific IRQ handlers (STM32H750 has ~150)

Reset_Handler:
    ldr sp, =_estack                (redundant — core already loaded from vector[0], but explicit)
    bl  copy_data_section           .data init (from flash load addr to RAM)
    bl  zero_bss_section            .bss = 0
    bl  SystemInit                  clocks, cache, FPU
    bl  __libc_init_array           C++ ctors — empty in step 1
    bl  main
    b   .

Default_Handler:
    b .                             infinite loop, easy to spot in debugger
    (weak-aliased by every IRQ and fault handler except the ones main code overrides)
```

Every handler is `.weak` aliased to `Default_Handler` so that main code can override any of them with a normal C function having the matching name. Standard CMSIS pattern.

**Stack:** `_estack` comes from the linker script (see §5). Initial MSP value, written as word 0 of the vector table so the core loads it on reset before executing anything.

**FPU:** The M7 FPU is enabled by setting CPACR bits in `SystemInit`. We do this early so the C runtime can use float safely. Step 1 doesn't need floats, but enabling the FPU costs ~4 instructions and avoids a gotcha later.

**Cache:** `SCB_EnableICache()` and `SCB_EnableDCache()` equivalents, also in `SystemInit`. Both optional for a blink program but needed for any serious performance — and we want step 1 to leave the core in its "real" state, not a reduced one we'd later have to enable.

**VTOR:** We set `SCB->VTOR` to the link address of `_isr_vector` so the core finds our vector table. Critical if we're not running from 0x00000000 / 0x08000000.

---

## 5. Linker script — `stm32h750_flash.ld`

Code runs from the STM32H750's on-chip flash bank at 0x08000000 (128 KB). Stack and writable data live in DTCM-RAM at 0x20000000 (128 KB) — zero wait state, no cache coherency concerns because DTCM bypasses the D-cache, and DMA doesn't touch it (it doesn't need to for step 1).

Memory regions available on H750 (for reference — we use only the first two):

| Region | Address | Size | Used in step 1? |
|---|---|---|---|
| FLASH (internal) | 0x08000000 | 128 KB | yes — all code + rodata + .data LMA |
| ITCM-RAM | 0x00000000 | 64 KB | no |
| DTCM-RAM | 0x20000000 | 128 KB | yes — .data, .bss, stack |
| AXI SRAM (D1) | 0x24000000 | 512 KB | no |
| SRAM1/2/3 (D2) | 0x30000000 | 288 KB | no |
| SRAM4 (D3) | 0x38000000 | 64 KB | no |

Layout:
```
MEMORY {
    FLASH   (rx)  : ORIGIN = 0x08000000, LENGTH = 128K
    DTCMRAM (rwx) : ORIGIN = 0x20000000, LENGTH = 128K
}
SECTIONS {
    .isr_vector : { KEEP(*(.isr_vector)) } > FLASH
    .text       : { *(.text*) *(.rodata*) } > FLASH
    .data       : {
        _sdata = .;
        *(.data*)
        _edata = .;
    } > DTCMRAM AT > FLASH
    _sidata = LOADADDR(.data);
    .bss (NOLOAD) : {
        _sbss = .;
        *(.bss*) *(COMMON)
        _ebss = .;
    } > DTCMRAM
    ._stack (NOLOAD) : {
        . = ALIGN(8);
        . = ORIGIN(DTCMRAM) + LENGTH(DTCMRAM);
        _estack = .;
    } > DTCMRAM
    /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) }
}
```

Stack grows downward from the top of DTCMRAM (0x20020000). No heap — if any library code references `_sbrk`, the link fails, which is exactly what we want per the hard rule in `CLAUDE.md`.

The startup file copies `.data` from its LMA in flash (`_sidata`) to its VMA in DTCM (`_sdata`..`_edata`), then zeros `.bss`. Standard Cortex-M bring-up.

**Loading mechanism — LOCKED: SWD via STM32CubeIDE.** CubeIDE is the debug/flash frontend; it sees our `.elf` as an external build and programs the internal flash over SWD using its bundled ST-LINK GDB server. No DFU bootloader, no `dfu-util`. Big win: when power cycles, the program is already in flash and runs on its own — no debugger required for a functional test.

---

## 6. SystemInit (`system_init.c`)

Called from Reset_Handler before `main`. Sequence:

```c
void SystemInit(void) {
    // 1. Enable FPU (CPACR CP10/CP11 full access)
    SCB->CPACR |= (0xF << 20);

    // 2. Set VTOR to our vector table address (DTCM base + offset)
    SCB->VTOR = (uint32_t)&_isr_vector;

    // 3. Enable caches
    SCB_EnableICache();
    SCB_EnableDCache();

    // 4. Configure clock tree → 480 MHz
    ConfigureClocks();
}
```

`ConfigureClocks()` is in `clock.c` and does the register-level work described in §7.

---

## 7. Clock configuration — `clock.c`

Boot-up state (after reset, before this runs):
- HSI 64 MHz as SYSCLK
- VOS3 (default low-power scale)
- Flash latency 7 (RCC default — conservative, works at any frequency)
- PLLs off

Sequence to reach 480 MHz on HSE:

```
1. PWR->CR3:  set SMPS/LDO supply selection to LDO
                  (HAL_PWREx_ConfigSupply(PWR_LDO_SUPPLY) equivalent;
                   bits BYPASS=0, LDOEN=1, SMPSEN=0)
   Wait PWR->CSR1 ACTVOSRDY = 1.

2. PWR->D3CR: set VOS = 0b11 (VOS0, highest performance, needed for 480 MHz)
   Wait PWR->D3CR VOSRDY = 1.

   NOTE: on H750, SYSCFG->PWRCR.ODEN (overdrive enable) may need to be set first
   if revision V silicon; on revision Y it's a different register.
   Need to verify against the errata sheet (ES0392).

3. RCC->CR:   HSEON = 1. Wait HSERDY = 1.

4. FLASH->ACR: LATENCY = 4, WRHIGHFREQ = 0b10 (programming delay).
   Verify ACR reflects the write before proceeding.

5. RCC->PLLCKSELR:
     PLLSRC = HSE
     DIVM1  = 4      (PLL1 input = 4 MHz)
6. RCC->PLL1DIVR:
     DIVN1 = 240-1   (VCO = 960 MHz)
     DIVP1 = 2-1     (SYSCLK = 480 MHz)
     DIVQ1 = 5-1
     DIVR1 = 2-1
7. RCC->PLLCFGR:
     PLL1VCOSEL = 0  (wide VCO, 192-960 MHz)
     PLL1RGE    = 2  (4-8 MHz input range... wait, 4 MHz is the boundary)
     DIVP1EN = DIVQ1EN = DIVR1EN = 1

     NOTE: the PLL1 input at 4 MHz is right at the boundary between
     VCIRANGE_1 (2-4 MHz) and VCIRANGE_2 (4-8 MHz). libDaisy uses VCIRANGE_2
     per their source, and that works; we'll do the same. Confirm against RM.

8. RCC->CR:   PLL1ON = 1. Wait PLL1RDY = 1.

9. RCC->D1CFGR: D1CPRE=1 (/1), HPRE=8 (/2) → HCLK = 240 MHz
   RCC->D2CFGR: D2PPRE1=4 (/2), D2PPRE2=4 (/2) → APB1/2 = 120 MHz
   RCC->D3CFGR: D3PPRE=4 (/2) → APB4 = 120 MHz
   RCC->D1CFGR: D1PPRE=4 (/2) → APB3 = 120 MHz

10. RCC->CFGR: SW = 0b011 (PLL1) — switch SYSCLK to PLL1
    Wait SWS = 0b011 confirms the switch landed.
```

Each step checks its own ready/lock bit with a timeout; on timeout we sit in a `while(1)` that a debugger can catch. No fallback to HSI — if PLL1 fails at this stage, we want the failure to be visible, not silently degraded.

**What is NOT done here:** PLL2 (FMC/SDMMC — deferred to SDRAM step), PLL3 (SAI — deferred to audio step), peripheral kernel clock selection (done per-peripheral later), MPU regions (default MPU is fine without D-cache bugs since nothing is using DMA yet).

---

## 8. GPIO — `gpio.c`

The narrowest useful GPIO helper:

```c
typedef enum { GPIO_IN, GPIO_OUT_PP, GPIO_OUT_OD, GPIO_AF } gpio_mode_t;

void gpio_enable_port(GPIO_TypeDef *port);   // turn on RCC AHB4ENR bit
void gpio_set_mode(GPIO_TypeDef *port, uint32_t pin, gpio_mode_t mode);
void gpio_write(GPIO_TypeDef *port, uint32_t pin, bool value);
void gpio_toggle(GPIO_TypeDef *port, uint32_t pin);
bool gpio_read(GPIO_TypeDef *port, uint32_t pin);
```

Alternate-function routing is deferred — step 1 doesn't need AF, only push-pull output. We'll extend this helper when step 2 needs PE2–PE6 in AF mode for SAI1.

---

## 9. SysTick — `systick.c`

Configure SysTick for a 1 ms tick at HCLK/8 = 30 MHz:

```c
SysTick->LOAD = (30000000 / 1000) - 1;   // 30000 ticks = 1 ms
SysTick->VAL  = 0;
SysTick->CTRL = 0b111;                   // clksrc = processor (external/8), tickint, enable
```

Wait — actually the M7 SysTick "external" clock is `STCLK = HCLK/8`. With HCLK=240 MHz, STCLK=30 MHz. Alternatively use `clksrc=1` to run off the processor clock directly at 240 MHz — same result, just a different LOAD value. We'll use HCLK/8 for consistency with convention and margin.

Global volatile tick counter:
```c
static volatile uint32_t g_ticks_ms;
void SysTick_Handler(void) { g_ticks_ms++; }
uint32_t millis(void) { return g_ticks_ms; }
void delay_ms(uint32_t ms) { uint32_t t0 = millis(); while ((millis() - t0) < ms) {} }
```

---

## 10. main.c

```c
int main(void) {
    gpio_enable_port(GPIOC);
    gpio_set_mode(GPIOC, 7, GPIO_OUT_PP);
    for (;;) {
        gpio_toggle(GPIOC, 7);
        delay_ms(500);
    }
}
```

---

## 11. Makefile

Minimal, targets:

- `make` — build `build/daisy_step1.elf`, `.bin`, `.hex`, and `.map`
- `make clean` — rm build dir
- `make size` — `arm-none-eabi-size` on the elf (quick sanity check that .text fits in 128 KB flash)

No `make upload` target — flashing is done from STM32CubeIDE's debug launcher, which treats our ELF as an "external build" artifact and writes it to internal flash over SWD. Keeping this out of the Makefile keeps the build system platform-independent and avoids having to know where CubeIDE's `ST-LINK_gdbserver` lives.

Toolchain variables `CC`, `AS`, `LD`, `OBJCOPY`, `SIZE` all point at `arm-none-eabi-*`. We prefer the copy bundled with STM32CubeIDE but any recent `arm-none-eabi-gcc` (10+) will work. Flags:

```
-mcpu=cortex-m7 -mthumb -mfpu=fpv5-d16 -mfloat-abi=hard
-ffreestanding -nostdlib -nostartfiles -fno-common
-Og -g3 -Wall -Wextra -Wshadow -Wundef
-DSTM32H750xx -DHSE_VALUE=16000000
-T linker/stm32h750_flash.ld
-Wl,--gc-sections -Wl,-Map=build/daisy_step1.map
```

`-Og` for debuggable step-1 builds. `-O2`/`-O3` later when audio needs performance. `-ffreestanding -nostdlib -nostartfiles` ensures no libc/newlib startup code is linked — our `startup_stm32h750.s` is the only entry point. `-fno-common` puts every uninitialized global in its own `.bss` slot, which plays nicely with our hand-written linker script.

---

## 12. Acceptance test

- Connect an ST-LINK (or compatible SWD probe) to the Daisy Seed's JTAG header (P6). Power Seed via micro-USB.
- In STM32CubeIDE, create a **Debug Configuration → "GDB Hardware Debugging"** (or "STM32 C/C++ Application") pointing at `Daisy_Claude/build/daisy_step1.elf`. Make sure the "Project" box is empty and the build step is disabled — CubeIDE will just load the ELF and launch the debugger.
- Launch the debug session. CubeIDE writes `.text` into internal flash at 0x08000000, then halts at `Reset_Handler`.
- Let it run.
- **Primary:** User LED on the Seed blinks at ~1 Hz.
- **Power-cycle test:** disconnect the SWD probe, unplug and replug USB power. The LED should blink on its own with no debugger attached — that's the whole point of running from flash.

Secondary checks:
- In a SWD debugger, verify `SystemCoreClock` (if we populate it) reads 480 000 000.
- Verify `RCC->CFGR SWS` = 0b011 (PLL1 selected).
- Verify `FLASH->ACR LATENCY` = 4.
- Verify `PWR->D3CR VOS` = 0b11.

If any of those read wrong, the clock tree code has a bug.

---

## 13. Out of scope (explicitly)

The following must NOT be added to step 1 even though they're tempting:

- Any audio code. SAI, DMA, PLL3. That's step 2.
- SDRAM init. That's step 3 or later.
- USB CDC for `printf`. Nice to have, but adds USB stack complexity.
- A real driver layer. We're writing the *first* working program; drivers emerge in step 4+ when we need them in multiple places.
- Unit tests. No tests on target until we have a way to see their output.
- Error-handling infrastructure beyond "hang in an infinite loop the debugger can see".

---

## 14. Decisions — locked

1. **CMSIS headers:** use ST `stm32h750xx.h` + `core_cm7.h` from libDaisy's CMSIS path for register definitions only. No HAL. (§3)
2. **Upload mechanism:** SWD via STM32CubeIDE, writing to internal flash at 0x08000000. No DFU bootloader. (§5)
3. **Execution model:** run from internal flash at 0x08000000; stack/.data/.bss in DTCMRAM. Treat this as a dress rehearsal for the future H743-class custom board. (§5)
4. **Dynamic allocation:** none, anywhere. Linker does not define `_end`/`_sbrk` — any accidental `malloc` reference fails to link. (see `CLAUDE.md` hard rule)
