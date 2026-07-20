# Project Concept

The project is an algorithm for shifting the pitch of bass guitar signals down in pitch. A typical application is an octave dropper, but the only real limitation in terms of pitch interval is that the pitch can only be shifted down.

The core idea behind the algorithm is to store the incoming signal in a delay line, and to play back a signal out of the delay line at a reduced sampling rate, which implies fractional delays for anything besides an octave drop. The delay time increases by a constant for each output sample, effectively lowering the pitch of the output signal. But the delay time needs to be set/reset at certain times, both to preserve attack transients and to limit output latency.

The delay time is reset in a discontinuous fashion based on two different triggers, described below. In order to prevent clicks, two delay lines sharing the same delay buffer operate in ping-pong fashion so that a quick crossfade can be implemented at set/reset points.

The first trigger, which has the higher precedence, is an input from an attack detector. It causes a delay time transition to a delay of near-zero, using the crossfade technique described above. This reset to a virtually zero delay allows the early attack portion of a new note to be represented properly. A latency counter is set to zero, which is used for the second trigger.

The second, lower priority trigger is used during the sustain portion of a note. During sustain, the latency will gradually increase. At a certain point it will become desirable to reset the delay time to reduce the latency. In order to reduce or eliminate artifacts, we try to reset the delay time such that the output jumps from one zero crossing to another separated by an integer number of pitch periods. We describe the "looping" strategy in more detail in later sections. There is a trade-off concerning when to try to reset: waiting longer accumulates more latency but retains more of the note's character.

# Functional block breakdown and high level design

## Attack Detector

This block detects attack transients in the input signal. The output is an impulse stream — zero on most samples, one on samples where an attack is detected — consumed by the Control Logic where it has top priority (overrides any in-progress looping) and triggers a near-zero-delay fade-in on the dedicated attack tap of the three-tap delay (see *Three Tap Fractional Delay Line*) so the new note's transient is captured cleanly.

The detector is bass-specific. Per-cycle level variation is the dominant source of false-trigger pressure across the bass range, so the design uses three envelope followers at different time scales plus a small state machine. Two detection paths cooperate: a derivative-based **normal** path that catches new attacks, and a level-based **retrigger** path that recovers from false triggers landing on top of cycle peaks.

Implementation: `Python_STM32/python/pitch_shifter_demo/attack_detector.dsp` (Faust). Offline visualisation: `attack_detector_diagnostic.py` in the same folder.

### Signal flow

```
audio ─→ x² → onepole → √(·)  =  rms
                                 ├─→ env_ar(1 ms / 10 ms)   = fast_env
                                 ├─→ env_ar(5 ms / 50 ms)   = med_env
                                 └─→ env_ar(50 ms / 200 ms) = slow_env

note_ended  = fast_env < slow_env × end_ratio
threshold   = note_ended ? armed_thresh : active_thresh
raw_detect  = (fast_env − fast_env') > threshold              ← normal path
retrigger   = fast_env > med_env × retrigger_ratio            ← retrigger path

state machine: inhibit_count, did_retrigger  →  trigger
```

### Front end — RMS

`rms_env(window_s, x) = onepole(x²) → √(·)`, onepole coefficient `exp(−1 / (window_s · SR))`. Default `window_s = 8 ms` — short enough to track attack envelopes, long enough to average the dominant harmonic content that contributes to level. At the bottom of the bass range the 8 ms window is shorter than the fundamental period (E1 = 41 Hz → 24 ms period), so a residual 41 Hz ripple survives into the followers; see *Known issues*.

### Envelope followers

Three asymmetric one-pole followers (`env_ar`) sample the RMS signal at different time constants:

| Follower    | Attack | Release | Purpose                                          |
|-------------|--------|---------|--------------------------------------------------|
| `fast_env`  | 1 ms   | 10 ms   | Tracks transients; source of the derivative     |
| `med_env`   | 5 ms   | 50 ms   | "Current energy" reference for the retrigger path |
| `slow_env`  | 50 ms  | 200 ms  | Long-term reference for the note-end ratio test |

