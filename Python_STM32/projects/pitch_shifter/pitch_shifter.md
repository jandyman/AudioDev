# Pitch Shifter — pipeline

Output-side pitch shifter for bass guitar. It reads a triple-tap fractional delay
line at a pitch-scaled rate, and periodically jumps the read pointer back by
exactly one period — the precise period `P` from the YIN detector — so each splice
is phase-matched *by periodicity* and no explicit splice point is needed.
`pitch_ratio` 0.5 = one octave down (runtime-adjustable).

Signal flow — left output channel is the dry (raw) input, right is the spliced
output (dry/wet crossfade over the shifted signal):

```
audio ─┬─→ lpf ─┬─→ atk ─(trigger, active_gain)─┐
       │        ├─→ yd  ─(P, aperiodicity)──────┴─→ lc ──┬─(3 tap delay_ms)─→ dtd
       │        └──────────────(audio_in)────────────────────────────────────→ dtd
       │                                                  │                     │
       │                                             (3 gains)             (3 taps)
       │                                                  ▼                     ▼
       │                                                  └──→ mixer3 ◄─────────┘
       │                                                          │ (wet)
       ├─────────(dry)──→ splice ◄────────────────────────────────┘
       │                    │ ▲──(atk: trigger, dive_strength)
       │                    └─→ audio_out_r  (spliced)
       └──────────────────────→ audio_out_l  (dry)
```

`lc` (loop_controller) is the hub: the attack detector and the YIN detector feed
it, and it drives both `dtd` (the three tap delay times) and `mixer` (the three tap
gains). `dtd` reads the band-limited delay line that `lpf` fills and emits the three
taps that `mixer` sums. `splice` crossfades the mixer's wet output against the raw
dry input on attacks and note ends. The dry left output taps the raw input ahead
of `lpf`.

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
- [Output Splicer](output_splicer.md) — `splice` (C++): dry/wet crossfade on the output, driven by attack and note-end events.

## Design notes — splice policy and pitch layers (2026-07-03)

Forward-looking; to be picked up once the attack-detector dive redesign
(`attack_detector_design_notes.md`) lands and we return here to evaluate the
ensemble.

### Splice policy — be live *before* the attack, not at it

The attack-time crossfade preserves the pluck's character only if the output
reaches the dry signal within ~10 ms of the onset — a tight budget to hit
*reactively*. The goal is that in the common cases the output is **already on
the live signal when the attack arrives**, so attack fidelity never depends on
detection + crossfade speed. Case by case:

- **Damped note** — the note-end detection fades the output to dry when the
  damp happens (the current latched `e_noteend` already does this). By the
  next attack the output is live.
- **Note ringing out to nothing** — no damp event fires, so this needs a
  **"last note amplitude"** reference: latch the note's level at onset and
  declare the note over when the current level falls far below *its own*
  amplitude (note-relative, like the rest of the dive redesign). The reference
  **must leak** toward the current level over seconds: if the player turns the
  bass volume knob down, a stale loud reference would read all subsequent soft
  playing as "rung out" (and a stale soft reference would never end a note).
- **Connected / legato notes** — there is no silent gap and no clean isolated
  transient to preserve; the new attack's fidelity doesn't matter, so the
  reactive attack-time snap is acceptable there (and is masked anyway).

The reactive ~10 ms attack crossfade stays as the fallback for any attack that
arrives with the output still wet — it is the safety net, not the design point.

### Two pitch detectors, two homes

- **Slow (YIN, ~50 ms)** — now also feeds the **attack detector's** dive path:
  the period-commensurate energy window (see the design notes) uses the
  latched P. New `yd.P → atk` edge in the graph when the redesign is ported.
- **Fast (early-cycle naive detector)** — works very well on clean attacks,
  poorly on dead notes. Its home is the **loop controller**, not the attack
  detector: it could start the loop earlier than the ~50 ms operating point on
  clean attacks, and its dead-note unreliability is harmless there because
  aperiodicity gating ignores pitch estimates exactly when they're untrusted.
  Future track; not part of the current redesign.

This is the layered-latency principle from the attack-detector notes applied
pipeline-wide: ~1 ms attack trigger (energy edges only) → tens-of-ms energy
layer → ~50 ms pitch layer, each refining downstream behaviour, never
re-deciding an earlier layer's call.
