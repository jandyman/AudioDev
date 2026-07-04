# Attack Detector — Design Notes / Handoff (2026-07-03, rev 3)

Forward-looking notes from a design session, revised twice after review. The
*shipped* behaviour lives in `attack_detector.dsp` / `attack_detector.md`; the
lab and its RMS-ratio dive are in `attack_detector_lab.py` /
`attack_detector_lab.md`. This file captures the **open problems and the agreed
design direction** for the dive (note-end) path, not yet reflected in code.

## Where the code is now

- Lab envelope API unified (commit `61e0ceb`): every follower takes time
  constants in **seconds + sr** and calls `tau_to_c` internally; `tau_to_c(0)=0`
  (instant attack), `tau=inf → 1` (perfect hold). Peak-hold followers collapsed
  into the `env_ar_*` family.
- Dive path is now a **fast/slow RMS envelope ratio** (a program-adaptive gate):
  `active_gain = clip(hold_env / slow_env, 0, 1)`, `dive_strength = 1 − active_gain`.
  `rms` = 25 ms window; `hold_env`, `slow_env` are followers of it.
- **Not yet ported to Faust** — the lab dive path is ahead of the block.

## The central problem — damp vs ripple at low notes

This is the problem to solve **first**; everything else leans on it. At low E
the envelope of a live note ripples at the period (~24 ms), and a hand damp
completes on a comparable timescale. Any fixed smoothing long enough to remove
the ripple smears the damp by at least as much — the two live on the same
timescale, so **no time-invariant filter can separate them**. Every energy
detector tried so far has hit this wall.

It matters doubly because `active_gain` is not just a detector output — it is
the **audible gain signal** muting notes played back from delay memory. Ripple
on it is modulation distortion on the output. The once-per-loop hold in
`loop_controller` patches this; the real fix is an envelope that doesn't ripple
in the first place.

The way out is the way the eye does it. Reading the waveform, a decaying note
is recognizable because **each cycle has the same shape as the last, just
smaller** — the eye segments into periods and reads the scale factor between
them. That is period-synchronous comparison, and it is the information a
period-blind detector cannot access. Formally: for a periodic signal, energy
integrated over a window of **exactly one period is constant** — zero ripple by
construction, whatever the waveform shape. So:

**Core design: the dive-path energy window tracks the note's period.** Window
length follows the latched P from the YIN detector when one is available, and
rests at 25 ms (one low-E period) otherwise — the current fixed-window design
is literally the fallback mode. Consequences:

- The one-period energy envelope is ripple-free, so its **log-slope is the
  decay rate on a clean signal** — the primary damp evidence (below) computed
  without the ripple/decay confusion.
- `active_gain` becomes smooth **by construction**, replacing the once-per-loop
  hold with something principled rather than layering more smoothing on it.
- Solving low E with a commensurate window solves everything above it: higher
  notes fit more periods into any window and only get easier.

The P-dependence is *soft*, satisfying the constraint below: a stale or
slightly-wrong P leaks a little ripple — output degrades, no decision flips.
And the availability profile fits: P is missing only for the first ~50 ms of a
note, where `active_gain` should be pinned at 1 anyway (the attack just
re-armed everything); damps happen mid/late note, exactly when the
`loop_controller` latch holds a confident P. (Implementation flag: a true
boxcar via running-sum-minus-delayed-sum drifts in float32 on the STM32 — use
the leaky variant.)

**Why not peak detection** (considered, rejected): per-period energy is
phase-blind — by Parseval it is the sum of the harmonic powers, indifferent to
how H1 and H2 align. The composite waveform's *peak* depends on their relative
phase. A 2H-dominant note has two comparable peaks per period whose height
ordering evolves as the harmonics decay at different rates, so a peak-picker
swaps between them mid-note; since relative phase drifts, the peak envelope can
even rise while total energy falls. Peak detection measures a phase artifact;
commensurate-window energy is the robust version of the same idea.

**Free extra evidence — YIN aperiodicity.** The other half of the eye's read
("the shape does change") is shape consistency between adjacent periods, which
is essentially what `yd.aperiodicity` measures. On a damp, periodicity
collapses and it should jump, on top of the energy drop. It is decimated and
window-smeared, so possibly too slow to be primary — **before building
anything, pull up an existing probe plot of `yd.aperiodicity` around a damp in
"Longer Bass Notes.wav"** and see whether it responds usefully.

## Other open problems observed

1. **Double / missed triggers** (minor for the pitch shifter). User has ideas.
2. **`active_gain` wrong on two notes in succession** — a softer second note
   reads as the decay of the first and gets wrongly gated.
3. **Occasional missed attack** — appears when a note-end was never detected.
4. **`hold_env` dives slower than `fast_env`.** Measured after a hard note-off
   (1/e): `rms` 50 ms, `hold_env` 76 ms, `fast_env` 43 ms. Two causes:
   - the RMS **sqrt doubles the release TC** — a 25 ms window on x² reads out
     as a 50 ms amplitude decay (`sqrt(e^(−t/τ)) = e^(−t/2τ)`);
   - `hold_env`'s `rel_hold_s = 0.5 s` plateau over its first 28 ms adds ~26 ms.
   - The "feels like 200 ms" is the exponential *tail* (~3–4 TCs), not the TC.
   Cleanest fix: do the dive math in the **power or dB domain** and the sqrt
   (and its TC doubling) disappears — rather than hand-compensating windows.

