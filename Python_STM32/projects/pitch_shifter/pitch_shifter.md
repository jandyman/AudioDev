# Pitch Shifter — pipeline

Output-side pitch shifter for bass guitar. It detects loop points (zero
crossings and note attacks) on the input, reads a triple-tap fractional delay
line at a pitch-scaled rate, and crossfades between taps to splice loops
seamlessly. `pitch_ratio` 0.5 = one octave down.

Signal flow — left output channel is the dry input, right is the shifted output:

```
audio ─┬─→ lpf ─┬─→ zc  ─(zc_impulse)──────────┐
       │        ├─→ atk ─(trigger, active_gain)─┤
       │        ├─→ hr  ─(P, sigma, qualified)──┴─→ lc ──┬─(3 tap delays)──┐
       │        │                                        │                 ▼
       │        └─────────────────(audio_in)────────────────────────────→ dtd
       │                                                 │                 │
       │                                          (3 gains)            (3 taps)
       │                                                 ▼                 ▼
       │                                                 └──→ mixer3 ◄──────┘
       │                                                        │
       │                                                        └─→ audio_out_r
       └────────────────────────────────────────────────────────────→ audio_out_l  (dry)
```

`lc` (loop_controller) is the hub: the detectors feed it, and it drives both `dtd`
(the three tap delay times) and `mixer3` (the three tap gains). `dtd` reads the
delay line that `lpf` fills and emits the three taps that `mixer3` sums.

The wiring is defined in [`pitch_shifter.graph`](pitch_shifter.graph); each block
has its own doc beside its source.

## Modules

- [Input Low-Pass Filter](input_lpf.md) — `lpf` (Faust): band-limits the input ahead of all detectors.
- [Zero-Crossing Detector](zero_crossing_detector.md) — `zc` (Faust): qualified positive-going crossings as loop-point candidates.
- [Attack Detector](attack_detector.md) — `atk` (Faust): boosted-threshold transient trigger, plus a dive note-end detector that drives output muting.
- [Harmonic Rejector](harmonic_rejector.md) — `hr` (C++): a trusted period estimate `P` for the loop-length gate.
- [Loop Controller](loop_controller.md) — `lc` (C++): owns all tap delays and gains; loop crossfades, attack response, bailout.
- [Triple-Tap Delay](triple_tap_delay.md) — `dtd` (Faust): one shared buffer, three independent fractional read taps.
- [Mixer3](mixer3.md) — `mixer` (C++): stateless weighted sum of the three taps.