`env_ar` rule per sample: if `x > prev`, attack toward `x` at coefficient `att_c = exp(−1 / (att_s · SR))`; else decay (`prev := rel_c · prev`) toward zero, *not* toward `x`. The asymmetry plus the decay-toward-zero shape makes the envelopes effectively peak-hold-ish: each cycle peak refreshes the envelope upward, and between peaks the envelope drifts down at the release rate.

### Note-end detection

A note has ended (or is dying) when the fast envelope drops well below the slow envelope:

```
note_ended = (fast_env < slow_env × end_ratio + ε)
```

with `end_ratio = 0.75` (fast has fallen to 75 % of slow) and `ε = 0.0001` (avoids spurious arming in silence). `note_ended` is a probe output and gates the threshold scheme below.

### Adaptive threshold (two regimes)

The detector uses two regimes for the normal trigger threshold:

- **Armed** (during `note_ended`): expecting a new attack. Threshold scales with current energy so a quiet new attack still trips: `armed_thresh = max(armed_floor, med_env × armed_scale)`. Defaults: `armed_floor = 5 × 10⁻⁵` (floor in silence), `armed_scale = 0.003` (low — favours sensitivity).
- **Active** (sustaining note): threshold held high so derivative spikes within a sustained cycle do not re-fire. Default `active_thresh = 0.02`.

The decision quantity is the per-sample derivative of `fast_env`:

```
fast_deriv = fast_env − fast_env'      // x − x'
raw_detect = fast_deriv > threshold
```

### Two detection paths

**Normal trigger.** Fires when `raw_detect == 1` AND the inhibition counter is zero. This is the main path: a real attack is rising fast enough that the derivative clears the (armed-scaled) threshold, and we are not in the post-trigger inhibition window.

**Retrigger.** Some attacks land in the middle of the inhibition window of a previous (possibly false) trigger and would be lost by the armed path alone. To catch them, the retrigger path watches absolute levels:

```
retrigger_detect = (fast_env > med_env × retrigger_ratio)
```

with `retrigger_ratio = 1.4`. If true *while inhibited*, fire — but at most once per inhibition window (governed by `did_retrigger`). The retrigger does not abort the previous crossfade; it starts a fresh one. This pattern is a recovery mechanism, not a primary path — if it fires often, the normal-path tuning needs revisiting.

### State machine

Two state variables: `inhibit_count` (samples remaining in the inhibition window) and `did_retrigger` (has a retrigger already fired in the current window?).

Per sample:

```
can_fire        = (inhibit_count ≤ 0)
normal_fire     = raw_detect AND can_fire
can_retrigger   = (inhibit_count > 0) AND (NOT did_retrigger) AND retrigger_detect
trigger         = normal_fire OR can_retrigger
inhibit_count   = trigger ? inhibit_samples : max(0, inhibit_count − 1)
did_retrigger   = normal_fire ? 0 : (can_retrigger ? 1 : did_retrigger)
```

Default `inhibit_time = 50 ms` (~2400 samples at 48 kHz).

### Probe outputs

Six signals emitted continuously, all consumed by the diagnostic harness. Output indices match `attack_detector.dsp::process`:

| Idx | Output       | Type        | Meaning                                                  |
|-----|--------------|-------------|----------------------------------------------------------|
| 0   | `trigger`    | impulse 0/1 | Attack detection — consumed by Control Logic             |
| 1   | `threshold`  | level       | Currently active threshold (armed or active value)       |
| 2   | `fast_env`   | level       | 1 ms / 10 ms envelope                                    |
| 3   | `slow_env`   | level       | 50 ms / 200 ms envelope                                  |
| 4   | `note_ended` | flag 0/1    | Armed regime indicator                                   |
| 5   | `med_env`    | level       | 5 ms / 50 ms envelope                                    |

The diagnostic distinguishes normal vs. retrigger after the fact by inter-trigger gap (gaps shorter than `inhibit_time + 5 ms` are tagged retrigger). The firmware does not currently expose the authoritative `did_retrigger` flag as a probe — see *Known issues*.

### Known issues / open work

