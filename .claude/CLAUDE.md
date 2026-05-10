# AudioDev - Claude Context

Cross-project configuration for audio development work.

## Python Environment

Always activate the conda environment before running Python scripts:
```bash
source ~/miniforge3/etc/profile.d/conda.sh && conda activate scipy
```
This environment has numpy, matplotlib, dawdreamer, pybind11, and other dependencies needed for testing Faust modules and audio processing.

This environment is also required when building Faust modules for Python:
```bash
cd audio-graph-python/build
make -f faust.make DSP=attack_detector
```
The build needs pybind11 headers from the conda environment.

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

All DSP logic must be implemented in **Faust or C++**. Python is used exclusively as a test harness: loading compiled modules, generating control signals, running audio through them, and plotting/saving results. Do not implement DSP algorithms in Python.

**No dynamic memory allocation in the audio render callback.** Allocation during module construction is fine. For embedded targets, pure static allocation (fixed-size class member arrays) is preferred and avoids the issue entirely.

If concept development or debugging becomes difficult within Faust/C++, a Python prototype is acceptable as a temporary step, but the target implementation must always be Faust or C++.

The pattern of **multiple output probe signals** per module has been working well and should be continued. Each module should expose internal state signals (envelopes, flags, computed values) as additional outputs so they can be plotted in Python for diagnosis.

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
- `audio-graph-python/examples/pitch_shifter_demo.py` — full pipeline, saves output WAV, `--ratio` arg

C++ module: `dsp_library/cpp/src/loop_controller.cpp` / `include/loop_controller.h`
Build: `cd audio-graph-python/build && make -f audio.make TARGET=loop_controller`

## Next Steps

- Listen to output and tune parameters (thresholds, crossfade durations, pitch_ratio)
- Fix zoomed panel in pitch_shifter_demo.py (sharex=True conflicts with mixed time units)
- Harmonic rejection in ZC Detector (dual LPF approach — see spec) once basic tuning is done
