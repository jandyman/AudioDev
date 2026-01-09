# PitchShifter Project - Claude Context

Real-time pitch shifting algorithm specifically designed for bass guitar signals.

---

## Project Overview

**Purpose:** Implement a downward pitch shifter for bass guitar using dual delay lines with intelligent loop point detection

**Target Applications:**
- Octave dropper effect
- Sub-bass generation
- Bass guitar pitch effects

**Key Constraint:** Pitch can only be shifted downward (not upward)

---

## Core Algorithm Concept

### Signal Flow
```
Input Signal → Delay Buffer → Dual Fractional Delay Lines → Crossfaded Output
                    ↓
            Attack Detector ──→ Control Logic
                    ↓
         Zero Crossing Detector ─┘
```

### Dual Delay Line Technique
- Two delay taps share a single delay buffer
- Operate in ping-pong fashion for glitch-free crossfading
- Variable delay time increases at constant rate (fractional delay for non-octave intervals)
- Playback at reduced sampling rate lowers pitch

### Latency Management
- Latency gradually increases during sustain
- Must reset delay times periodically to control latency
- Two reset triggers with different priorities

---

## Functional Blocks

### 1. Attack Detector
**Function:** Detect note attack transients

**Output:** Impulse stream (1 = attack detected, 0 = no attack)

**Purpose:** Preserve attack character by resetting delay to near-zero on new notes

**Priority:** Highest - overrides all other logic

### 2. Zero Crossing Detector
**Function:** Identify zero crossings in input signal

**Output:** Impulse stream marking zero crossing points

**Purpose:** Find clean loop points for artifact-free delay resets

### 3. Dual Fractional Delay Line
**Inputs:**
- Input signal
- Two delay time control signals (one per tap)

**Outputs:**
- Two delayed signals (crossfaded for final output)

**Buffer:** Fixed-size delay buffer shared by both taps

### 4. Control Logic
**Inputs:**
- Attack detector impulses
- Zero crossing detector impulses
- Current latency state

**Outputs:**
- Two delay time control signals
- Crossfade control

**Responsibilities:**
- Manage delay time resets
- Orchestrate crossfades between delay taps
- Implement looping strategy

---

## Reset Triggers

### Trigger 1: Attack Detection (High Priority)
**When:** Attack impulse received from attack detector

**Action:**
1. Crossfade to inactive delay tap
2. Reset that tap's delay time to ~0
3. Reset latency counter to 0
4. Preserve early attack portion

**Result:** Minimal latency, accurate attack transient representation

### Trigger 2: Sustain Loop Points (Low Priority)
**When:** During sustain, when latency exceeds threshold

**Action:**
1. Search zero crossing history for loop candidates
2. Match zero crossings separated by integer multiples of period
3. Schedule crossfade at earlier zero crossing's playback time
4. Reset delay time to align with later zero crossing

**Purpose:** Reduce accumulated latency without artifacts

**Requirements:**
- Zero crossings must be pitch-period aligned
- Playback time of earlier crossing must be in future
- Difference in playback times must match plausible waveform period

---

## Looping Strategy Details

### Zero Crossing Record Structure
For each zero crossing, store:
- **Arrival Time (AT):** When zero crossing entered system
- **Playback Time (PT):** When it will/did play back (PT = AT + DT)
- Used to find matching loop points

### Loop Point Selection Algorithm
1. **Check latency:** If below threshold, store crossing and continue
2. **Prune history:** Remove crossings already played (current_time > PT)
3. **Find candidates:** Compare latest crossing to historical crossings
4. **Match periods:** Only consider PT differences consistent with bass guitar pitch
5. **Schedule transition:** Crossfade at earlier crossing's PT, reset delay to later crossing

### Bailout Strategy
If no valid loop point found and latency exceeds upper limit:
- Force a reset with longer crossfade time
- Accepts potential artifacts to prevent excessive latency
- Likely occurs during noise tails or unpitched content

---

## Design Trade-offs

### Attack vs. Latency
- **Longer wait before looping:** More attack character preserved, higher latency
- **Earlier looping:** Lower latency, may lose some attack detail

### Loop Point Matching
- **Stricter period matching:** Fewer artifacts, may wait longer for good match
- **Looser matching:** More opportunities to loop, potential for slight pitch modulation

### Bailout Threshold
- **Higher threshold:** Better loop quality, rare forced resets
- **Lower threshold:** More forced resets, better latency guarantee

---

## Implementation Considerations

### Data Structures
- **Delay buffer:** Circular buffer for signal storage
- **Zero crossing history:** FIFO queue with (AT, PT) records
- **State machine:** Track current active tap, crossfade state, latency

### Performance
- Real-time constraints require efficient circular buffer access
- Zero crossing search must be O(n) or better
- Fractional delay may use interpolation (linear, cubic, etc.)

### Parameters
- **Pitch shift ratio:** Determines delay time increment rate
- **Latency thresholds:** Lower (start searching) and upper (bailout)
- **Period range:** Valid bass guitar periods for loop matching
- **Crossfade time:** Attack crossfade vs. bailout crossfade
- **Attack detector sensitivity:** Trade-off between responsiveness and false triggers

---

## Potential Implementation Targets

Based on sibling projects in AudioDev:
- **Max/MSP External** (C++) - See `Max Experiments/` for template
- **Embedded Platform** (Daisy, C++) - See `DaisyExamples/`
- **Python Prototype** (SciPy) - For algorithm validation
- **Faust DSP** - Functional approach via `faust-python-interop/`

---

## Current Status

📝 **Concept Stage**
- Algorithm designed and documented
- Ready for implementation planning
- No code written yet

---

## Next Steps (Suggested)

1. **Choose implementation platform**
   - Prototype in Python (SciPy) for validation?
   - Direct to Max/MSP external for live performance?
   - Target embedded Daisy platform?

2. **Implement core blocks individually**
   - Attack detector (envelope follower + threshold?)
   - Zero crossing detector
   - Fractional delay line with interpolation
   - Control logic state machine

3. **Test with bass guitar samples**
   - Validate attack preservation
   - Measure latency behavior
   - Tune parameters for artifact-free operation

4. **Optimize performance**
   - Profile real-time execution
   - Optimize circular buffer and history search
   - Tune crossfade lengths

---

## Related Projects

- **Max Experiments**: Production template for Max/MSP externals
- **Embedded DSP DevSystem**: Python → embedded workflow (could prototype here)
- **SciPy**: Python DSP tools folder (potential prototyping location)
- **DaisyExamples**: If targeting Daisy hardware

---

## Resources

- **Project Concept:** `Pitch Shifter concept.md` (detailed algorithm description)
- **Bass Guitar Frequency Range:** E1 (41 Hz) to D4 (294 Hz) typical
  - Fundamental periods: ~3.4 ms to 24.4 ms
  - Important for loop point period matching

---

*This is a Claude Code context file for the PitchShifter project. Algorithm is conceptually designed and ready for implementation.*
