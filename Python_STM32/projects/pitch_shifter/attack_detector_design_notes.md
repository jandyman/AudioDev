# Attack Detector — Design Notes / Handoff (2026-07-02)

Forward-looking notes from a design session. The *shipped* behaviour lives in
`attack_detector.dsp` / `attack_detector.md`; the lab and its RMS-ratio dive are
in `attack_detector_lab.py` / `attack_detector_lab.md`. This file captures the
**open problems and the agreed design direction** for the dive (note-end) path,
which are not yet reflected in code.

## Where the code is now

- Lab envelope API unified (commit `61e0ceb`): every follower takes time
  constants in **seconds + sr** and calls `tau_to_c` internally; `tau_to_c(0)=0`
  (instant attack), `tau=inf → 1` (perfect hold). Peak-hold followers collapsed
  into the `env_ar_*` family (`env_ar_hold(att_s=0, rel_hold_s=inf)` = flat-hold
  peak; `env_ar_accel(att_s=0)` = instant peak track).
- Dive path is now a **fast/slow RMS envelope ratio** (a program-adaptive gate):
  `active_gain = clip(hold_env / slow_env, 0, 1)`, `dive_strength = 1 − active_gain`.
  `rms` = 25 ms window; `hold_env`, `slow_env` are followers of it.
- **Not yet ported to Faust** — the lab dive path is ahead of the block.

## Open problems observed

1. **Double / missed triggers** (minor for the pitch shifter). User has ideas.
2. **`active_gain` wrong on two notes in succession.**
3. **Occasional missed attack** — appears when a note-end was never detected.
4. **`hold_env` dives slower than `fast_env`.** Measured after a hard note-off
   (1/e): `rms` 50 ms, `hold_env` 76 ms, `fast_env` 43 ms. Two causes:
   - the RMS **sqrt doubles the release TC** — a 25 ms window on x² reads out as a
     50 ms amplitude decay (`sqrt(e^(−t/τ)) = e^(−t/2τ)`); well-known RMS gotcha;
   - `hold_env`'s `rel_hold_s = 0.5 s` plateau over its first 28 ms adds ~26 ms.
   - The "feels like 200 ms" is the exponential *tail* (~3–4 TCs), not the TC.

## Root-cause understanding

Problems 2 and 3 share a root: **slow references don't reset between successive
notes.** `slow_env` (~1 s release) and the trigger's `ref` outlive the note they
reference, so note 2 is measured against note 1's tail. A softer note-2 then reads
as the *decay* of note-1 → wrongly gated (prob. 2); a legato/soft note-2 makes too
small a `fast/ref` spike → missed fire (prob. 3).

Deeper: the detector has plenty of *analog* memory (every one-pole has state) but
**no symbolic / note-level memory** — nothing represents "a note started here,
with this strength, this period." The running envelopes are note-agnostic. What a
human does reading the waveform is segment into notes and judge each *relative to
its own onset*. That's the missing layer.

## Agreed design direction

Add a **note-level memory layer anchored on the attack** (which is sharp, low-
latency, and the reliable signal). At each confirmed fire, latch a per-note record:
**onset strength**, **period P** (YIN already computes it), onset time.

Then reframe note-end as a **note-relative** question — "relative to *this* note's
onset, has energy dropped faster than a ringing string would?" — instead of "is
the level below a slow running reference?". Each attack re-arms the reference, so
note 2 self-references (fixes prob. 2). Payoffs from having P per note:
- **pitch-adaptive smoothing**: set the RMS/hold window to the measured period →
  ripple-free at every pitch with minimal latency (kills the fixed-25 ms compromise);
- **damp = departure from expected decay**: hold a cheap `onset · e^(−t/T_ring)`
  template and flag "falling well below expected" within a period or two — the
  same evidence the eye uses.

## Hard constraint — SOFT decisions, not a hard state machine

User's firm preference (and a good one): **fuzzy / soft decisions, not a rigid
FSM.** A hard state machine has *absorbing failure states* — one missed attack or
spurious note-end drops you into the wrong mode and you're stuck until the next
transition; errors persist and cascade (audibly). A soft system has a *restoring
force* — a bad reading nudges the output and self-corrects as evidence accumulates.
Graceful degradation is the property to protect for a real-time effect.

Key point: **this philosophy is already in the codebase and working** — the
trigger's boosted-threshold holdoff (`k` rests at `k_nom`, snaps up on a fire,
decays back) is a *soft, overridable* holdoff, not a hard debounce (a bigger
attack fires straight through). That is the template to extend.

So: keep the note-level **memory**, but express every **decision** as a continuous
confidence like `k(t)`:
- **onset reference** = a leaky value that fast-tracks the level *weighted by
  attack confidence*, holds otherwise — not a hard latch (a wrong attack perturbs
  it slightly and it recovers);
- **"note is alive"** = a continuous membership, a soft product of "energy high
  relative to onset" AND "not falling faster than a natural ring-down", feeding
  `active_gain` (already a soft [0,1] gain — nothing hardens into a mode).

The only unavoidably-hard decision in the chain is the **read-jump** in
`loop_controller` (jump or not). Push that hard edge as far downstream as possible
and keep everything feeding it soft.

## Next steps (candidates)

- Prototype the expected-decay damp test in the lab against a soft-after-loud note
  pair; check it fixes prob. 2 without a hard state machine.
- Sketch the per-note state record and where it hooks into the trigger fire.
- Revisit double/missed triggers (user has ideas) — related to references not
  falling between notes, i.e. the same reset-on-attack lever.
- Only then port the settled dive design back to `attack_detector.dsp`; re-verify
  `lab == Faust`.
