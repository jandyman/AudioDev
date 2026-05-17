# AudioDev - Claude Context

Cross-project configuration for audio development work.

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
- Actual unit tests live in `audio-graph-python/tests/` and DO use the `test_` prefix.

## Project Structure

- **max_externals/** - Max/MSP external objects (C++)
- **dsp_library/** - Shared DSP code including Faust modules
- **audio-graph-python/** - Python testing framework
- **Max Experiments/** - Max patchers and documentation
- **PitchShifter/** - Pitch shifter algorithm development

## Implementation Architecture

All DSP logic is implemented in **C++**. Faust is used only for rapid algorithm sketching — once an algorithm is proven, it is translated into plain C++ and the Faust version is retired. Python DSP prototyping is acceptable only as a very temporary step before C++ translation.

**One C++ source, two build targets.** The same C++ files compile for the embedded target (arm-none-eabi) and natively on macOS via pybind11. There is no separate desktop simulation — the code under test *is* the firmware code. Platform differences are confined to a thin platform header; DSP logic is identical across targets.

**Static graph topology, generated at design time.** Pipelines are expressed as direct C++ function calls, not a runtime graph framework. Claude generates the connection code from a spec. This makes static graphs practical without the boilerplate cost that would otherwise force a dynamic system. Each algorithm gets freshly generated concrete code, not a reused framework.

**Python is the test harness only.** Python drives pybind11-wrapped C++ blocks, generates input signals, collects outputs, and plots results. Do not implement DSP logic in Python.

**No dynamic memory allocation in the audio render callback.** Allocation during module construction is fine. For embedded targets, pure static allocation (fixed-size class member arrays) is required.

**Signal node probing.** Every block must expose internal state signals as additional outputs (envelopes, flags, computed values). Python taps any node in the pipeline for diagnosis without restructuring the graph. This pattern applies to all new blocks.

## Current State: Full Pipeline Working

The end-to-end pitch shifter pipeline is implemented and producing audio output:

```
Audio → ZC Detector (Faust) → zc_impulse ─────────────┐
Audio → Attack Detector (Faust) → attack_impulse        ├→ Loop Controller (C++)
                                                        ↓
                              tap1_delay_ms, tap2_delay_ms, gain1, gain2
                                                        ↓
Audio → Dual Tap Delay (Faust) ──────────────────────→ tap1, tap2
                                                        ↓
                              output = tap1 * gain1 + tap2 * gain2
```

Demo scripts:
- `audio-graph-python/examples/loop_controller_demo.py` — loop controller probe visualization
- `audio-graph-python/examples/pitch_shifter_demo.py` — full pipeline, saves output WAV

C++ module: `dsp_library/cpp/src/loop_controller.cpp` / `include/loop_controller.h`
Build: `cd audio-graph-python/build && make -f audio.make TARGET=loop_controller`

## Next Steps

- Listen to output and tune parameters (thresholds, crossfade durations, pitch_ratio)
- Fix zoomed panel in pitch_shifter_demo.py (sharex=True conflicts with mixed time units)
- Harmonic rejection in ZC Detector (dual LPF approach — see spec) once basic tuning is done
