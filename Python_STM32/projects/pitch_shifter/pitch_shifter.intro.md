# Pitch Shifter — pipeline

Output-side pitch shifter for bass guitar. It detects loop points (zero
crossings and note attacks) on the input, reads a triple-tap fractional delay
line at a pitch-scaled rate, and crossfades between taps to splice loops
seamlessly. `pitch_ratio` 0.5 = one octave down.

Signal flow — left output channel is the dry input, right is the shifted output:

```
audio → lpf ─┬─→ zc  ───────────────→ loop_controller (zc_impulse)
             ├─→ atk ───────────────→ loop_controller (trigger + active_gain)
             ├─→ hr  ───────────────→ loop_controller (P / sigma / qualified)
             └─→ dtd (triple-tap delay)
loop_controller → 3 tap delays + 3 gains → dtd → mixer3 → audio_out_r
```

The sections below document each block **in topological order** (the order the
pipeline runs them). Each block's `inputs` / `outputs` line is generated from
its `@block` marker, so it cannot drift from the code.
