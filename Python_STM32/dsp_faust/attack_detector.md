# Attack Detector

Bass-guitar transient detector. Two independent subsystems share the block,
joined only at its outputs:

- a **trigger** — the live edge detector that fires on a new note, and
- a **dive** detector — a note-end estimate that drives output muting downstream.

### Trigger — boosted-threshold edge detector

Level-invariant: it asks *"is this a step above what's sounding right now?"*, not
*"is this loud?"*.

- **`fast_env`** — peak-track of `|audio|` with a 25 ms hold and an accelerating
  release. The hold carries the per-cycle peak through one low-E period so it
  doesn't wobble; rise time is ~0 ms.
- **`ref_env`** — a two-stage-attack / two-stage-release follower **of**
  `fast_env`: the reference ceiling that `fast` is measured against. Its attack
  lags so a fresh transient opens a `fast/ref` gap:
  - *attack* — slow for a brief window after re-entering attack mode (fast pulls
    ahead → wider ratio spike → stronger detection), then fast to catch back up;
  - *release* — holds briefly, then drops, so `ref` dives along with `fast`
    between notes. A new attack therefore always sees a low `ref` and a clean
    spike regardless of the previous note's level (this is what makes legato work,
    where a within-cycle reference would have ridden up with the signal).
- **fire** = a rising edge of `fast/ref` across a **live threshold `k`** that
  rests at `k_nom`, snaps to `k_boost` on each fire, then decays back toward
  `k_nom`. The boost is an *overridable* holdoff: a within-note secondary peak
  sits under the fresh-and-tall bar and is suppressed, while a genuinely larger
  attack (ratio above the still-elevated `k`) fires through. Because the edge is
  tested against the *moving* threshold, a sustained-high ratio produces no new
  edge as `k` decays — no re-fire, and no debounce timer. Level independence
  holds because `k` rests at a fixed nominal value; only the post-fire holdoff
  is time-varying.

There is no absolute level threshold — noise-floor false fires are accepted
(too quiet to make an audible artifact, and `active_gain` mutes the output there
anyway).

### Dive — note-end detector (drives muting)

`hold_env` (a fast RMS peak) versus `slow_env` (a slow RMS, ~1 s release — a
natural string ring-down reference). When the player damps or articulates a note
end, `hold` falls fast while `slow` lags, and that gap is the dive:

```
dive_strength = clip((slow_env - hold_env) / slow_env, 0, 1)
active_gain   = 1 - dive_strength      # 1 = note sounding, 0 = ended / damped
```

`loop_controller` multiplies the pitch-shifted loop taps by `active_gain`, so the
output mutes during silence/damping. This path is kept entirely separate from the
trigger.

### Key parameters

| name | value | meaning |
|------|-------|---------|
| `k_nom` | 2.0 | resting threshold (fast/ref) |
| `k_boost` | 20.0 | threshold immediately after a fire |
| `k_decay_s` | 20 ms | boost decay time constant |

`fast`: 25 ms hold / 50 ms accel release. `ref`: 50 → 15 ms two-stage attack with
a 12 ms slow window, 25 ms release hold then 50 ms drop.

### Tuning workflow

Tuned in `attack_detector_lab.py` (pure Python/numpy — edit, run, plots refresh),
then ported to this `.dsp` with `lab == Faust` verified on the bass test files.
