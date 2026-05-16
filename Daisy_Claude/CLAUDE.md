# Daisy_Claude — STM32H750 Bare-Metal Audio Project

An experiment: can Claude generate a working STM32H750 audio firmware largely from scratch, using the Daisy Seed (Rev 4) + Daisy Pod as the hardware target, without libDaisy and without ST HAL?

The parent `AudioDev/.claude/CLAUDE.md` still applies for conda and general audio-dev conventions, but this folder has its own rules that override when they conflict.

## Goals

- **Stage 1 (complete):** Minimal "wire" program — stereo audio in → block-based processing function (identity) → stereo audio out, at 48 kHz, through the on-board AK4556 codec. Confirmed clock tree, SAI1, DMA, and audio callback all working end-to-end.
- **Stage 1a (complete):** EQ + remote parameter control. Stereo biquad hi-shelf + LP filters, SEGGER RTT binary protocol, macOS SwiftUI app confirmed working on hardware. Verdict: Claude Code is highly effective for DSP firmware development — this stack is the blueprint for Bluetooth + iOS.
- **Stage 2 (planning):** Design and fab a custom board. See `docs/spec/04_stage2_custom_board.md` for planning decisions made so far.
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

- **Stage 1 (complete):** Wire program on the Daisy Seed Rev 4 + Pod.
  - Part 1: Chip boot, clock tree at 480 MHz, LED blink. ✓
  - Part 2: SAI1 + DMA + AK4556 stereo audio passthrough at 48 kHz. ✓
- **Stage 1a (complete):** EQ + remote parameter control. ✓
  - Stereo biquad hi-shelf + LP filters with real-time coefficient update. ✓
  - SEGGER RTT binary protocol (CMD_PING, CMD_SET_PARAM, CMD_GET_PARAM). ✓
  - macOS SwiftUI app, spec-driven UI, confirmed working on hardware. ✓
- **Stage 2 (planning):** Design and fab a custom board. Target chip locked: STM32H743VIT6 (LQFP-100). See `docs/spec/04_stage2_custom_board.md`.

## Toolchain

- **Compiler:** `arm-none-eabi-gcc` from the STM32CubeIDE-bundled toolchain
- **Build system:** Makefile (hand-written, no CubeMX)
- **Debugger / flasher:** STM32CubeIDE, used *only* as a debug frontend — project is not a CubeIDE-managed project
- **Target:** STM32H750IBK6 on Daisy Seed Rev 4, mounted on Daisy Pod Rev 5

## Hardware facts (authoritative)

See `docs/spec/01_hardware_overview.md` for the full summary. Irreducible facts:

- **HSE crystal:** 16 MHz (confirmed by back-solving libDaisy's PLL math)
- **Target SYSCLK:** 480 MHz (VOS0, flash latency 4)
- **On-board codec:** AKM AK4556, hardware-configured (no I2C/SPI), 24-bit left-justified, slave/slave
- **Codec RST:** PB11, active-low. Pulse HIGH→1ms→LOW→1ms→HIGH at startup (before SAI clocks start). Leaving low = codec in reset = no audio.
- **Codec bus:** SAI1 on PE2 (MCLK_A), PE3 (SD_B = RX from ADC), PE4 (FS_A), PE5 (SCK_A), PE6 (SD_A = TX to DAC). Sub-block A is TX master, sub-block B is RX slave synchronous with A.
- **User LED:** PC7, active-high
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
│   ├── seed/                         Daisy Seed Rev 4 datasheet, schematic, pinout
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

**Firmware milestone archives:** When a firmware version is confirmed working on
hardware, copy `seed_h750/` to a numbered archive folder before adding new features:

```
seed_h750_01_wire/      ← stereo passthrough confirmed working
seed_h750_02_eq/        ← EQ + OpenOCD param control confirmed working
seed_h750/              ← active development (always the latest)
```

Each archive is a fully self-contained, independently buildable CubeIDE project.
This gives a one-click "open and flash" recovery path without any git operations.
Git tags (`git tag wire-program`) should be created alongside for version history.

After copying, immediately update the `<name>` field in the archive's `.project`
to match the folder name (e.g. `seed_h750_01_wire`). CubeIDE refuses to import
two projects with the same name into one workspace.

## Coding style

See `docs/coding_standards.md` for the full rules. Key points that must be followed in all new code:
- **1TBS braces** — opening brace on the same line as the function/struct/control keyword, always
- **2-space indent** — no tabs, no 4-space indent
- **snake_case** — variables, functions, file names

## Host app / parameter UI convention

Mac and iOS apps are **spec-driven**: Claude constructs the UI from the DSP spec and source at design time. No runtime parameter-tree discovery.

**Schema identity:** each DSP/app pair has a UUID v4 (random, generated when the spec changes) plus human-readable `APP_NAME` and `VERSION` constants. All three are defined in the spec document and copied verbatim into both firmware and the host app:

```c
#define SCHEMA_APP_NAME  "daisy_eq"
#define SCHEMA_VERSION   "1.0.0"
#define SCHEMA_UUID      "7f3a1c09-4e82-4b61-9d3f-a82c05f1ee44"
```

The host app verifies the UUID at connect time before doing anything. A mismatch means firmware and app are out of sync. Generate a new UUID (via `uuidgen`) whenever the parameter spec changes in a breaking way.

Parameters are stored as named C structs so they are visible in the IDE debugger by field name, not raw address.

## Remote DSP Testing Strategy

The RTT binary protocol supports a `CMD_AUDIO_BLOCK` command: host sends a stereo PCM buffer, STM32 runs it through the DSP graph, host receives the processed buffer. This is a **blocking round-trip per buffer** — send 48 frames, wait for response, repeat.

**Measured overhead (H750 at 480 MHz, USB-SWD via J-Link):** ~14× real-time. A 1 ms audio block (48 frames at 48 kHz) takes ~14 ms round-trip. RTT is therefore **not suitable for real-time playback** via the host.

**What it is good for — block-level correctness testing:**
- Send known input → receive STM32 output → compare against native C++ (pybind11) output
- If the native and STM32 results match bit-for-bit (or within float rounding), the firmware graph is correct
- This catches porting bugs, alignment issues, endianness errors, and coefficient calculation mistakes

**Key requirement — identical graph creation:** The graph wiring code (which blocks connect to which, in what order) must be generated identically for both the native pybind11 build and the STM32 firmware. Claude generates this wiring from the same spec. If the connection code is identical, a block-level RTT test that passes guarantees the firmware graph is correct by construction.

**Future: per-block execution timing.** Firmware should measure and report the CPU cycles consumed by each block's `process()` call (via DWT cycle counter or SysTick). Report these via `CMD_GET_BLOCK_TIMING` or similar. During graph creation, Claude can sum the per-block cycle budgets and flag graphs that exceed the real-time deadline (1 ms = 480,000 cycles at 480 MHz). This makes DSP load estimation automatic at design time.

**Tools:** `Python_STM32/host/python/tools/`
- `rtt_wire_test.py` — passthrough correctness + per-block timing measurement
- `rtt_testbench.py` — process audio files through the STM32 DSP graph
- `rtt_params.py` — set/get EQ parameters via RTT (uses pylink, not TCP)

## Working conventions

- When writing code, favor register-level clarity over brevity. A comment naming the reference-manual section/page for each non-obvious register write is welcome; vague "configure SAI" comments are not.
- Pin assignments live in exactly one header (`board.h` eventually). No magic numbers scattered through drivers.
- Spec documents in `docs/spec/` are append-only once agreed. If a decision changes, add a new document that supersedes, don't silently edit history.