- **RMS window vs. low-E period.** The 8 ms RMS window is shorter than E1's 24 ms fundamental period. A residual ~41 Hz ripple survives into `fast_env` on very low notes, raising the floor for the active-mode threshold and limiting how quickly the detector can decide a note has ended. The planned **hold-then-release envelope** (below) is one possible fix.
- **Shared `slow_env`.** A single follower drives the note-end ratio test. Splitting roles (one envelope for arming, another for the ratio) is on the table but not yet motivated by a concrete failure.
- **Regime-switch behaviour at the boundary** is not currently characterised — the `fast_env < slow_env × end_ratio` crossing is a single thresholded signal with no hysteresis, and rapid toggling near the boundary has not been audited.
- **Probe gap:** `did_retrigger` and the raw `raw_detect` / `retrigger_detect` decisions are internal to the state machine. The diagnostic infers behaviour from outputs, which is reliable for normal cases but cannot distinguish, e.g., a `retrigger_detect` that was suppressed by `did_retrigger == 1` from one that simply did not occur.

### Planned: hold-then-release envelope

A fourth envelope follower with a two-stage release time constant is planned, to supplement (and possibly replace) `med_env`. When the signal first crosses below the envelope estimate, a timer starts. While the timer runs, release is **slow** — bridges intra-cycle ripple at the lowest fundamental of interest (~24 ms for E1). When the timer expires, release transitions to **fast** — quickly catches note-end. The transition is gradual rather than switched to avoid zipper artifacts. Goal: reduce per-cycle envelope ripple on low notes without sacrificing note-end detection latency.

Design status: concept agreed, tuned to the lowest frequency of interest (not the highest), fixed timer preferred over adaptive-from-harmonic-rejector-P (because `hr.qualified` typically goes false during the decay tail, exactly when the follower needs to be working). Implementation pending.

## Zero Crossing Detector

This block watches the incoming audio signal and emits an impulse at each qualified zero crossing. A "qualified" zero crossing filters out crossings that are likely noise artifacts: only crossings with a consistent direction (e.g., positive-going), above a minimum amplitude threshold in the surrounding samples, and separated from the previous crossing by a minimum time interval are counted.

The detector's output is simply an impulse stream. Record creation — including arrival time and playback time — is handled by the Control Logic, which has access to the current delay time needed to compute PT.

### Harmonic rejection

Bass guitar signals are harmonically rich; the 2nd harmonic can produce additional positive-going zero crossings within a single fundamental period. Without suppression these spurious ZCs are indistinguishable from fundamental ones to the loop controller and lead to wrong loop points. The Harmonic Rejection block runs a parallel filter bank, scores each filter for "cleanness" of the period it would yield, and selects the lowest-cutoff filter whose score is trustworthy. The selected filter's running mean of inter-peak intervals becomes the period estimate `P` that the loop controller's candidate-selection gate (see *Urgency and relaxed matching*) tests against.

**Filter bank.** N parallel 2nd-order Butterworth LPFs (12 dB/oct) with octave-spaced cutoffs — current default `{60, 120, 240} Hz`. Each cutoff is chosen so that for some register of fundamentals the filter passes F0 and substantially attenuates H2. The bank is cheap (a handful of biquads) and entirely time-domain, so it adds no latency beyond filter group delay.

**Per-filter analysis.** For each filter `k`:

- A **tall-peak stream** — positive peaks of the filtered signal whose value is at least `frac × envelope` at the same sample. The envelope is the Hilbert magnitude of the filtered signal in offline analysis or a one-pole follower in real-time. Tall peaks mark fundamental-cycle instants because harmonic bumps mid-cycle sit below the envelope.
- **Running EMA statistics over inter-tall-peak intervals:**
  ```
  μ_k  = EMA over intervals               ← period estimate (samples)
  σ_k  = sqrt( EMA of (interval − μ_k)² ) ← interval std
  cleanness_k = 1 / (1 + σ_k / μ_k)       ← coefficient-of-variation form, ∈ (0, 1]
  amplitude_k = EMA(env_filt) / EMA(env_raw)
  ```
  EMA time constant is on the order of a few cycles — short enough to track per-note period changes, long enough to smooth single-cycle perturbations. `μ_k` is undefined until the filter has produced at least two tall peaks; `cleanness_k` reports `0` (filter not qualified) until enough intervals have arrived for the EMA to settle.

