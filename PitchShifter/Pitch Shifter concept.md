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

#### Why the crossfade cannot happen immediately at input zero crossing arrival

When a zero crossing impulse arrives from the Zero Crossing Detector, the output tap is playing audio from some time in the past and is almost certainly not at a zero crossing. Executing a crossfade mid-waveform would produce a click.

Instead, the Control Logic uses the impulse to create a record and *schedule* a future transition. Because the Control Logic knows the current delay time DT, it can compute when that zero crossing will emerge from the output. The crossfade is executed at that scheduled time, at which point the output is playing the stored zero crossing — guaranteeing a clean transition.

#### Zero crossing history

When a zero crossing impulse is received, the Control Logic creates a record:
- **Arrival Time (AT):** The current sample index when the zero crossing entered the delay buffer.
- **Playback Time (PT):** The future sample index at which that zero crossing will emerge from the output tap.

PT is derived from two relationships. First, the definition of delay at output time TO with delay DO:

```
TI = TO - DO
```

Second, the delay at output time equals the input delay DI plus the delay accumulated over the intervening samples (DD is the delay increment per sample = 1 − pitch_ratio):

```
DO = DD × (TO − TI) + DI
```

Substituting the first equation into the second (TO − TI = DO):

```
DO = DD × DO + DI  →  DO = DI / (1 − DD) = DI / pitch_ratio
```

Therefore:

```
PT = AT + DI / pitch_ratio
```

where DI is the instantaneous delay at the time the zero crossing arrives. Note that the naïve formula PT = AT + DI is incorrect — it assumes the delay stays fixed after arrival, but the read head is moving at pitch_ratio speed, so it takes longer to reach AT than a simple delay offset suggests.

#### Loop candidate search

As each new input zero crossing arrives (AT_new, PT_new), the looping logic runs:

1. **Prune the history:** Remove any records whose PT has already passed (current real time > PT). Those zero crossings have already been played and cannot be used as transition targets.

2. **Check latency:** The current latency is DT (the current delay time). If latency is below a lower threshold, no action is taken beyond storing the new record.

3. **If latency is above threshold, search for a candidate:** For each remaining record (AT_old, PT_old), check whether the difference in playback times is consistent with an integer number of output-domain pitch periods:

   PT_new − PT_old ≈ N × T_output_period, where N ≥ 1

   Since PT differences are in output time and the pitch is shifted down by pitch_ratio, the output period is the input period divided by pitch_ratio. The valid range is therefore:

   T_output_period = T_input_period / pitch_ratio

   For bass guitar (E1 = 41 Hz to D4 = 294 Hz), T_input_period spans approximately 3.4 ms to 24.4 ms, so T_output_period spans 3.4/pitch_ratio ms to 24.4/pitch_ratio ms (e.g. 6.8 ms to 48.8 ms for an octave drop).

4. **If a candidate is found:** Schedule a transition at real time PT_old. At that time, the output tap will be playing the zero crossing that was recorded as AT_old — a clean transition point. The new delay at fire time will be `time_until_fire = PT_old − S` (where S is the current sample index), which must be smaller than the active tap delay at fire time to reduce latency. (Note: the new delay is *not* PT_new − PT_old; that is the period alignment check quantity, not the resulting delay.)

5. **Pre-positioning the inactive tap:** The inactive tap is set at *scheduling* time, not at fire time, so it can ramp to the correct position by the time the crossfade fires. If the inactive tap starts at `D0 = time_until_fire × pitch_ratio` now, it will ramp to `D0 + time_until_fire × dd = time_until_fire` by fire time — exactly the desired new delay. The crossfade is then executed at PT_old with no additional delay adjustment needed.

#### Urgency and relaxed matching

The need for a transition becomes more urgent as latency grows. The matching criteria relax accordingly:

- **Below lower threshold (100 ms):** No search, just record.
- **Above lower threshold:** Search for period-aligned candidates (strict matching).
- **As latency continues to grow:** The acceptable tolerance for period alignment widens, allowing candidates that are not perfectly integer-period-aligned.
- **Above upper threshold (200 ms, bailout):** Fire a transition immediately at the current input zero crossing, resetting the inactive tap to near-zero delay, using a longer crossfade time (3× the loop crossfade) to reduce the audible artifact. Waiting for the output ZC at PT is not viable: during the wait of `time_until_fire = current_delay / pitch_ratio`, the inactive tap ramps back up to approximately the same delay level, providing no latency reduction. Firing immediately accepts a non-ZC transition in the output (mitigated by the long crossfade) in exchange for effective latency reset. This is expected to occur during noise tails, unpitched transients, or other unresolvable situations.

#### Period range for candidate matching

The valid input-domain period range is based on the bass A string up to 2.5 octaves above:

- **A1 (55 Hz):** ~18.2 ms — lowest expected fundamental
- **2.5 octaves above A1 (≈ 311 Hz):** ~3.2 ms — upper limit

The output-domain period range used for PT difference matching is T_input / pitch_ratio (e.g. 3.2–18.2 ms becomes 6.4–36.4 ms for an octave drop). The exact tolerances and whether to prefer the smallest valid N will require tuning once the looping logic is running.

## Open Issues

### History buffer size

The ZC record list is a statically declared ring buffer. Dynamic memory allocation is permitted during module construction (object initialisation), but not in the audio render callback. For embedded targets, pure static allocation (compile-time fixed array as a class member) is the preferred approach and eliminates allocation concerns entirely.

At the 200 ms bailout threshold and ~3.2 ms minimum period, the worst-case record count is roughly 60–70. A 128-slot fixed array (next power of two) is a safe choice. When the buffer is full and a new record arrives before old ones have been pruned, the oldest entry is overwritten.

Sample indices can be `int32_t` (overflows after ~12 hours at 48 kHz). If long sessions on embedded hardware are a concern, timestamps can be reset to zero on each attack detection without affecting the algorithm.

### Candidate selection when multiple records match

Choose the record that produces the minimum resulting delay at fire time, which is `time_until_fire = PT_old − S`. Since PT_old is smaller for older records (they have smaller playback times), **the oldest valid record minimises latency** — not the newest. This corresponds to the largest valid N (most periods separating the two zero crossings). The search should iterate from oldest to newest record and take the first valid hit.

### Attack interrupting a loop crossfade (deferred)

If an attack is detected while a loop crossfade is already in progress, both a fade-out and a new fade-in need to happen simultaneously. With only two taps, the tap being faded out may not be available for the attack reset. A third delay tap may be needed to handle this case cleanly — allowing both the in-progress crossfade to complete its fade-out and the new attack tap to fade in independently. This issue will be revisited once the looping logic is working in isolation.