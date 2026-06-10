// Varispeed wrapper around triple_tap_delay.
// Exposes a single `ratio` parameter; drives tap1's delay as a linear ramp.
// Taps 2 and 3 are tied to 0 ms and eliminated by Faust's dead-code pass.
//
// Inherited constraint: triple_tap_delay's buffer is 300 ms at 48 kHz,
// so max input duration is roughly 0.3 / (1 - ratio) seconds.

import("stdfaust.lib");
tt = library("triple_tap_delay.dsp");

ratio = nentry("ratio", 0.85, 0.5, 1.0, 0.001);

process(audio_in) = tt.process(audio_in, delay_ms, 0.0, 0.0) : _, !, !
with {
  t = (+(1) ~ _) - 1;                              // 0, 1, 2, ... output-sample counter
  delay_ms = (1.0 - ratio) * t * 1000.0 / ma.SR;   // linear ramp in ms
};