**Selector.** At each sample, walk the bank from lowest to highest cutoff and pick the first filter `k` where `cleanness_k ≥ C_min` AND `amplitude_k ≥ A_min`. Lower cutoffs are preferred because they reject H2 most strongly; the selector steps up only when the fundamental has moved above the current cutoff and the filter no longer dominates its output. The amplitude check guards against locking onto sympathetic vibration during decay, when a low-cutoff filter's output could be "clean" but tracking residual energy rather than the played note. If no filter qualifies, the selector emits a *no-estimate* sentinel; the loop controller's integer-multiple gate is then disabled and falls through to its newest-valid pick.

**Period and margin source.** When a filter is selected, `P = μ_k` of that filter. The matching margin used by the loop-candidate gate scales with `σ`:
```
margin = max(C_margin · P, σ_k)
```
A noisier estimate naturally widens the gate. The loop controller may further widen the margin with an urgency multiplier as latency grows (see *Urgency and relaxed matching*).

**Probe outputs.** Per filter: filtered signal, envelope, envelope-normalized signal, tall-peak impulses, running `μ`, running `σ`, cleanness, amplitude. Plus selector: selected filter index, selected `P`, selected `σ`, qualified vs. no-estimate flag. All probes are emitted continuously and consumed by the offline test harness.

**Earlier approaches now subsumed:**

- *Dual-LPF energy switching* — generalised to the N-filter bank above. Energy-comparison switching is replaced by per-filter cleanness scoring, which is more directly aligned with what we actually want (a period estimate we can trust) and which extends to more than two filters without restructuring.
- *Peak-to-envelope ratio* — folded into the per-filter analysis (the `frac × envelope` threshold for tall peaks). The question of "is this filter's period trustworthy?" is then answered by the cleanness and amplitude probes rather than peak-to-envelope alone.

**Derivative magnitude at crossing (not recommended).** Initial investigation showed that the derivative `x - x'` at a zero crossing does not reliably discriminate fundamental crossings from harmonic-induced spurious crossings — at a zero crossing the signal is mid-swing and all harmonics contribute to the slope simultaneously, so there is no clean separation. The ZC detector still emits the derivative as a probe output (output 4) for completeness.

## Three Tap Fractional Delay Line

The target design is a delay buffer of a fixed size with **three** independent read taps sharing a single write buffer. Each tap has its own delay-time input and produces one delayed-signal output. The three taps have specific roles:

- **Attack tap** — dedicated to attack-triggered resets. Idle except when an attack fires and during the subsequent fade-in/out.
- **Loop 1 / Loop 2** — the ping-pong pair for loop transitions. Exactly one is the "active" tap producing sustained output at any moment; the other parks for the next loop crossfade.

Reserving the attack tap (rather than time-sharing all three) is what lets an attack-triggered crossfade overlap a loop crossfade already in progress without aborting it. See *Attack interrupting a loop crossfade* in *Open Issues* for the choreography decisions still open.

**Current implementation status: dual-tap.** Per the loop-first development ordering, the current `dual_tap_delay.dsp` exposes only the two loop taps; the attack tap is added once loop tuning is settled and the attack detector is brought back into the live pipeline.

## Control Logic

Takes inputs from the attack detector and the zero crossing detector, and determines when to reset the delay lines. It manages crossfades and overall state. It outputs the two delay times for the dual delay line.

There are two triggers for resetting the delay times and initiating a crossfade:
- **Attack detector impulse:** highest priority, resets the inactive tap delay to near-zero.
- **Looping logic:** lower priority, resets the inactive tap delay to a detected loop point (a non-zero delay corresponding to an earlier point in the waveform that is an integer number of pitch periods behind the current output position).

No matter what the looping logic is doing, if an attack is detected, a crossfade takes place immediately. The looping logic is more complex and requires a separate explanation.

### Crossfade timing

Different events have different crossfade time requirements:

- **Loop transitions:** The crossfade can be relatively long and relaxed, since the signal content on both sides of the transition is period-aligned and the artifact risk is low.
- **Attack fade-out:** The outgoing tap can also fade out slowly — the attack has already started on the incoming tap and the fade-out content is the tail of the previous note.
- **Attack fade-in:** Must be short. The whole point of an attack reset is to capture the transient faithfully, so the new tap needs to reach full gain quickly before the attack transient passes.