## Root-cause understanding (problems 2 & 3)

**Slow references don't reset between successive notes.** `slow_env` (~1 s
release) and the trigger's `ref` outlive the note they reference, so note 2 is
measured against note 1's tail. A softer note-2 then reads as the *decay* of
note-1 → wrongly gated (prob. 2); a legato/soft note-2 makes too small a
`fast/ref` spike → missed fire (prob. 3).

And the two problems feed each other in a **loop**: a missed attack means no
re-arm, no re-arm means the reference goes staler, and a staler reference makes
the *next* attack easier to miss. Any fix that re-arms the reference *only* on
detected attacks rebuilds this loop one level up — the reference must also
recover on its own (the upward leak, below).

Deeper: the detector has plenty of *analog* memory (every one-pole has state)
but **no note-level memory** — nothing represents "a note started here, with
this strength." The running envelopes are note-agnostic; a human judges each
note *relative to its own onset*. That's the missing layer.

## Note-level memory anchored on the attack

At each confirmed fire, capture a per-note reference: onset strength and onset
time. Two corrections to how the reference is built:

- **Sample the early sustain, not the attack peak.** The transient peak of a
  plucked bass sits well above the level the note settles to. If the reference
  latches the fire-instant peak, "level relative to onset" reads low for the
  whole note. Track the RMS over the first few tens of ms after the fire and
  let *that* become the reference.
- **Give the reference an upward leak.** Besides fast-tracking on an attack
  (weighted by attack confidence), let it slowly track *upward* whenever the
  level rises well above it with no fire. This breaks the missed-attack loop:
  even if a fire is missed entirely, the reference re-arms eventually and the
  next attack is detectable again.

Note-end then becomes a **note-relative** question with two soft pieces of
evidence, combined as a product:

