The brain of the pitch shifter. It owns every delay ramp and tap gain across the
three delay taps and decides when to splice a new loop or respond to an attack.

**Output-side detection:** input zero crossings are recorded as absolute
sample-index times in a ring buffer; on each output sample the controller
compares `AT_out = sample_index − DT_active` against the head of that buffer, and
when they line up it is emitting that crossing and may fire a loop transition.
Bailout runs every sample (not gated on input arrival), so the active delay can
never grow unbounded past the upper threshold.

### Tap roles

One tap at a time is the **active** loop tap (the bulk of the output); during a
loop crossfade a second tap is the **loop-incoming** tap fading in; on an attack a
third free tap becomes the **attack** tap. Roles are *dynamic* — which physical
tap {0,1,2} holds which role rotates round-robin after each response, so anything
that gates or routes a tap must key on the role member (e.g. `attack_tap_`),
never a fixed gain index.

### Attack response

On an attack impulse (only while in `LOOP_ONLY` mode) a free tap becomes the
attack tap and fades in fast (`ATTACK_FADEIN_MS` = 1 ms) to carry the new
transient at full level; the loop pair then fades out together
(`ATTACK_FADEOUT_MS` = 10 ms), after which the attack tap becomes the new active
tap. Loop firing and bailout are suppressed during the response (~11 ms worst
case); the attack detector's own holdoff keeps attacks from overlapping.

### active_gain muting

Every **non-attack** tap's gain is multiplied by `active_gain` (the attack
detector's dive output) so buffer-bleed has no audible path during silence or the
attack crossfade. The attack tap is deliberately **not** gated — that is what
lets its 1 ms fade-in carry the transient cleanly. Because tap roles are dynamic,
this exclusion is by role (`attack_tap_`), not by a fixed gain index.

### Harmonic-rejector gate

When the harmonic rejector reports `qualified` with a period `P`, loop-point
selection prefers a candidate whose loop length is an integer multiple of `P`
(rejecting octave errors); otherwise it falls back to the newest delay-valid
candidate.

No dynamic allocation in `process()` — all state is statically declared.
Parameter: `pitch_ratio` (runtime-adjustable; flushes ZC history on change).
