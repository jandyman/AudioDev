/* @block
(define-block input_lpf
 (inputs in)
 (outputs out)
 (params (fc :default 10000)))
*/

// Input low-pass filter for the pitch shifter pipeline.
//
// 2nd-order Butterworth at 10 kHz cutoff. Sits ahead of all detectors
// (ZC, attack) and the delay buffer. Bass guitar has effectively no
// useful content above 10 kHz, and in-band group delay of a 2nd-order
// biquad at this cutoff is negligible (~10 µs near fc at 48 kHz),
// so the latency cost is invisible relative to the loop crossfade /
// pitch-shift latencies.
//
// 1 input → 1 output.
// fc is exposed as a UI param so the demo can sweep it for tuning.

import("stdfaust.lib");

fc = hslider("fc", 10000, 100, 20000, 1);

process = fi.lowpass(2, fc);
