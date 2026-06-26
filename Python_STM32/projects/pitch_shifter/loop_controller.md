# Loop Controller

The brain of the pitch shifter. It owns every delay ramp and tap gain across the
three delay taps, turning the YIN detector's precise period `P` plus the attack
impulse into the three tap delays and crossfade gains for the triple-tap delay. No
dynamic allocation in `process()` — all state is statically declared.

### YIN-driven loop policy (k·P jumps)

The active tap's delay *is* the latency; it grows by `dd_ = 1 − pitch_ratio` every
sample (the read falls behind the write, which is what lowers the pitch). When the
latency exceeds the operating point (`LOWER_THRESHOLD_MS` = 50 ms), a confident `P`
is in hand, and the loop lockout has expired, the controller jumps the read back by
exactly `k·P` (k = 1 in steady state — only ~one period has accumulated since the
last loop). A jump of an integer number of periods is **phase-matched by
periodicity**: the waveform lines up no matter *where* in the cycle the jump lands.
So the loop POINT no longer matters, only that the jump length ≈ P — there is no
splice point, no peak / zero-crossing clock, and no period/margin gate (the entire
peak-clock apparatus this replaced is gone).

Lower latency = fresher looped material = less timbral modulation on an evolving
note, which is why the operating point sits low (50 ms) rather than at the bailout
ceiling.

### Confidence and the latched period

YIN emits `aperiodicity` (the normalized difference at its chosen dip); low =
confident. The controller **latches** `P` while `aperiodicity ≤ APERIODICITY_THRESH`
(0.40) and holds the last good `P` through brief confidence dips. The latched `P` is
**invalidated on an attack**, so a fresh note never loops on the previous note's
period before YIN re-converges (~50 ms); the attack tap covers the onset meanwhile.

### Loop lockout

`LOOP_LOCKOUT_MS` (7 ms) is the minimum time between loop fires — an **absolute**
time (one crossfade plus a settle margin), deliberately **not** a multiple of `P`.
The jump *length* must be ≈ P, but the time a crossfade needs to settle has nothing
to do with the period.

### Bailout (decoupled safety)

Latency is checked every sample. If it ever reaches `UPPER_THRESHOLD_MS` (200 ms) —
e.g. a long stretch with no confident `P` — a bailout crossfade (`BAILOUT_CROSSFADE_MULT`
= 3× the loop crossfade) resets the read toward `MIN_DELAY`. A rarely-reached safety
net, decoupled from normal loop firing.

### Tap roles

One tap at a time is the **active** loop tap (the bulk of the output); during a loop
crossfade a second tap is the **loop-incoming** tap fading in; on an attack a third
free tap becomes the **attack** tap. Roles are *dynamic* — which physical tap {0,1,2}
holds which role rotates (via `pick_free_tap`) after each response, so anything that
gates or routes a tap must key on the role member (`active_tap_`, `attack_tap_`, …),
never a fixed gain index.

### Attack response

On an attack impulse (only while in `LOOP_ONLY` mode) a free tap becomes the attack
tap and fades in fast (`ATTACK_FADEIN_MS` = 1 ms) to carry the new transient at full
level; the loop pair then fades out together (`ATTACK_FADEOUT_MS` = 10 ms), after
which the attack tap becomes the new active tap. The attack detector's own holdoff
keeps attacks from overlapping.

### active_gain muting

Every **non-attack** tap's gain is multiplied by `active_gain` (the attack detector's
dive output) so buffer-bleed has no audible path during silence or the attack
crossfade. The attack tap is deliberately **not** gated — that is what lets its 1 ms
fade-in carry the transient cleanly. Because tap roles are dynamic, this exclusion is
by role (`attack_tap_`), not by a fixed gain index.

### Parameter

`pitch_ratio` is runtime-adjustable (`set_param("pitch_ratio", …)` / `set_pitch_ratio`);
the setter clamps it and recomputes the derived constants (`dd_`, threshold and
crossfade sample counts). 0.5 = one octave down.

---

The diagnostic probe outputs (`latency_ms`, `loop_event`, `active_tap`,
`bailout_event`, `gated_event`, `attack_event`) are not wired downstream in the graph
— they exist purely as taps for Python plots.