1. **Decay rate (primary).** "Is the level falling faster than a ringing
   string would?" — the local slope of the log of the (now ripple-free,
   period-commensurate) energy envelope. A natural bass ring-down (τ ≈ 1 s)
   loses ~0.2 dB per low-E period; a hand damp loses several dB per period — a
   20–40× rate separation, so no delicate threshold is needed. Self-anchoring
   (a badly-captured onset can't poison it); needs a level floor under it
   (log-slope gets noisy near silence).
2. **Level relative to onset (secondary).** "Is the note still loud compared
   to how it started?" — where the note-level reference is used. Being
   secondary, the reference only needs to be roughly right.

Each attack re-arms the reference, so note 2 self-references (fixes prob. 2).
The upward leak covers the case where the attack was missed (guards prob. 3).

## Layered-latency architecture

The output splice crossfades to the live signal on an attack (~10 ms budget to
preserve the pluck's character — see `pitch_shifter.md`), which pins the attack
decision to a hard latency budget **permanently**:

- **~1 ms — attack trigger**: raw energy edges only. May never depend on
  pitch, shape analysis, or anything windowed.
- **tens of ms — energy layer**: onset reference capture, dive evidence.
- **~50 ms — pitch layer**: YIN's P and aperiodicity; refines window sizing,
  gating, loop jumps.

Each later layer *refines* downstream behaviour; it never re-decides an earlier
layer's call. (The temptation this guards against: "the trigger would be
smarter if it knew the pitch." It would also be 50 ms late.) The slow pitch
layer now feeds the attack detector's dive path; the *fast* early-cycle pitch
detector idea deliberately does **not** — its home is the loop controller (see
`pitch_shifter.md`, design notes).

## Hostile use cases — dead notes and very short notes

Fixtures: the two "Bass Notes Bad Trigger" files. These impose constraints the
design must satisfy (and, by construction, does):

- **Dead notes run permanently in fallback mode.** No confident P ever arrives,
  so the window rests at 25 ms for the note's whole life. That's fine: ripple
  rejection matters for *sustained periodic* signal (a thump has no steady
  ripple), and a dead note loses several dB per 25 ms — the damp membership
  saturates even with a sloppy window. The dive path is arguably *more*
  important here: it stops the delay memory replaying stale thump after the
  note has died. Rule: **nothing in the dive path may break when P never
  arrives.**
- **Very short notes can be shorter than the onset-capture window.** A hard
  latch would capture garbage; the leaky confidence-weighted tracker ends up
  partially updated and then leaks — degraded, not wrong.
- **Refire speed.** A dead thump followed immediately by a real note is the
  double/missed-trigger territory of the bad-trigger files. The soft holdoff
  must let a genuinely bigger attack punch through quickly, and the re-armed
  references make the second fire detectable at all.
- **Emergent behaviour is graceful passthrough** — attack fires → output goes
  live → P never latches → loop never jumps → note-end mutes the tail quickly.
  Unpitched content plays (mostly) dry, which is the correct perceptual
  outcome, not a failure.

## Evidence vs policy — active_gain's home (agreed 2026-07-03)

The dive path's job splits in two, and the split decides what moves to the
loop controller when this is ported:

- **Evidence** (stays in the attack detector, exposed as probe outputs): the
  soft memberships — `alive_decay`, `alive_level`, `alive_floor` — and their
  raw product. They come from the detector's envelope machinery and mean
  "how alive does this note look", independent of what any consumer does
  with it.
- **Policy** (belongs in the loop controller): the onset pin (hold the gate
  open through the attack transient's fast settle — the controller already
  receives the trigger and owns attack handling), the asymmetric
  close-fast/reopen-slow smoothing, and per-ROLE application (the attack tap
  is already gate-exempt there). The output splicer keeps its own note-end
  latch policy on the same evidence.

Two policy details settled in the lab: a detected attack must SNAP the gate
smoother state open (racing it up from below causes a sag-and-recover after
the pin expires), and `ref`'s release must not duplicate `fast`'s anti-ripple
hold — the cascaded 25 ms plateau + 50 ms drop made ref lag ~60–100 ms after
a mute, missing 30 ms mute-to-attack gaps (now 10 ms settle + 25 ms drop; the
ripple defense lives in `fast` alone). Trigger startup guard: the note-memory
bar initializes at −10 dB and leaks to its floor over ~3 s ("a loud note just
ended"), which removes the file-start fire cluster by construction.

## Hard constraint — SOFT decisions, not a hard state machine

User's firm preference (and a good one): **fuzzy / soft decisions, not a rigid
FSM.** A hard state machine has *absorbing failure states* — one missed attack
or spurious note-end drops you into the wrong mode and you're stuck until the
next transition; errors persist and cascade (audibly). A soft system has a
*restoring force* — a bad reading nudges the output and self-corrects as
evidence accumulates.

This philosophy is already in the codebase and working: the trigger's
boosted-threshold holdoff (`k` rests at `k_nom`, snaps up on a fire, decays
back) is a *soft, overridable* holdoff, not a hard debounce (a bigger attack
fires straight through). That is the template to extend. The design rule that
makes "restoring force" real: **every remembered quantity must have a leak** —
the onset reference's upward leak is exactly this rule applied.

So: keep the note-level **memory**, but express every **decision** as a
continuous confidence like `k(t)`:
- **onset reference** = a leaky value that fast-tracks the level *weighted by
  attack confidence*, drifts upward when undershooting, holds otherwise;
- **"note is alive"** = a continuous membership — the soft product of the two
  evidence terms above — feeding `active_gain` (already a soft [0,1] gain;
  nothing hardens into a mode).

The only unavoidably-hard decision in the chain is the **read-jump** in
`loop_controller` (jump or not). Push that hard edge as far downstream as
possible and keep everything feeding it soft.

## Demoted — onset-anchored decay template

An `onset · e^(−t/T_ring)` expected-decay template was considered and demoted,
not just deferred: a real bass ring-down is multi-slope (high partials die
fast, the fundamental lingers), so a single-exponential template anchored at
the onset misreads the first ~100 ms of a healthy note as a partial damp. The
decay-rate evidence captures the same information without the template.

## Next steps

- **Capture regression audio first**: a loud→soft note pair and a legato pair
  (the prob. 2 / prob. 3 failure cases), alongside "Longer Bass Notes.wav" and
  the two "Bass Notes Bad Trigger" files (dead/short-note fixtures) — so fixes
  are scored against files, not by eye.
- Check the existing `yd.aperiodicity` probe around a damp (free evidence?).
- Prototype the period-commensurate energy window + log-slope damp membership
  in the lab; verify it separates damp from ripple at low E, and that
  `active_gain` is clean enough to drop the once-per-loop hold.
- Add the soft onset reference (early-sustain capture + upward leak); check it
  fixes prob. 2 and that a deliberately-missed attack still recovers (prob. 3).
- Revisit double/missed triggers — largely LANDED in the lab (2026-07-03):
  a **level qualification** (leaky previous-note-strength bar, −30 dB rel,
  soft 10 dB band, constant −45 dB memory floor; separate from `k`, which
  stays level-independent) removes between-note junk; the `k` holdoff is now
  **hold-then-fast-drop + re-arm** (edge counts only after the ratio dips
  below `k_nom`), killing same-transient doubles without masking later real
  attacks; `k_nom` lowered 2.0 → 1.6. Remaining: one LBN attack (~3.9 s, peak
  qualified ratio 1.34) still missed — the stale-`ref` case; fix it with the
  reference re-arm redesign above, NOT by lowering `k` further (1.2 re-admits
  tail junk). Startup fire cluster at t≈0: FIXED by the memory-bar init ramp.
- Only then port the settled dive design back to `attack_detector.dsp`
  (new `yd.P → atk` edge in the graph); re-verify `lab == Faust`. Everything
  here is one-poles, ratios, and leaky latches — Faust-friendly territory.
