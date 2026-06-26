# Pitch Shifter — pipeline

Output-side pitch shifter for bass guitar. It reads a triple-tap fractional delay
line at a pitch-scaled rate, and periodically jumps the read pointer back by
exactly one period — the precise period `P` from the YIN detector — so each splice
is phase-matched *by periodicity* and no explicit splice point is needed.
`pitch_ratio` 0.5 = one octave down (runtime-adjustable).

Signal flow — left output channel is the dry (raw) input, right is the shifted output:

```
audio ─┬─→ lpf ─┬─→ atk ─(trigger, active_gain)─┐
       │        ├─→ yd  ─(P, aperiodicity)──────┴─→ lc ──┬─(3 tap delay_ms)─→ dtd
       │        └──────────────(audio_in)────────────────────────────────────→ dtd
       │                                                  │                     │
       │                                             (3 gains)             (3 taps)
       │                                                  ▼                     ▼
       │                                                  └──→ mixer3 ◄─────────┘
       │                                                         │
       │                                                         └─→ audio_out_r  (shifted)
       └───────────────────────────────────────────────────────────→ audio_out_l  (dry)
```

`lc` (loop_controller) is the hub: the attack detector and the YIN detector feed
it, and it drives both `dtd` (the three tap delay times) and `mixer` (the three tap
gains). `dtd` reads the band-limited delay line that `lpf` fills and emits the three
taps that `mixer` sums. The dry left output taps the *raw* input ahead of `lpf`.

The loop clock is the YIN detector's period `P`: when the active tap's latency has
grown past the operating point, the controller jumps the read back by `k·P` (k = 1
in steady state). Because the jump is an integer number of periods, the waveform
lines up regardless of *where* in the period the jump lands — so the old peak-clock
apparatus (a pitch-detector filter bank plus a zero-crossing detector that supplied
splice points) is gone.

The wiring is defined in [`pitch_shifter.graph`](pitch_shifter.graph); each block
has its own doc beside its source.

## Modules

- [Input Low-Pass Filter](input_lpf.md) — `lpf` (Faust): band-limits the input ahead of the detectors and the delay line.
- [Attack Detector](attack_detector.md) — `atk` (Faust): boosted-threshold transient trigger, plus a dive note-end detector that drives output muting (`active_gain`).
- [YIN Detector](../yin/yin_detector.md) — `yd` (C++): decimated brute-force YIN; emits the precise period `P` (full-rate samples) and an `aperiodicity` confidence (low = confident). Replaces the old pitch-detector bank + zero-crossing detector. (Source lives in `dsp_cpp/`, pulled in cross-project; the authoritative spec is in `projects/yin/`.)
- [Loop Controller](loop_controller.md) — `lc` (C++): owns all tap delays and gains; the `k·P` loop policy, attack response, and bailout.
- [Triple-Tap Delay](triple_tap_delay.md) — `dtd` (Faust): one shared buffer, three independent fractional read taps.
- [Mixer3](mixer3.md) — `mixer` (C++): stateless weighted sum of the three taps.
