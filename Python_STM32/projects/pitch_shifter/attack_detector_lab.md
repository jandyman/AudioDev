# Attack Detector Lab

`attack_detector_lab.py` is the pure-Python/numpy experimentation space for the
bass attack detector — **no Faust, no chunking, no build step**: edit, run in
PyCharm, plots refresh. It is the *design* half of the tuning workflow; the Faust
block `dsp_faust/attack_detector.dsp` is the *port* half. The intent is that they
stay **verified-equal mirrors** — tune here, port there, confirm `lab == Faust` on
the bass test files. Read this alongside `dsp_faust/attack_detector.md`, which
describes the shared design; this file covers only what is specific to the lab.

> **Sync status:** the dive path has been redesigned in the lab (rev 3 —
> period-commensurate window, below) and is currently **well ahead of** the
> Faust block, which still carries the older difference-form RMS dive. The
> port also needs a new `yd.P → atk` graph edge (the block consumes the
> latched period). Port it back and re-verify `lab == Faust` once the tuning
> settles. Design rationale: `attack_detector_design_notes.md`.

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
| `onepole_smooth` | — | symmetric one-pole (tracks both directions; for signed signals) |
| `onset_ref_track` | — | leaky note-level onset reference (rev-3 dive path) |
| `fir_decimate` / `yin_frames` / `latch_period` | (consumes `yd.P`) | lab-only YIN stand-in — the Faust port takes the latched P as an input instead |

## The two paths

Same split as the Faust block — joined only at the outputs (see
`attack_detector.md` for the full design rationale).

- **Trigger** — `fast` (`env_ar_accel` of `|audio|`, instant attack) vs `ref` (a
  two-stage follower of `fast`); fire on a rising edge of `fast/ref` across a
  live threshold `k` (rest 1.6). On each fire `k` snaps to 30 and **holds
  15 ms, then drops fast** (8 ms TC) — doubles are same-transient re-crossings
  within ~1–20 ms, real retriggers arrive 40+ ms later, so suppression is
  brutal early and gone quickly (a plain exponential is backwards for this).
  A **re-arm condition** backs it up: a new edge only counts once the ratio
  has dipped below `k_nom` since the last fire — timing-free, so a false fire
  can't mask a later real attack. Produces `fires`.
  A **level qualification** multiplies the ratio before edge detection —
  deliberately separate from `k` (which stays level-independent): a leaky
  previous-note-strength memory (`env_ar` of `fast`, ~30 ms up / ~8 s leak,
  with a constant −45 dB floor it can't leak below) sets a bar ~30 dB down;
  candidates below it are weighted out over a 10 dB soft band. Rejects string
  perturbations (fret rattle, brushes), which sit far below the last real note.
  The memory initializes at −10 dB and leaks to its floor over ~3 s ("a loud
  note just ended") — this removes the file-start fire cluster by construction.
- **Dive** — a note-end estimate driving `active_gain` muting downstream (below).

## Dive path — rev 3: period-commensurate energy window

Full rationale in `attack_detector_design_notes.md`; the lab implements it as:

- **Lab YIN stand-in** (`fir_decimate` ÷8 → `yin_frames` CMNDF → `latch_period`)
  — an offline substitute for the pipeline's `yd.P` latch. Confident frames
  update a per-sample latched period; the latch holds through dips and resets
  to a 25 ms fallback on each fire ("invalidate on attack"). The picker prefers
  the **doubled lag** whenever it is also a deep null: for the *window* use an
  octave down is harmless (2 periods is still commensurate) while an octave up
  (P/2 on a 2H-dominant note) leaves the fundamental rippling.
- **`p_db`** — mean power over a true boxcar of exactly the latched period
  (cumsum trick), in dB. For a periodic signal this is ripple-free by
  construction; measured on "Longer Bass Notes.wav" it cuts mid-note envelope
  ripple from ~2–3 dB (fixed 25 ms window) to ~0.2–0.5 dB.
- **`slope`** — dB change across exactly one period, expressed as dB/s, then
  smoothed 25 ms. A live note decays at ≈ −9 dB/s; a damp is −500 dB/s or
  faster. The heavy smoothing rejects genuine ~20 Hz string-beat AM on
  2H-dominant notes (which no window can remove) at almost no damp-latency
  cost — a damp still crosses the knee in < 10 ms.
- **`onset_ref`** (`onset_ref_track`) — leaky note-level reference (dB):
  fast-tracks the level for 30 ms after each fire (settling at the
  early-sustain level, not the attack peak), drifts up on undershoot (breaks
  the missed-attack → stale-reference loop), leaks down only very slowly.
- **Soft memberships**, combined as a product — nothing hardens into a mode:

```
alive_decay = soft(slope in [s_damp=−240 … s_edge=−60] dB/s)   # damp evidence
alive_level = soft(p_db − onset_ref in [−45 … −25] dB)         # rung-out evidence
alive_floor = soft(p_db in [−60 … −45] dBFS)                   # absolute floor
active_gain = smooth(alive_decay × alive_level × alive_floor)  # 1 = sounding
```

The gate smoothing is **policy layered on the evidence** (see the design notes'
evidence-vs-policy split — this part moves to `loop_controller` at port time):
asymmetric close-fast (2 ms) / reopen-slow (50 ms) anti-flutter, plus an
**onset pin** — each fire snaps the smoother state open and holds the gate up
(40 ms hold, 40 ms decay, scaled by post-attack level) through the transient's
fast settle, which would otherwise read as a partial damp.

The previous fast/slow RMS-ratio path is still computed and overlaid dashed in
the gate panel for A/B comparison. Reference file: "Longer Bass Notes.wav"
(the mid-note `active_gain` dips of the old path — its live-decay-reads-as-
partial-end problem — sit at 0.84–0.96 there; the rev-3 gate holds 1.000).

## Panels

1. Input waveform (with fire dots)
2. Trigger envelopes in dB — `fast`, `ref`, `ref × k` threshold (clipped), qual bar
3. Qualified ratio (bold; raw ratio faint) vs live threshold `k`
4. Lab YIN → latched period (= energy window; 25 ms fallback, reset on attack)
5. Commensurate-window energy (dB) vs leaky onset reference (+ alive_level band)
6. Decay rate (dB/s) vs the `s_edge` / `s_damp` knees
7. Note-end gate — `alive_decay`, `alive_level`, their product `active_gain`,
   and the old fast/slow-ratio gate (dashed) for A/B

## Test files

`files_to_run` at the bottom of the script (from repo-root `test_audio/`).
"Longer Bass Notes.wav" is the reference for the dive-path low-note work.
