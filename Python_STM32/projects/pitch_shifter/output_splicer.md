# Output Splicer

Dry/wet crossfade on the output, driven by the two events the `attack_detector`
already emits. The unprocessed (dry) signal is made live on a note end and on an
attack; in both cases the output blends back to the shifted (wet) signal.

```
out[n] = dry[n] * m[n] + wet[n] * (1 - m[n])      m in [0,1]
```

`m = 1` is dry live, `m = 0` is full wet. `m` is the max of two independent
envelopes that, by construction, don't fight:

- **`e_attack`** — a rising edge of `attack_trigger` snaps the output live with a
  fast `ATTACK_RISE_MS` (1 ms) ramp to full dry, then crossfades back to wet over
  `attack_to_wet_ms`. This lets the natural pluck transient through and **sharpens
  the attack**. It does *not* mask the YIN/loop onset latency: with a longer
  crossfade the shifted note is audibly arriving underneath the dry tail, so the
  effect is a transient sharpener, not a latency hider. Keep the crossfade short
  for a crisp attack; lengthen it only if you want the dry character to bleed
  further into the note.
- **`e_noteend`** — slews toward `dive_strength` (the note-end detector, 0→1 as a
  note dies) at a rate set by `note_end_fade_ms`, revealing the natural dry decay.

During the pluck `dive_strength` is low, so `e_attack` dominates; as the note dies
`e_attack` is long gone, so `e_noteend` dominates; mid-sustain both sit near 0 and
the output is full wet. When a new attack lands while the previous note is still
diving, `e_noteend` legitimately holds dry live a little longer past the attack
crossfade — the `max()` doing its job, not a glitch.

## Inputs / outputs

| Port | Dir | Meaning |
|------|-----|---------|
| `dry` | in | unprocessed signal (raw graph input) |
| `wet` | in | shifted signal (summed delay taps) |
| `attack_trigger` | in | attack impulse (`atk.trigger`) |
| `dive_strength` | in | note-end strength 0..1 (`atk.dive_strength`) |
| `out` | out | spliced output |
| `dry_mix` | out | the mix coefficient `m` (probe) |

## Parameters

| Param | Default | Meaning |
|-------|---------|---------|
| `attack_to_wet_ms` | 50 | crossfade time from full dry back to wet after an attack |
| `note_end_fade_ms` | 50 | slew time for the note-end fade toward dry |

`ATTACK_RISE_MS` (1 ms) is a fixed constant — short enough to keep the transient,
long enough to avoid a coefficient-jump click.
