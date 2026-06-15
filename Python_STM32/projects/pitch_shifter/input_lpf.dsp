/* @block
(define-block input_lpf
 (inputs in)
 (outputs out)
 (params (fc :default 10000)))
*/

// Input low-pass filter — 2nd-order Butterworth ahead of all detectors and the
// delay buffer. Doc: input_lpf.md.

import("stdfaust.lib");

fc = hslider("fc", 10000, 100, 20000, 1);

process = fi.lowpass(2, fc);
