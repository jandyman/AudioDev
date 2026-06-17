# AudioDev - Claude Context

Cross-project configuration for audio development work.

## C++ Coding Style

- **1TBS braces** — opening brace on the same line for functions, structs, classes, control blocks. No K&R function-definition exception.
- **2-space indent** — no tabs, no 4-space indent.
- **snake_case** — variables, functions, file names. Well-known domain acronyms (`dma`, `sai`, `pll`, `i2s`) stay lowercase as-is.
- **Conserve vertical space** — blank lines between logical steps, not between every line. Tightly related statements stay contiguous.
- **Block-comment spacing** — code should read like paragraphs: a paragraph-style (multi-line) comment heading a function *or* a block of constants gets a blank line under it; single-line labels and in-body comments hug the code.
- **Align trailing `//` comments** vertically when a group of them appears together.

These apply to Faust `.dsp` source as well as C++ — read "function" as a top-level
definition (`name = …;`), and a labeled parameter group as a block of constants;
only the 1TBS brace rule is C++-specific.

Full reference: `Daisy_Claude/docs/coding_standards.md`.

## Python Environment

Python scripts are always run from **PyCharm**, which is configured to use the `scipy` conda environment directly. Do not add conda activation steps to scripts and do not generate CLI arguments — PyCharm runs scripts as-is, and configurable parameters live as named variables at the bottom of the script.

When Claude needs to run a **build** (make) command that requires the conda environment (e.g. pybind11 headers), activate it first:
```bash
source ~/miniforge3/etc/profile.d/conda.sh && conda activate scipy
make -f eq.make
```
The `scipy` environment has numpy, matplotlib, dawdreamer, pybind11, and other audio-dev dependencies.

## Naming Conventions

- **Never name example/demo scripts with a `test_` prefix.** PyCharm collects `test_*.py` files for pytest, which prevents interactive plotting. Use `_demo.py` suffix instead (e.g. `attack_detector_demo.py`, `pitch_shift_demo.py`).
- Actual unit tests use the `test_` prefix and live in a `tests/` folder, separate from demos.

## Project Structure

- **Python_STM32/** - ACTIVE hub: shared C++/Faust DSP blocks, built native (pybind11) and for the STM32H750; per-algorithm work lives in `projects/<algo>/`. See `Python_STM32/.claude/CLAUDE.md`.
- **max_externals/** - Max/MSP external objects (C++)
- **dsp_library/** - Shared DSP code including Faust modules
- **audio-graph-python/** - DEPRECATED reference framework (superseded by Python_STM32); no new work here
- **Max Experiments/** - Max patchers and documentation
- **PitchShifter/** - Pitch shifter algorithm development

## Implementation Architecture

DSP logic is implemented in **C++ or Faust**. Faust is the implementation language of choice for feedback-dense blocks (resonators, IIRs, delay-modulation effects, coupled envelope followers, multi-channel state machines); plain C++ for fixed-coefficient filters, gain/mix/sum, and straightforward chunk-wise math. The inter-block contract is chunk-based — blocks process buffers of samples, not individual samples; per-sample / feedback techniques live inside blocks. Faust's runtime never ships to the STM32 — only the generated `.cpp` is embedded as first-class firmware code, called in the chunk-by-chunk processing sequence. Python DSP prototyping is acceptable only as a very temporary step before C++/Faust translation. See `Python_STM32/docs/audio_graph_architecture.md` for the full architecture and block source file conventions.

**One C++ source, two build targets.** The same C++ files compile for the embedded target (arm-none-eabi) and natively on macOS via pybind11. There is no separate desktop simulation — the code under test *is* the firmware code. Platform differences are confined to a thin platform header; DSP logic is identical across targets.

**Static graph topology, generated at design time.** Pipelines are expressed as direct C++ function calls, not a runtime graph framework. Claude generates the connection code from a spec. This makes static graphs practical without the boilerplate cost that would otherwise force a dynamic system. Each algorithm gets freshly generated concrete code, not a reused framework.

**Python is the test harness only.** Python drives pybind11-wrapped C++ blocks, generates input signals, collects outputs, and plots results. Do not implement DSP logic in Python.

**No dynamic memory allocation in the audio render callback.** Allocation during module construction is fine. For embedded targets, pure static allocation (fixed-size class member arrays) is required.

**Signal node probing.** Every block must expose internal state signals as additional outputs (envelopes, flags, computed values). Python taps any node in the pipeline for diagnosis without restructuring the graph. This pattern applies to all new blocks.

## Per-project state

This file is cross-project configuration only. Each project's current state,
structure, and next steps live in its own `CLAUDE.md`. The active project is
**Python_STM32** — see `Python_STM32/.claude/CLAUDE.md` for the pitch-shifter
pipeline state, build workflow, and conventions.
