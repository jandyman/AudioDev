// Split and gain example - Faust DSP
// One input, two outputs:
//   Output 1: passes input directly
//   Output 2: applies 0.5 gain to input

import("stdfaust.lib");

// Process function: split input to two outputs
// First output: identity (pass through)
// Second output: multiply by 0.5
process = _ <: _, *(0.5);
