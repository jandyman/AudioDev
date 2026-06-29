# keybass_1 — Processing Architecture & Design

**Design doc (in flux).** This is the plan for the *processing* version of
keybass_1: turning a bass guitar into the synth-bass voice we prototyped, by
driving that voice from the bass signal's own period. It is distinct from the two
**background** threads (`docs/Billy Ocean Thread.pdf`,
`docs/Pulse wave sync aliasing reduction techniques.pdf`), which are reasoning
transcripts, not design — this doc is the spec we build from. Open questions are
called out explicitly; expect a fair amount of soundfile experimentation before
anything settles into Faust/C++.

## Goal

Drive the existing synth voice — raised-cosine **bandlimited pulse → ADSR → 24 dB
resonant LP** (see `pulse_generator.py`, `adsr.dsp`, `filter_sweep.dsp`) — from the
bass guitar, so the output follows what's played in pitch and time. The oscillator
stops being free-running: it becomes a **pulse train hard-synced to the bass's
period**, measured from the signal's extrema, with an envelope and filter on top.

This is the "waveform *constructor* driven by an event stream, not a phase
accumulator" reframe from the aliasing thread — the pulse is re-anchored to the
bass, not run open-loop.

## Pipeline

```
bass in → input_lpf → attack_detector ─┬─ trigger, fast_env, active_gain
                                        │
                       extremum / period+phase estimator (NEW)  ← fast_env, trigger
                       yin_detector ────┘  P, aperiodicity
                                        │
        estimator → synced pulse → resonant LP (cutoff ← VCF env)
                                 → × amplitude follow (fast_env) → out
```

Reuses the now-shared blocks: `dsp_faust/input_lpf`, `dsp_faust/attack_detector`
(gives `trigger`, `fast_env`, `active_gain` for free), `dsp_cpp/yin_detector`
(gives `P`, `aperiodicity`).

## Two estimators, distinct jobs

- **Extrema (peaks) → phase/timing + the early period.** They own the sync: every
  pulse anchor lands on a qualified extremum, and they deliver a usable period
  after ~1 cycle.
- **YIN → period validation + sustain robustness.** It is the sanity gate, not the
  clock.

Peaks always own the phase; YIN qualifies which extremum is the anchor and
confirms the period. Division of labor: **peaks = when, YIN = is-this-right.**

## The gap timeline

```
t0  attack trigger
t1  first anchor extremum     (shortly after t0)
t2  second anchor extremum    (= t1 + P → period known after ~1 cycle)
t3  YIN locks                 (~3 cycles)
```

- **[t0, t2): the blind gap (~1 period).** Fire pulse 1 at the trigger with a
  *guessed* width (no period yet). This gap is ~1 period, not YIN's ~3 — the big
  win of the peak method.
- **[t2, t3): peak-driven.** Period from anchor-to-anchor, **re-anchored every
  cycle**, so period error never accumulates and there is no phase drift between
  pulse and bass.
- **[t3, …): YIN up.** YIN validates anchor selection (expect the next anchor ~one
  YIN-period out); peaks still set the phase.

**Observed (small sample, to confirm):** YIN produces solid estimates *before* the
2nd harmonic becomes prominent, so there is no extended "peak-only while 2H grows"
danger window. The YIN-gated anchor selection in [t3, …) is cheap insurance for
long held notes where 2H eventually rises and could otherwise present a
shoulder-extremum that steals the phase anchor.

## Extremum detection & qualification

Detect extrema as **derivative zero-crossings** of the `input_lpf`-filtered signal,
with a single-pole LP on the derivative for noise immunity. An extremum is accepted
as an anchor only if **all** of:

1. **Curvature opposite-signed to the value** (the slope of the derivative:
   +slope before, −slope after a maximum). Passes positive-maxima / negative-minima;
   rejects extrema on the wrong side of zero (a sub-zero local max, a super-zero
   local min — i.e. one-sided ripple).
2. **`|value| > fast_env × k_qual`** — adaptive, envelope-normalized threshold
   (reuses `attack_detector.fast_env`). Rejects shallow extrema, including shallow
   2H shoulders.
3. **Refractory period** since the last accepted extremum (~just under the minimum
   expected period at the highest expected note). Rejects double-counts.

These three are complementary — each catches a failure the others miss.

**Subsample timing (Step 2):** 3-point parabolic interpolation on each accepted
extremum, `δ = ½·(y₋₁ − y₊₁)/(y₋₁ − 2y₀ + y₊₁)`, anchor time `= n + δ`. Tightens
the period estimate and only pays off paired with fractional pulse placement
(below). Deferred to Step 2 — Step 1 measures periods at sample resolution, which
is ample to test the basic idea (±1 sample on an ~800-sample period is noise).

**Self-calibrating polarity:** the first qualified extremum after the trigger
*defines* the anchor polarity for that note. Same-polarity extrema are the **anchor
extrema** (sync points); opposite-polarity extrema are cross-check only. No
absolute-polarity assumption → works on any bass / pickup / preamp inversion.

## Period, phase, confidence

- **Period** `Pₖ = t(anchorₖ) − t(anchorₖ₋₁)`.
- **Phase anchor** — a chosen phase of the pulse lands on each anchor extremum.
  *Which* phase (falling edge? center of the matching plateau?) is an open question
  (below).
- **Confidence (provisional model, tune on soundfiles):** interval agreement —
  `|Pₖ − Pₖ₋₁| / Pₖ < tol` builds confidence; out-of-tolerance resets it.
  Optionally weight by anchor-amplitude regularity. Cross-check the opposite-
  polarity half-period for octave errors. Once YIN is up,
  `agreement(P_peak, P_yin)` is the high-confidence signal.

