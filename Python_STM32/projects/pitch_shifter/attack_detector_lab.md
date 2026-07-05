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
| `residue_track` | — | trough-averaging residue anchor (prototype, probe-only) |
| `fir_decimate` / `yin_frames` / `latch_period` | (consumes `yd.P`) | lab-only YIN stand-in — the Faust port takes the latched P as an input instead |

## The two paths

Same split as the Faust block — joined only at the outputs (see
`attack_detector.md` for the full design rationale).

- **Trigger** — edge detector producing `fires` (below).
- **Dive** — a note-end estimate driving `active_gain` muting downstream (below).

## Trigger path

Four mechanisms, composed in this order: a level qualification weights the
ratio, the edge detector fires on it, and two independent suppression
mechanisms (threshold hold, re-arm) keep one transient from firing twice.

**Core edge detector.** `fast` (`env_ar_accel` of `|audio|`, instant attack)
vs `ref` (a two-stage follower of `fast`); fire on a rising edge of the ratio
`fast/ref` across a live threshold `k` (rest value `k_nom` = 1.6).

**Double-fire suppression — threshold hold.** On each fire `k` snaps to 30,
**holds 15 ms, then drops fast** (8 ms TC) back to `k_nom`. The shape matters:
doubles are same-transient re-crossings within ~1–20 ms, while real retriggers
arrive 40+ ms later — so suppression should be brutal early and gone quickly.
A plain exponential is backwards for this (weakest exactly when doubles land,
still lingering when real attacks arrive).

**Double-fire suppression — re-arm.** A new edge only counts once the ratio
has dipped below `k_nom` since the last fire. This backs up the threshold
hold and is timing-free, so a false fire can't mask a later real attack.

**Level qualification.** A weight multiplies the ratio *before* edge
detection — deliberately separate from `k`, which stays level-independent.
A leaky previous-note-strength memory (`env_ar` of `fast`, ~30 ms up / ~8 s
leak, with a constant −45 dB floor it can't leak below) sets a bar ~30 dB
below the last real note; candidates below the bar are weighted out over a
10 dB soft band. This rejects string perturbations (fret rattle, brushes),
which sit far below the last real note.

**Startup.** The strength memory initializes at −10 dB and leaks to its floor
over ~3 s — equivalent to "a loud note just ended" — which removes the
file-start fire cluster by construction.

## Dive path — rev 3: period-commensurate energy window

The dive path produces `active_gain` — a soft [0,1] "note is alive" gain that
`loop_controller` uses to mute the delay-memory taps once a note ends. Full
rationale in `attack_detector_design_notes.md`; this section describes the lab
implementation top-down.

One idea drives the whole structure. At low E a live note's envelope ripples
at the period (~24 ms) and a hand damp completes on the same timescale, so no
fixed-length smoothing can separate the two. But energy integrated over
**exactly one period** of a periodic signal is constant — ripple-free by
construction — so the energy window tracks the note's period. Everything
below exists to serve that: the gate needs evidence signals, the evidence
signals need a ripple-free energy measure, and the energy measure needs the
period.

### Signal hierarchy

```
active_gain = smooth + onset pin                 ← policy (moves to loop_controller)
  of: alive_decay × alive_level × alive_floor    ← decision: soft memberships
  from: slope, p_db − onset_ref, p_db vs floor   ← evidence signals
  from: p_db — energy over one latched period    ← measurement
  from: latched P (lab YIN stand-in)             ← period source
```

### The gate — three soft memberships, combined as a product

Each membership is a `soft()` ramp answering one independent question about
the note; their product is the raw "note is alive" value:

- **`alive_decay`** — *"is the level falling faster than a ringing string
  would?"* The primary damp evidence, from `slope`.
- **`alive_level`** — *"is the note still audible relative to how it
  started?"* The rung-out evidence, from `p_db − onset_ref`. Secondary, so
  the onset reference only needs to be roughly right.
- **`alive_floor`** — *"is there any signal at all?"* An absolute floor on
  `p_db`. It guards `alive_decay`, whose log-slope gets noisy near silence.

```
alive_decay = soft(slope in [s_damp=−240 … s_edge=−60] dB/s)   # damp evidence
alive_level = soft(p_db − onset_ref in [−45 … −25] dB)         # rung-out evidence
alive_floor = soft(p_db in [−60 … −45] dBFS)                   # absolute floor
active_gain = smooth(alive_decay × alive_level × alive_floor)  # 1 = sounding
```

Why a product of soft memberships rather than a state machine: nothing
hardens into a mode. Each term pulls the gate down only while its evidence
lasts and recovers on its own when the evidence fades, so a bad reading
nudges the output and self-corrects.

### Evidence: `p_db` — one-period energy

Mean power over a true boxcar of exactly the latched period (cumsum trick),
in dB. For a periodic signal this is ripple-free by construction, whatever
the waveform shape. Measured on "Longer Bass Notes.wav", mid-note envelope
ripple drops from ~2–3 dB (fixed 25 ms window) to ~0.2–0.5 dB.

### Evidence: `slope` — decay rate

The dB change across exactly one period, expressed as dB/s, then smoothed
25 ms. The rate separation is what makes it robust primary evidence:

- a live note decays at ≈ −9 dB/s;
- a damp runs −500 dB/s or faster.

The heavy smoothing rejects genuine ~20 Hz string-beat AM on 2H-dominant
notes — which no window length can remove — at almost no damp-latency cost:
a damp still crosses the `s_edge` knee in < 10 ms.

### Evidence: `onset_ref` — note-level reference

A leaky reference (dB) for what "this note, at full strength" means
(`onset_ref_track`). Three behaviours:

- **fast-tracks for 30 ms after each fire** — so it settles at the
  early-sustain level, not the attack peak (which sits well above what the
  note settles to);
- **drifts up on undershoot** — if the level rises well above it with no
  fire, it follows anyway; this breaks the missed-attack → stale-reference
  loop;
- **leaks down only very slowly** otherwise.

### Period source — lab YIN stand-in

`fir_decimate` ÷8 → `yin_frames` CMNDF → `latch_period`: an offline
substitute for the pipeline's `yd.P` latch (the Faust port consumes `yd.P`
directly via a new graph edge instead). The latch:

