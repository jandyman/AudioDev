# Loop Controller

The brain of the pitch shifter. It owns every delay ramp and tap gain across the
three delay taps and decides when to splice a new loop or respond to an attack.

**Output-side detection:** loop points come from the pitch detector's
**selected-band peak train** (`pd.selected_peak`) — a clean one-per-period clock
that isolates the fundamental, far steadier than raw input zero crossings on
harmonically-rich notes (which stutter on the growing 2nd harmonic). Each peak
time is recorded as an absolute sample index in a ring buffer; on each output
sample the controller compares `AT_out = sample_index − DT_active` against the
head of that buffer, and when they line up it may fire a loop transition.
Splicing peak-to-peak is **phase-matched by construction** — both endpoints share
the filter's group delay, which cancels in the loop length. Bailout runs every
sample (not gated on peak arrival), so the active delay can never grow unbounded
past the upper threshold.

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

### Loop-point selection (target latency)

When latency exceeds `LOWER_THRESHOLD_MS`, the controller jumps back to whichever
peak lands latency closest to the operating point (the lower threshold). In steady
state only ~one period has accumulated since the last loop, so this is a
**single-peak (k=1) step that holds latency near the threshold** — small per-loop
amplitude steps, not a jump-to-minimum sawtooth. If latency has overshot (clawback
after a deferral, or corner cases) it jumps back as many peaks as needed: `k` is
simply whatever reaches the target. Because the candidates are the clean
per-period peak clock, every jump is an integer number of periods and
phase-matched, so **no period/margin gate is needed** (the old `MARGIN_FRAC_P` /
urgency machinery is gone). The scan stops once a candidate would drop
`new_inactive` below `MIN_DELAY`.

*Known residual:* the firing-cadence/crossfade dynamics currently yield a
~2-period latency sawtooth rather than a tight 1-period one — a deferred polish,
not a correctness issue; splices stay phase-matched throughout.

No dynamic allocation in `process()` — all state is statically declared.
Parameter: `pitch_ratio` (runtime-adjustable; flushes ZC history on change).