## The first pulse (the guess)

At t0 there is no period. Width is `duty × P`, and P is unknown. Options to
evaluate: carry the previous note's P (good for legato/repeats), a default register
P, or fire only the leading edge at t0 and commit the width at t2 when P arrives.
Guiding principle from the threads: **continuity > accuracy** — the ear is itself
pitch-ambiguous this early, and the VCA attack + filter sweep mask the guess; we
re-anchor cleanly at t2.

## Fractional pulse placement (Step 2)

Subsample anchor timing is wasted if edges snap to integer samples — that
re-quantizes the anchor to ±0.5 sample and reintroduces the jitter parabolic interp
just removed. So pulse transitions must be placeable at a **fractional** sample
position.

Because we *construct* the waveform (not delay an existing one), the natural,
exact way is to **evaluate the raised-cosine edge analytically at the fractional
offset**: for an edge starting at continuous time `t0` with width `w`, sample `n`
takes `0.5·(1 − cos(π·(n − t0)/w))` across the edge. No phase quantization. Our
existing `pulse_generator.py` already does this (continuous phase → per-sample
raised cosine), so the Python prototype gets fractional placement for free.

For the embedded target that analytic edge becomes a **polyphase coefficient
bank** — the edge precomputed at K sub-sample phases (K × w coefficients), indexed
by `frac(anchor)`, with optional linear interpolation between the two nearest
banks. No runtime trig on the M7, fixed cost. K ≈ 16–32 (nearest bank) or K ≈ 8
(with inter-bank interp) keeps residual quantization (±1/2K sample) well below the
parabolic precision and below audibility.

Two consequences:
- The banks are just the **window-integral kernel sampled at K phases**, so the
  kernel choice (Hann → raised cosine, Blackman, …) and width N stay orthogonal
  knobs — swap bank contents, same machinery.
- This is the construction-side counterpart of **PolyBLEP**: same goal (a
  bandlimited edge at a fractional time), reached by construction. Because the edge
  is *already* bandlimited, fractional placement adds no aliasing — unlike a naive
  hard step, the case PolyBLEP exists to fix.

Plan: analytic evaluation in Python now; polyphase bank (the same coefficients,
tabulated) on the embedded target — guaranteed to agree, since the bank is the
analytic edge sampled.

## Jitter

Hard-syncing to every anchor is drift-free but inherits peak-timing jitter (worse
when 2H distorts the extremum location). Parabolic interpolation first; **measure
the jitter on real files before** adding any period smoothing — don't pre-optimize
the smoothing vs. lock-tightness tradeoff.

## Amplitude / dynamics

The pulse train's amplitude **follows the input envelope** (`fast_env` for now), so
the synth voice breathes with the player's dynamics instead of imposing a synthetic
shape. This is a notable departure from the synthesis prototype, which used a VCA
ADSR purely to give the note a clean start/stop: here `fast_env` already goes to ~0
between notes, so **input-envelope-following provides the note gating for free** and
supersedes that VCA ADSR. The filter sweep (VCF cutoff) stays an attack-triggered
envelope — that's the "Diamond" timbre and is independent of the amplitude path.

Open within this:
- **Pre- vs post-filter** placement of the amplitude multiply. Post-filter keeps the
  resonant filter seeing a constant-level pulse (consistent behavior, esp. near
  self-oscillation); pre-filter lets the filter respond to playing dynamics. Decide
  empirically.
- **`fast_env` vs a purpose-tuned follower.** `fast_env` (attack_detector's
  hold + accelerating-release peak track) is the starting source; its decay shape
  may or may not be the right amplitude contour for the voice — a dedicated
  follower with its own attack/release may replace it later.
- **Velocity tie-in.** `fast_env` at the trigger instant is a natural velocity
  signal — it could scale the VCF env depth (harder hit → brighter), linking the
  two paths.

## Step 1 — pure sensing (no synthesis, sample resolution)

Validate the core hypothesis before any audio generation: interpolation and
fractional placement are Step 2 (they refine precision once we make sound and don't
change whether the basic idea works). Step 1 measures everything at sample
resolution.

Build a Python diagnostic (using the `diagnostic_plot` toolset — shared-x panels,
`mark_events`, zoom) that runs the bass files through `input_lpf` +
`attack_detector` and a Python extremum detector, and overlays:

- the filtered signal with **qualified anchor extrema marked by polarity**,
- the (LP'd) derivative,
- `fast_env` (the amplitude-follow source) and the `fast_env × k_qual`
  qualification threshold,
- the running peak-to-peak period estimate,
- `yd.P` for comparison.

**Starting file:** `Bass Notes Bad Trigger 2.wav` (good variety). Expand to the
descending-into-low-E / 2H-dominant files once the detector behaves.

Goal: eyeball how reliably "the 2nd same-polarity extremum = the period" holds,
confirm YIN-before-2H, and tune the qualifiers (k_qual, refractory, derivative LP)
across files — **before** any DSP moves into Faust/C++.

## Open questions

- **Confidence metric** — concrete thresholds and whether amplitude regularity
  earns its place.
- **Phase anchor** — which pulse phase maps to the anchor extremum.
- **First-pulse width** — guess policy (previous P / default / defer to t2).
- **Estimator home** — a Python prototype first, then likely a C++ block (sibling
  to `loop_controller`); what it emits (P, anchor impulses, polarity, confidence).
- **Terminology** — using "extremum / extrema"; "anchor extremum" for the sync
  points. (Open to a better word.)
