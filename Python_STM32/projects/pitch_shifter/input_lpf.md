# Input Low-Pass Filter

2nd-order Butterworth low-pass at 10 kHz, sitting ahead of all detectors (ZC,
attack, harmonic rejector) and the delay buffer. Bass guitar has effectively no
useful content above 10 kHz, and a 2nd-order biquad's in-band group delay at this
cutoff is negligible (~10 µs near `fc` at 48 kHz), so the latency cost is
invisible next to the loop-crossfade / pitch-shift latencies.

`fc` is exposed as a parameter so the demo can sweep it for tuning.
