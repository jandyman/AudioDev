// eq.cpp — Firmware wiring between the biquad EQ (dsp_cpp) and the parameter
// tree. The three free functions here are the only call surface used by
// main.cpp and audio.cpp.

#include "eq.h"
#include "audio.h"    // AUDIO_SAMPLE_RATE
#include "params.h"

EqChannel eq_ch[2];

void eq_init() {
  for (int ch = 0; ch < 2; ++ch) {
    eq_ch[ch].init(eq_params[ch].shelf_gain->value,
                   eq_params[ch].shelf_fc->value,
                   eq_params[ch].lp_fc->value,
                   AUDIO_SAMPLE_RATE);
  }
}

void eq_recompute_from_params() {
  for (int ch = 0; ch < 2; ++ch) {
    eq_ch[ch].recompute(eq_params[ch].shelf_gain->value,
                        eq_params[ch].shelf_fc->value,
                        eq_params[ch].lp_fc->value,
                        AUDIO_SAMPLE_RATE);
  }
}

void eq_apply_new_coefficients() {
  for (int ch = 0; ch < 2; ++ch) {
    eq_ch[ch].apply_new_coefficients();
  }
}
