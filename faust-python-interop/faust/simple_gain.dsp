// Simple gain example - Faust DSP
// Demonstrates basic signal processing

import("stdfaust.lib");

// Single parameter: gain (0.0 to 1.0)
gain = hslider("gain", 0.5, 0.0, 1.0, 0.01);

// Process function: multiply input by gain
process = *(gain);
