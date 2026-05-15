// eq.h — Firmware wiring: connects EqChannel (dsp_cpp/biquad.h) to the
// parameter tree (params.h). These three functions are the only call surface
// used by main.cpp and audio.cpp.
//
// Handshake protocol:
//   1. Host writes a param value + sets params_dirty DIRTY bit.
//   2. Foreground sees DIRTY → clears DIRTY → calls eq_recompute_from_params()
//      → sets READY bit.
//   3. Audio ISR sees READY → calls eq_apply_new_coefficients() → clears flags.
//
// params_init() must be called before eq_init().

#pragma once

#include "biquad.h"

// [0] = L, [1] = R.
extern EqChannel eq_ch[2];

// Must be called after params_init(). Seeds both live and staged coefficients.
void eq_init();

// Foreground: read params and write new coefficients into staging.
void eq_recompute_from_params();

// ISR: commit staged coefficients into live filters.
void eq_apply_new_coefficients();
