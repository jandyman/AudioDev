# Project Concept

The project is an algorithm for shifting the pitch of bass guitar signals down in pitch. A typical application is an octave dropper, but the only real limitation in terms of pitch interval is that the pitch can only be shifted down.

The core idea behind the algorithm is to store the incoming signal in a delay line, and to play back a signal out of the delay line at a reduced sampling rate, which implies fractional delays for anything besides an octave drop. The delay time increases by a constant for each output sample, effectively lowering the pitch of the output signal. But the delay time needs to be set/reset at certain times, both to preserve attack transients and to limit output latency.

The delay time is reset in a discontinuous fashion based on two different triggers, described below. In order to prevent clicks, two delay lines sharing the same delay buffer operate in ping-pong fashion so that a quick crossfade can be implemented at set/reset points.

The first trigger, which has the higher precedence, is an input from an attack detector. It causes a delay time transition to a delay of near-zero, using the crossfade technique described above. This reset to a virtually zero delay allows the early attack portion of a new note to be represented properly. A latency counter is set to zero, which is used for the second trigger.

The second, lower priority trigger is used during the sustain portion of a note. During sustain, the latency will gradually increase. At a certain point it will become desirable to reset the delay time to reduce the latency. In order to reduce or eliminate artifacts, we try to reset the delay time such that the output jumps from one zero crossing to another separated by an integer number of pitch periods. We describe the "looping" strategy in more detail in later sections. There is a trade-off concerning when to try to reset: waiting longer accumulates more latency but retains more of the note's character.

# Functional block breakdown and high level design

## Attack Detector

This block detects attack transients. The output is zero for any sample which does not represent an attack, and one for a sample which represents an attack detection. So it is a series of isolated impulse spikes. The output is sent to the control logic.

## Zero Crossing Detector

This block watches the incoming audio signal and emits an impulse at each qualified zero crossing. A "qualified" zero crossing filters out crossings that are likely noise artifacts: only crossings with a consistent direction (e.g., positive-going), above a minimum amplitude threshold in the surrounding samples, and separated from the previous crossing by a minimum time interval are counted.

The detector's output is simply an impulse stream. Record creation — including arrival time and playback time — is handled by the Control Logic, which has access to the current delay time needed to compute PT.

### Harmonic rejection

Bass guitar signals are harmonically rich, and the 2nd harmonic (and higher) can cause additional positive-going zero crossings within a single fundamental period, producing spurious records that would lead the loop controller to select incorrect loop points. Several approaches exist; the chosen design is expected to require tuning over time.

**Dual low-pass filter with energy-based switching (primary approach)**
Two LPF paths are run in parallel:
- *Low filter* (~80–100Hz cutoff): isolates the fundamental for the E and A string range, cutting the 2nd harmonic of the low E (82Hz)
- *High filter* (~350Hz cutoff): isolates the fundamental for the D and G string range, cutting harmonics above the 311Hz upper limit

Band energy in the low and mid frequency regions is compared to select which filter's zero crossing output to use. The filter cutoff frequencies and energy switching threshold are key tuning parameters.

**Dual low-pass filter with energy-based switching (primary)**
Two LPF paths run in parallel:
- *Low filter* (~80–100Hz cutoff): for E and A string range
- *High filter* (~350Hz cutoff): for D and G string range

Band energy comparison selects which filter's crossings to trust. The cutoff frequencies and switching threshold are key tuning parameters.

**Peak-to-envelope ratio (strong backup)**
For bass guitar, most of the amplitude information is in the peaks of the waveform, not the zero crossing area. The fundamental dominates the peaks because harmonic phases tend to align there. A positive peak that reaches close to the slow envelope level is almost certainly from the fundamental — harmonic bumps mid-cycle peak well below the envelope. This makes peak-based pitch detection potentially more robust than zero-crossing-based approaches for this signal type. Zero crossings remain the right tool for the actual loop transition timing, but peak tracking could be used to estimate the fundamental period and gate which zero crossings are valid.

**Derivative magnitude at crossing (not recommended)**
Initial investigation showed that the derivative `x - x'` at a zero crossing does not reliably discriminate fundamental crossings from harmonic-induced spurious crossings. At a zero crossing the signal is mid-swing and all harmonics contribute to the slope simultaneously, so there is no clean separation. The ZC detector still emits the derivative as a probe output (output 4) for completeness, but it is not expected to be useful as a primary filter.

## Dual Fractional Delay Line

This block contains a delay buffer of a fixed size. It has three inputs: the input signal and two delay time inputs. It has two outputs corresponding to the delayed signal at each tap. The two taps share a single write buffer and operate in ping-pong fashion during crossfades.

Two taps are sufficient for loop-first development on sustained signals. The final pipeline will use **three taps** to handle attack-during-loop-crossfade cleanly; see the planned three-tap design in *Open Issues*.

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

- **Below lower threshold** No search, just record.
- **Above lower threshold:** Search for period-aligned candidates (strict matching). (FUTURE, for now any zero crossing is good enough)
- **As latency continues to grow:** The acceptable tolerance for period alignment widens, allowing candidates that are not perfectly integer-period-aligned. (FUTURE, for now any zero crossing is good enough)
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

If an attack is detected while a loop crossfade is already in progress, both a fade-out and a new fade-in need to happen simultaneously. With only two taps, the tap being faded out is not available for the attack reset, forcing a compromise: either abort the in-progress crossfade (audible) or delay the attack response (loses transient).

**Decision:** the final pipeline will use **three delay taps** rather than two, so that the in-progress crossfade can complete its fade-out on one tap while the attack reset fades in on a third. The dual-tap implementation remains adequate for validating loop-detection behaviour in isolation (loop-first development ordering); the third tap is added once the loop logic is tuned and the attack detector is brought back into the pipeline.

Implementation implications:
- `Dual Tap Delay` becomes a `Tri Tap Delay` with three independent read positions on the shared buffer.
- The control logic tracks three tap delays and three gains instead of two, plus a "next free tap" selector (or LRU policy) for routing reset events.
- The crossfade model generalises from "active/inactive" to "fading-out / steady / fading-in" with at most one tap in each role at any moment.