# Attack Detector Lab

`attack_detector_lab.py` is the pure-Python/numpy experimentation space for the
bass attack detector — **no Faust, no chunking, no build step**: edit, run in
PyCharm, plots refresh. It is the *design* half of the tuning workflow; the Faust
block `dsp_faust/attack_detector.dsp` is the *port* half. The intent is that they
stay **verified-equal mirrors** — tune here, port there, confirm `lab == Faust` on
the bass test files. Read this alongside `dsp_faust/attack_detector.md`, which
describes the shared design; this file covers only what is specific to the lab.

> **Sync status:** the dive path has been redesigned in the lab (RMS-ratio, below)
> and is currently **ahead of** the Faust block, which still carries the older
> difference-form RMS dive. Port it back and re-verify `lab == Faust` once the
> tuning settles.

## Contract

Two functions you edit; everything else is driver boilerplate:

- **`compute(audio, sr) -> dict`** — runs the detector on a whole file at once
  (no chunking) and returns a dict of named signals to plot, plus `'fires'` (int
  sample indices of triggers). The driver adds `sigs['audio']` for convenience.
- **`plot_panels(axes, sigs, t)`** — draws each panel from `sigs[<name>]`. Set
  `NUM_PANELS` to match the number of panels you draw.

The driver loads each file in `files_to_run`, calls `compute`, builds a sharex'd
vertical stack of `NUM_PANELS` subplots, overlays fire markers on every panel
(big red dots on the audio panel), and installs scroll-wheel x-zoom (toolbar
Home resets). Numba accelerates the per-sample feedback loops ~50× if present;
it falls back to pure Python otherwise.

## Envelope primitives

Every follower takes its time constants in **seconds** plus `sr` (default 48 kHz)
and calls `tau_to_c` internally — callers pass times, never coefficients. Two
limits make the family general: an attack time of `0` is an instantaneous peak
track (`prev ← x`), and a hold/release time of `np.inf` is a perfect plateau
(coefficient 1.0). So the old dedicated peak-hold followers are just special cases
— a flat-hold peak track is `env_ar_hold(att_s=0, rel_hold_s=inf)`.

| lab function | Faust mirror | role |
|---|---|---|
| `env_ar` | `env_ar` | asymmetric attack/release one-pole |
| `env_ar_hold` | — | AR + two-stage (hold→drop) release; `att_s=0, rel_hold_s=inf` = flat-hold peak track |
| `env_ar_2attack_hold` | `env_ar_2attack` | two-stage attack **and** release (the `ref` follower) |
| `env_ar_accel` | `env_hold_accel` | accelerating release; `att_s=0` = instant peak track (the `fast` follower) |
| `env_hold_blend` | `env_hold` | attack + ramped hold→release |
| `rms_env` | `rms_env` | one-pole RMS (leaky integrator on x², then sqrt) |

## The two paths

Same split as the Faust block — joined only at the outputs (see
`attack_detector.md` for the full design rationale).

- **Trigger** — `fast` (`env_ar_accel` of `|audio|`, instant attack) vs `ref` (a
  two-stage follower of `fast`); fire on a rising edge of `fast/ref` across a live
  threshold `k` that boosts on each fire and decays back. Produces `fires`.
- **Dive** — a note-end estimate driving `active_gain` muting downstream (below).

## Dive path — fast/slow RMS ratio

The dive detector is a **fast-vs-slow envelope ratio** — the detector side of a
program-adaptive gate (a downward expander whose threshold is the slow envelope
rather than a fixed level). Three envelopes:

- **`rms`** — short-term energy, `rms_env` with a ~25 ms window (≈ one low-E
  period). RMS is the robust choice here: a peak-hold latches onto stray samples
  and **falls apart on irregular periods**, whereas RMS integrates energy over the
  window and doesn't care where the peaks land.
- **`hold_env`** — short-term follower of `rms` (`env_ar_hold`).
- **`slow_env`** — slow-release reference (`env_ar` of `rms`, ~1 s release ≈
  bass-string ring-down).

```
active_gain   = clip(hold_env / slow_env, 0, 1)     # 1 = sounding, → 0 = ended/damped
dive_strength = 1 - active_gain
```

The ratio is the natural form. Algebraically `hold/slow == 1 − (slow−hold)/slow`,
so it is the *same quantity* as the old difference-based `dive_strength` — but the
difference form clamps every moment where `hold > slow` to exactly 1, so its
ripple appears as one-sided downward dips; the ratio swings cleanly around 1. (The
textbook version does this in dB: `20·log10(hold/slow)` through a threshold/range
gate curve — same idea, perceptually linear, no divide-by-small sensitivity.)

**Remaining issue — natural decay vs damp.** `slow_env` decaying slower than a
naturally ringing note pulls the ratio under 1 mid-note (a live decay reads as a
partial end). Distinguishing a damp from natural decay fundamentally requires
reading the *rate* of amplitude fall, so ~one period is the response floor. The
main tuning knob is `slow_release` set to the bass's natural ring-down, so the
ratio hovers near 1 through a live note and drops clearly on a real damp — i.e.
the gate threshold tracks the program. Reference file: "Longer Bass Notes.wav".

## Panels

1. Input waveform (with fire dots)
2. Trigger envelopes — `fast`, `ref`, `ref × k` threshold (clipped)
3. Ratio `fast/ref` vs live threshold `k`
4. Dive envelopes — `rms`, `hold_env`, `slow_env`
5. Note-end gate — `active_gain = hold_env / slow_env`

## Test files

`files_to_run` at the bottom of the script (from repo-root `test_audio/`).
"Longer Bass Notes.wav" is the reference for the dive-path low-note work.
