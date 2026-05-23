# PitchShifter Project - Claude Context

Real-time downward pitch shifter for bass guitar. Dual delay lines with intelligent loop-point detection over a shared delay buffer; near-zero pitch shift up, arbitrary shift down (octave dropper, sub-bass, etc.).

The authoritative algorithm description lives in **`Pitch Shifter concept.md`** (this folder). Read it first when working on pitch shifter logic. This file is project context only — it does not duplicate the algorithm.

## Current State

End-to-end pipeline is implemented and producing audio output:

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

Code locations (work is currently split across folders; will be collapsed into Python_STM32 ecosystem later):
- Concept doc: `PitchShifter/Pitch Shifter concept.md`
- Faust modules: `dsp_library/faust/{zero_crossing_detector,attack_detector,dual_tap_delay}.dsp`
- Loop controller (C++): `dsp_library/cpp/src/loop_controller.cpp` + `include/loop_controller.h`
- Python demos: `audio-graph-python/examples/{loop_controller_demo,pitch_shifter_demo,attack_detector_demo,dual_tap_delay_demo,crossfade_pitch_shift_demo}.py`
- Build (native pybind11): `cd audio-graph-python/build && make -f faust.make DSP=<name>` or `make -f audio.make TARGET=loop_controller`

## Development Ordering

**Loop-first.** Tune loop-point detection on sustained signals before reintroducing the attack detector. Attack handling is deferred until basic loop behaviour is validated.

**Why:** loop logic in isolation is simpler to diagnose; we also don't yet know how important attack handling will turn out to be in practice — that question is best answered after the sustain case works.

When demoing with the attack detector bypassed, force `attack_impulse = 0` rather than removing the wiring, so it's a one-line flip to bring it back.

## Planned Changes (not yet implemented)

- **Three-tap delay (instead of two).** Required to handle attacks that arrive mid loop-crossfade — see *Attack interrupting a loop crossfade* in the concept doc's Open Issues. Will be implemented after loop logic is tuned.
- **Low-latency lowpass preprocessor (~10 kHz).** Ahead of all detectors and the delay buffer. Bass has no useful content above 10 kHz, and 2nd-order biquad group delay is negligible in band.
- **Harmonic rejection in ZC detector.** Dual-LPF energy-switching design described in the concept doc. Deferred until basic loop tuning is done.

## Retired

- MaxMSP / `max_externals/dual_tap_delay_tilde` — no new Max work. Existing Max experiments are not a migration target.
- The `Potential Implementation Targets` section that used to live here — implementation choice has been made (Faust modules + C++ loop controller, both pybind11-wrapped for the Python test harness, same C++ targets STM32 unchanged).

## Bass Guitar Frequency Reference

- E1 (41 Hz) to D4 (294 Hz) typical playing range
- Fundamental periods: ~3.4 ms to 24.4 ms (input domain)
- Output-domain periods at octave drop: ~6.8 ms to 48.8 ms
- ZC qualifier and loop matching are sized for A1 (55 Hz) up to ~2.5 octaves above (~311 Hz)