### Probe outputs

The Control Logic should expose the following signals for diagnosis and tuning:
- Current delay time (latency)
- Loop point detection events (when a transition is scheduled, and what delay it targets)
- Crossfade state (which tap is active, crossfade progress)
- Bailout events

### Sustain Portion Looping Logic

**Looping during tails and silence:** The looping logic runs continuously, not only during active notes. During noise tails and silence, any zero crossing is a plausible loop candidate (since the signal content is indistinguishable), so transitions happen readily and the tap delay stays short. This ensures that when the next note attack arrives, the taps are already at low latency and the attack crossfade starts from a good position.

### About time references

I find it horribly confusing to describe the looping logic using relative times x(n) of the input, and using relative times of the output of introduces one more sense of confusion. So all the times we will store will be absolute times from the beginning of the file, expressed in samples. As an implentation note, if these numbers are stored as 32 bit integers, they will wrap around at about 24 hours at 48K. Although this is unlikely to be relevant, if we do unsigned math, we can count on being able to compute relative times even with wraparound. We just need to be careful to express things in relative terms in the actual implementation. And this will naturally fall out of the math, even though we think in absolute terms. So descriptions below are in absolute times. I think this will make more sense as we describe storing zero crossings to determine loop points. And it should make debug easier to have everything in absolute sample times.

#### Why the crossfade cannot happen immediately at input zero crossing arrival

When a zero crossing impulse arrives from the Zero Crossing Detector of the input signal, the output tap is playing audio from some time in the past and is almost certainly not at a zero crossing. Executing a crossfade in the output at that time would produce a click.

Instead, the Control Logic uses the zero crossing impulse to create a record of that crossing and *schedule* a future transition. Because the Control Logic knows the current delay time DT, it can compute when that zero crossing will emerge from the output. The crossfade is executed at that scheduled time, at which point the output is playing the stored zero crossing — guaranteeing a clean transition.

#### Zero crossing history

When a zero crossing impulse is received from the ZC Detector, the Control Logic creates a record containing the **Arrival Time (AT)** — the absolute sample index at which the zero crossing entered the delay buffer. The record is appended to a ring buffer of arrival times.

At any time, the Control Logic can determine the time at which the current output sample arrived at the input by subtracting the active tap's delay from the current sample time: `AT_out = CT − DT_active`. Note that DT_active is generally fractional (it ramps by `dd = 1 − pitch_ratio` per sample), so AT_out is fractional too — but the recorded ATs are integer (they are sample indices). The implementation rule is: AT_out has *reached* a recorded AT when `AT_out ≥ AT_record`, i.e. on the first output sample where AT_out crosses that integer boundary. The fractional residue `δ = AT_out − AT_record` at the firing moment is in `[0, pitch_ratio)`. It looks like it would cause a small positioning artifact, but it doesn't — as shown in *Fractional offset cancellation* below, the cross-fade math cancels it exactly, leaving both taps at the same fractional phase past their respective period-aligned zero crossings.

#### Loop candidate search

The loop check runs **per output sample**. The only input-driven action is *recording* a new ZC arrival into the ring buffer when the ZC Detector emits an impulse. All decisions — pruning, firing, bailout — happen on the output side. This asymmetry (record on input, decide on output) is the simplification the new scheme buys us, and it is why the algorithm no longer needs to compute or store playback times.

On each output sample:

1. Compute `AT_out = CT − DT_active`.

