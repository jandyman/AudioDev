# Daisy_Claude — STM32H750 Bare-Metal Audio Project

An experiment: can Claude generate a working STM32H750 audio firmware largely from scratch, using the Daisy Seed (Rev 7) + Daisy Pod as the hardware target, without libDaisy and without ST HAL?

The parent `AudioDev/.claude/CLAUDE.md` still applies for conda and general audio-dev conventions, but this folder has its own rules that override when they conflict.

## Goals

- **Step 1 (current):** Minimal "wire" program — stereo audio in → block-based processing function (identity) → stereo audio out, at 48 kHz, through the on-board PCM3060 codec. Confirms clock tree, SAI1, DMA, and the audio callback structure all work.
- **Long-term:** Build up from the wire program into a general DSP platform for the pitch-shifter work being done in sibling projects.

## Hard rules

- **No ST HAL.** CMSIS device headers (`stm32h750xx.h`, `core_cm7.h`) are allowed for register definitions only. No `HAL_*` calls, no CubeMX-generated code.
- **No libDaisy.** We may *read* libDaisy source as a cross-check on hardware-dictated values, but we do not copy or link against it.
- **Write everything ourselves.** Startup file, linker script, clock init, vector table, SAI driver, DMA driver, audio callback — all hand-written from the reference manual. We own it, we understand it.
- **Run-to-completion model.** No RTOS. Cooperative foreground loop. ISRs are the only preemption mechanism unless a specific need for more arises.
- **No dynamic allocation, anywhere, ever.** No `malloc`, no `calloc`, no `new`, no heap. All buffers are static (file-scope or function-local `static`) with fixed sizes known at compile time. The linker script does not define a heap region, and `_sbrk` is deliberately absent — if something tries to allocate, the link fails. This applies to every line of firmware code on this target, not just the audio callback.
- **Baby steps with checkpoints.** Every stage ends with something observable (LED blink, scope trace, audio passthrough) before we move on.
- **Run from internal flash only.** Code lives at 0x08000000. No external QSPI flash (the Daisy Seed has an 8 MB chip — we do not use it). No external SDRAM (the Daisy Seed has a 64 MB chip — we do not use it). This is a dress rehearsal for the future custom board, which will have ≥1 MB internal flash and **no external memory chips at all**.
- **Memory budget.** Whatever we build must fit in ~128 KB flash + ~1 MB internal SRAM on the current H750, and ~2 MB flash + ~1 MB SRAM on the future target. Avoid any design pattern that assumes multi-megabyte flash or off-chip RAM: no large lookup tables, no long impulse responses stored in `const`, no big static buffers. If an algorithm needs more than that, it needs a different algorithm.

## Long-term plan

- **Stage 1 (current):** Wire program on the Daisy Seed Rev 7 + Pod. Split into parts:
  - **Part 1:** Chip boot, clock tree at 480 MHz, LED blink. Proves the toolchain, startup, and clock code work.
  - **Part 2:** SAI1 + DMA + PCM3060 audio loopback at 48 kHz. Stereo identity passthrough.
- **Stage 1 is a gate, not a destination.** Its purpose is to validate whether Claude Code can actually deliver working embedded code. If yes, we move to Stage 2. If no, the project ends here.
- **Stage 2:** Design and fab a custom board. STM32H7 variant with ≥1 MB internal flash (e.g., H743, H723), more space-constrained, no external memory chips. Code written for Stage 1 should port to this board with linker-script-level changes only.

## Toolchain

- **Compiler:** `arm-none-eabi-gcc` from the STM32CubeIDE-bundled toolchain
- **Build system:** Makefile (hand-written, no CubeMX)
- **Debugger / flasher:** STM32CubeIDE, used *only* as a debug frontend — project is not a CubeIDE-managed project
- **Target:** STM32H750IBK6 on Daisy Seed Rev 7, mounted on Daisy Pod Rev 5

## Hardware facts (authoritative)

See `docs/spec/01_hardware_overview.md` for the full summary. Irreducible facts:

- **HSE crystal:** 16 MHz (confirmed by back-solving libDaisy's PLL math)
- **Target SYSCLK:** 480 MHz (VOS0, flash latency 4)
- **On-board codec:** TI PCM3060, hardware-configured (no I2C), 24-bit left-justified, slave/slave
- **Codec bus:** SAI1 on PE2 (MCLK_A), PE3 (SD_B = RX from ADC), PE4 (FS_A), PE5 (SCK_A), PE6 (SD_A = TX to DAC). Sub-block A is TX master, sub-block B is RX slave synchronous with A.
- **User LED:** PC7, active-high
- **Rev 7 detect:** PD5 tied to GND (input with pull-up, reads 0 on Rev 7)
- **Audio jacks (via Pod, passive):** line in on J2 = Seed pins 16/17, line out on J3 = Seed pins 18/19, headphone on J4 (after Pod's on-board TPA6110 amp + rotary volume pot)

## Directory layout

```
Daisy_Claude/                         repo subfolder; CubeIDE workspace lives here too
├── CLAUDE.md                         this file — project index
├── .metadata/                        CubeIDE workspace state (gitignored)
├── docs/
│   └── spec/                         spec documents, append-only once frozen
│       ├── 01_hardware_overview.md
│       ├── 02_step1_startup_and_clock.md
│       └── 03_project_layout.md      reorg into per-target subfolders
├── hardware/                         reference PDFs and vendor source (shared)
│   ├── seed/                         Daisy Seed Rev 7 datasheet, schematic, pinout
│   ├── pod/                          Daisy Pod Rev 5 datasheet, schematic, pinout
│   └── libdaisy_ref/                 libDaisy source pulled for cross-reference only
└── seed_h750/                        firmware project — one subfolder per hardware target
    ├── Makefile                      hand-written, build artifacts in seed_h750/build/
    ├── linker/
    │   └── stm32h750_flash.ld
    ├── include/
    │   └── board.h
    ├── src/
    │   └── … (.c, .h, startup_*.s)
    ├── build/                        gitignored
    └── .project, .cproject, .settings/, *.launch     CubeIDE project metadata
```

Each `<target>/` subfolder is one self-contained CubeIDE project: own Makefile,
own linker script, own debug launch config. A future Stage 2 port to a custom H743
board would land as `custom_h743/` next to `seed_h750/`, sharing `docs/` and
`hardware/` but with its own build and project metadata.

## Working conventions

- When writing code, favor register-level clarity over brevity. A comment naming the reference-manual section/page for each non-obvious register write is welcome; vague "configure SAI" comments are not.
- Pin assignments live in exactly one header (`board.h` eventually). No magic numbers scattered through drivers.
- Spec documents in `docs/spec/` are append-only once agreed. If a decision changes, add a new document that supersedes, don't silently edit history.
