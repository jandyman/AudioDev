// Simple gain processor - Faust DSP
// Demonstrates basic Faust parameter and processing

import("stdfaust.lib");

// Parameter: gain (0.0 to 2.0, default 1.0)
gain = hslider("gain", 1.0, 0.0, 2.0, 0.01);

// Process function: multiply input by gain
process = *(gain);