2. While the ring buffer is non-empty and `AT_out ≥ head.AT`, the output has just reached (or crossed) the head record. One of three things then happens:

   a. **Cross-fade in progress** → pop head and continue the loop. (We can't fire mid-cross-fade.)

   b. **`DT_active > lower_threshold` and at least one more record exists in the buffer** → fire. Treat head as `AT_old`. Pick `AT_new` by scanning from the newest record (tail) backward toward `head+1`, and choose the **first** record where:
      ```
      DT_inactive = DT_active − (AT_new − AT_old) ≥ MIN_DELAY_SAMPLES
      ```
      i.e. the newest record whose use as a target leaves a non-negligible delay. This maximises the latency reduction per transition — picking older records (smaller `AT_new − AT_old`) gives smaller reductions and causes transitions to fire on nearly every output ZC, producing an audible modulation tone. Set the inactive tap's delay to the `DT_inactive` computed above, so that the inactive tap reads `AT_new` on the very first sample of the cross-fade. The inactive tap was parked before this moment, so setting its delay here is the *only* place its value gets initialised. Start the cross-fade, pop head, and exit the loop. (Future versions will add period-alignment screening on top of this — see Open Issues.)

   c. **Otherwise** (latency too low, or no more records to loop to) → pop head and continue. The entry was reached without firing.

3. **Bailout**: if `DT_active > upper_threshold` on this sample and a cross-fade is not in progress, force a cross-fade immediately. Set the inactive tap to a near-zero delay (`MIN_DELAY_SAMPLES`) and use the long bailout cross-fade duration. Flush the ring buffer (its contents are stale after the reset). Because this check is per-sample (not gated on input ZC arrival), the delay can never grow unboundedly past the upper threshold — even during silence, noise tails, or unpitched content where no candidate ZC is available.

The while-loop in step 2 covers the rare case where AT_out crosses more than one record on a single sample (only possible with `pitch_ratio` very close to 0). The common case is at most one iteration per sample. Combining the prune and the fire check into one loop avoids the subtle bug of pruning the head before we get a chance to act on it.

#### Fractional offset cancellation

At the moment of firing in step 2b, `AT_out = AT_old + δ` for some `δ ∈ [0, pitch_ratio)`. The outgoing tap is reading the (interpolated) signal at `AT_out`. The incoming tap's delay is set to `DT_inactive = DT_active − (AT_new − AT_old)`, so its read position works out to:

```
CT − DT_inactive  =  CT − DT_active + (AT_new − AT_old)
                  =  AT_out + (AT_new − AT_old)
                  =  AT_old + δ + (AT_new − AT_old)
                  =  AT_new + δ
```

Both taps read at the *same* fractional offset `δ` past their respective ZCs. If the two ZCs are well period-aligned (the algorithm's premise), the interpolated samples at `AT_old + δ` and `AT_new + δ` are essentially identical. The cross-fade has nothing to cancel — the discontinuity is already zero at the start of the cross-fade.

The cancellation happens in the *difference* of the two tap delays, not in either tap's absolute delay. Critically, it does not depend on `dd` being constant. That's why the algorithm also handles modulated delay (see below).

#### Urgency and relaxed matching

The need for a transition becomes more urgent as latency grows. The matching criteria relax accordingly:

- **Below lower threshold:** No search, just record.
- **Above lower threshold:** Walk the ZC record list from newest (tail) backward toward oldest valid (head+1). Given the current period estimate `P` from the Harmonic Rejection block, the head's arrival time `AT_old`, and a `margin` (see Harmonic Rejection), accept the first record at `AT_new` where both:
  - `DT_inactive = DT_active − (AT_new − AT_old) ≥ MIN_DELAY_SAMPLES` (existing latency-reduction constraint), and
  - `| Δ − round(Δ / P) · P | ≤ margin`, where `Δ = AT_new − AT_old > 0` and `round(Δ / P) ≥ 1` (period alignment).

  If no record satisfies both — or if the Harmonic Rejection block reports *no estimate* — fall back to the existing newest-valid pick: the first record satisfying the `DT_inactive` constraint alone. This fallback is the same algorithm the controller uses today, so adding the gate is purely additive: at worst we land on a wrong-harmonic crossing, which is what we already do.
- **As latency grows toward the upper threshold:** Multiply the `margin` by an urgency factor that scales from 1 at the lower threshold to a larger value (e.g. 3×) approaching the upper threshold, so wrong-phase candidates become acceptable rather than letting the bailout fire.
- **Above upper threshold (200 ms, bailout):** Fire a cross-fade immediately on the current output sample, regardless of whether a ZC is being emitted. Reset the inactive tap to near-zero delay and use a longer cross-fade time (3× the loop cross-fade) to reduce the audible artifact. Because the bailout runs per output sample (see step 3 of the loop candidate search), this catches cases where no candidate ZC is available at the current output position — silence, noise tails, or unpitched content — and prevents the delay from growing unboundedly. The trade-off is a non-ZC transition in the output, mitigated by the long cross-fade.

#### Period range for candidate matching (FUTURE)

The valid input-domain period range is based on the bass A string up to 2.5 octaves above:

- **A1 (55 Hz):** ~18.2 ms — lowest expected fundamental
- **2.5 octaves above A1 (≈ 311 Hz):** ~3.2 ms — upper limit

The output-domain period range used for PT difference matching is T_input / pitch_ratio (e.g. 3.2–18.2 ms becomes 6.4–36.4 ms for an octave drop). The exact tolerances and whether to prefer the smallest valid N will require tuning once the looping logic is running.

#### Modulated delay (FUTURE)

The loop-detection and cross-fade math above never assume that the delay increment `dd` is constant per sample. The firing rule (`AT_out ≥ head.AT`), the cross-fade formula (`DT_inactive = DT_active − (AT_new − AT_old)`), and the fractional-offset cancellation all use `DT_active` *as observed at the current sample* — they make no commitment to how it got to that value.

This means the algorithm naturally accommodates:

- **Vibrato:** sinusoidal modulation of `dd` (or equivalently `pitch_ratio`) around a centre value.
- **Pitch envelopes / glides:** a smooth schedule of `pitch_ratio` between two notes.
- **Static pitch_ratio changes during sustain:** without needing to flush state.

The earlier PT-based scheme baked a constant `pitch_ratio` into every recorded playback time, so modulation would have invalidated already-scheduled fire times. The new output-side detection has no such dependency: it would work with any monotonic schedule of `DT_active`. No additional implementation work is needed beyond exposing the modulation source as a runtime input.

## Open Issues

### History buffer size

The ZC record list is a statically declared ring buffer. Dynamic memory allocation is permitted during module construction (object initialisation), but not in the audio render callback. For embedded targets, pure static allocation (compile-time fixed array as a class member) is the preferred approach and eliminates allocation concerns entirely.

At the 200 ms bailout threshold and ~3.2 ms minimum period, the worst-case record count is roughly 60–70. A 128-slot fixed array (next power of two) is a safe choice. When the buffer is full and a new record arrives before old ones have been pruned, the oldest entry is overwritten.

Sample indices can be `int32_t` (overflows after ~12 hours at 48 kHz). If long sessions on embedded hardware are a concern, timestamps can be reset to zero on each attack detection without affecting the algorithm.

### Candidate selection when multiple records match (FUTURE)

Choose the record that produces the minimum resulting delay at fire time, which is `time_until_fire = PT_old − S`. Since PT_old is smaller for older records (they have smaller playback times), **the oldest valid record minimises latency** — not the newest. This corresponds to the largest valid N (most periods separating the two zero crossings). The search should iterate from oldest to newest record and take the first valid hit.

### Attack interrupting a loop crossfade — three-tap design (planned)

If an attack is detected while a loop crossfade is already in progress, both an attack-tap fade-in and the loop crossfade need to proceed without aborting each other. With only two taps, the loop tap being faded out is not available for the attack reset, forcing a compromise: either abort the in-progress crossfade (audible) or delay the attack response (loses transient).

**Decision:** the final pipeline uses **three delay taps with specific roles** rather than three interchangeable taps:

- **Attack tap** — dedicated. Idle most of the time; fades in fast on attack detection and fades out after the attack transient has been captured.
- **Loop 1, Loop 2** — the ping-pong pair for loop transitions. The loop crossfade in progress when an attack fires is allowed to complete on these two taps; the attack fade-in happens in parallel on the attack tap.

The dual-tap implementation remains adequate for validating loop-detection behaviour in isolation (loop-first development ordering); the attack tap is added once the loop logic is tuned and the attack detector is brought back into the live pipeline.

Implementation implications:
- `dual_tap_delay` becomes a three-tap delay with three independent read positions on the shared buffer.
- The control logic tracks three tap delays and three gains, plus the role-state of each (which loop tap is currently active, whether the attack tap is engaged).
- The crossfade model has three concurrent activity slots: at most one loop tap fading-out, one loop tap fading-in, and the attack tap engaged. **Open:** the exact gain-summing choreography when all three are active simultaneously (e.g., should loop taps continue at unchanged gains while attack fades in over the sum, or should they attenuate to make headroom?).