- updates only from confident frames;
- holds through confidence dips;
- resets to a 25 ms fallback (one low-E period) on each fire — "invalidate
  on attack".

The picker prefers the **doubled lag** whenever it is also a deep null: for
the energy *window*, an octave down is harmless (two periods is still
commensurate), while an octave up (P/2 on a 2H-dominant note) leaves the
fundamental rippling.

### Policy layer — gate smoothing and onset pin

Policy layered on the evidence (the design notes' evidence-vs-policy split —
this part moves to `loop_controller` at port time):

- **asymmetric smoothing** — close fast (2 ms), reopen slow (50 ms);
  anti-flutter;
- **onset pin** — each fire snaps the smoother state open and holds the gate
  up (40 ms hold, 40 ms decay, scaled by post-attack level). Without it, the
  transient's fast settle reads as a partial damp.

### A/B against the old path

The previous fast/slow RMS-ratio path is still computed and overlaid dashed
in the gate panel. Reference file: "Longer Bass Notes.wav" — the old path's
mid-note `active_gain` dips (its live-decay-reads-as-partial-end problem) sit
at 0.84–0.96 there; the rev-3 gate holds 1.000.

## Absolute floors — inventory (known liability)

Design rule: every decision in this detector must be **level-relative**. The
instrument's volume knob sits upstream of this DSP, and between-note residue
is string perturbation — mechanical, non-flat spectrum — which scales with
the knob exactly like notes do. An absolute dBFS constant therefore cannot
separate junk from signal at more than one knob setting. The rule is
embodied in the ratio trigger, the note-memory qualification bar, and
`onset_ref`; four absolute floors nevertheless remain, each added as a guard
for the same degenerate regime ("no real note for a long time"):

| constant | value (dBFS) | role | what it guards |
|---|---|---|---|
| `mem_floor_db` | −45 | trigger-qual memory can't leak below (bar bottoms at −75) | long silence must not open qualification to digital-silence / file-start junk |
| `floor_lo/hi` (`alive_floor`) | −60 … −45 | third gate membership; also scales the onset pin | the only term closing the gate once `onset_ref` has leaked down (~10 s) and slope reads ~0 in stationary residue |
| `cap_floor_db` | −50 (+15 dB ramp) | onset-capture weight | a spurious fire in a quiet tail must not drag `onset_ref` down to the junk level |
| `frame_floor` | −55 | frames below it can't latch a period | the YIN latch must not lock onto between-note junk |

(The −10 dB trigger-memory startup init is also absolute but transient — it
leaks away over 3 s and never binds again.)

All four assume real notes sit above ≈ −45 dBFS, which fails as soon as the
volume knob comes down — so they are **provisional guards, not design**.
Measured (2026-07-04): between-note residue — mostly imperfect-muting string
content, non-flat spectrum — typically sits ~20 dB below note level, with
best-mute troughs near −40 dB relative. Typical residue therefore sails
*over* every floor even at full knob; the floors catch only deep troughs and
digital silence.

### Residue anchor — prototype (probe-only)

`residue_track` is the candidate replacement: a trough-averaging tracker of
`p_db` giving a data-derived **bottom anchor** for the level bracket
(`onset_ref` is the top). Once trusted, the four floors become relative
offsets from it. Not yet wired into any membership — it only plots in the
energy panel. Behaviour:

- **down** — one-pole (0.2 s) into troughs: settles within a between-note
  gap, doesn't chase one lucky deep mute;
- **up** — slew-limited (0.5 dB/s, *not* a one-pole, which would converge
  most of the way to note level during a sustain): a 10 s sustained note
  drifts the anchor up only ~5 dB;
- **fast recovery** — when `p_db` sits more than 25 dB above the anchor
  (just past the ~20 dB note-to-residue separation) the up-slew switches to
  30 dB/s, so after prolonged silence the anchor lands near note −25 within
  ~2 s, then the slow slew and real troughs finish the job. Recovery after
  silence is imperfect but quick, by design.

The asymmetry is deliberate: anchor-too-*high* is the dangerous error
(derived floors could gate real quiet notes) and recovers via the fast down
pole; anchor-too-*low* is benign — merely under-protective, i.e. today's
status quo — and may recover slowly. Measured on "Bass Notes Bad Trigger"
the bracket reads `onset_ref` ≈ −12, anchor ≈ −34…−42, median separation
23.5 dB — consistent with the hand-measured ~20 dB.

## Panels

1. Input waveform (with fire dots)
2. Trigger envelopes in dB — `fast`, `ref`, `ref × k` threshold (clipped), qual bar
3. Qualified ratio (bold; raw ratio faint) vs live threshold `k`
4. Lab YIN → latched period (= energy window; 25 ms fallback, reset on attack)
5. Commensurate-window energy (dB) — onset reference (top anchor), residue
   anchor (bottom, prototype), alive_level band
6. Decay rate (dB/s) vs the `s_edge` / `s_damp` knees
7. Note-end gate — the three memberships, their raw product (evidence,
   pre-policy), the policy-smoothed `active_gain`, and the old
   fast/slow-ratio gate (dashed) for A/B

## Test files

`files_to_run` at the bottom of the script (from repo-root `test_audio/`).
"Longer Bass Notes.wav" is the reference for the dive-path low-note work.
