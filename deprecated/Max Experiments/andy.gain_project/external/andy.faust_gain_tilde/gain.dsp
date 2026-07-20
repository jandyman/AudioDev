// Simple gain processor for Max/MSP
// Matches andy.gain_tilde functionality

import("stdfaust.lib");

// Declare gain parameter
// Range 0-10, default 1.0 (unity gain)
gain = hslider("gain", 1.0, 0.0, 10.0, 0.01);

// Process: multiply input by gain
process = _ * gain;
