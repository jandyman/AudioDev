// eq.h — Stereo EQ: 2-pole hi-shelf + 2-pole low-pass per channel.
//
// Both filters are biquads in Direct Form I. The hi-shelf uses the Audio EQ
// Cookbook formula with shelf slope S=1. The low-pass is a cookbook biquad
// with Butterworth Q (1/√2) — double zero at z=-1 (Nyquist), full
// attenuation there.
//
// Both filters share the positive-feedback storage convention: cookbook
// a1/a2 (which appear with a minus sign in the difference equation) are
// negated at store time so the per-sample loop uses additions throughout.
//
// Coefficient/state separation
// ----------------------------
// `BiquadCoeffs` holds just the five filter coefficients (b0, b1, b2, a1,
// a2) — no delay-line state. `Biquad` is the live filter: it OWNS the
// delay line and contains a BiquadCoeffs that the foreground can replace
// via set_coeffs(). This separation is what makes the foreground/ISR
// handshake non-glitching: applying new coefficients does NOT touch
// x1/x2/y1/y2, so the filter does not reset to silence each time the user
// drags a slider.
//
// Handshake protocol (full picture)
// ---------------------------------
//   1. Host writes a param value (ParamNode::value) via OpenOCD.
//   2. Host sets params_dirty bit 0 (DIRTY).
//   3. Foreground loop sees DIRTY → clears DIRTY → calls
//      eq_recompute_from_params() → sets bit 1 (READY). Clearing DIRTY
//      before recompute is what catches host writes mid-recompute.
//   4. Audio ISR sees READY → calls eq_apply_new_coefficients() (a 10-float
//      copy per channel) → clears all flags.
//
// Threading model
// ---------------
//   * Per-sample process() runs in the audio ISR. Must inline.
//   * recompute() runs in the foreground main loop. Trig is fine here.
//   * apply_new_coefficients() runs in the ISR. Plain assignment of
//     BiquadCoeffs; the few-cycle window of partial overwrite is inaudible.
//
// params_init() must be called before eq_init().

#pragma once

#include "audio.h"   // AUDIO_SAMPLE_RATE

// Just the five filter coefficients — no delay-line state.
struct BiquadCoeffs {
  float b0 = 0.f;
  float b1 = 0.f;
  float b2 = 0.f;
  float a1 = 0.f;  // stored negated relative to cookbook (see eq.cpp)
  float a2 = 0.f;
};

// Audio EQ Cookbook formulas. Free functions because they're pure math —
// no state, no I/O. AUDIO_SAMPLE_RATE is baked in (changes require a rebuild).
BiquadCoeffs biquad_compute_hishelf(float gain_db, float fc_hz);
BiquadCoeffs biquad_compute_lpf_butterworth(float fc_hz);

// Direct Form I biquad: a five-coeff filter plus a four-sample delay line.
// process() is in the header so the ISR can inline it. set_coeffs()
// replaces the coefficients without touching the delay line — this is what
// allows live parameter updates without clicks.
class Biquad {
 public:
  // One sample in, one sample out. Always-inlined into the ISR hot path.
  __attribute__((always_inline))
  float process(float x) {
    const float y = c_.b0 * x
                  + c_.b1 * x1_ + c_.b2 * x2_
                  + c_.a1 * y1_ + c_.a2 * y2_;
    x2_ = x1_; x1_ = x;
    y2_ = y1_; y1_ = y;
    return y;
  }

  // Replace the coefficients without disturbing the delay line.
  void set_coeffs(const BiquadCoeffs& c) { c_ = c; }

 private:
  BiquadCoeffs c_{};
  float x1_ = 0.f, x2_ = 0.f, y1_ = 0.f, y2_ = 0.f;
};

// One audio channel through the EQ chain: hi-shelf → low-pass.
//
// Holds the live filters AND the staging coefficients. recompute() (called
// in the foreground) writes staging; apply_new_coefficients() (called in
// the ISR) commits staging into the live filters.
class EqChannel {
 public:
  // Per-sample, both biquads. Inlined into the ISR.
  __attribute__((always_inline))
  float process(float x) {
    return lp_.process(shelf_.process(x));
  }

  // Set initial coefficients on both live AND staged biquads. Called once
  // from eq_init() so the filters have valid coefficients before the audio
  // ISR runs.
  void init(float shelf_gain_db, float shelf_fc_hz, float lp_fc_hz);

  // Compute new coefficients into the staging fields. Foreground only;
  // does not touch the live biquads.
  void recompute(float shelf_gain_db, float shelf_fc_hz, float lp_fc_hz);

  // Commit staging coefficients into the live biquads. ISR only.
  // Does not touch delay-line state.
  __attribute__((always_inline))
  void apply_new_coefficients() {
    shelf_.set_coeffs(staged_shelf_);
    lp_.set_coeffs(staged_lp_);
  }

 private:
  Biquad shelf_;
  Biquad lp_;
  BiquadCoeffs staged_shelf_{};
  BiquadCoeffs staged_lp_{};
};

// [0] = L, [1] = R.
extern EqChannel eq_ch[2];

// ---- Free functions wired up to the parameter tree -----------------------
// These are the call surface used by main.cpp and audio.cpp. They each
// fan out to both channels by reading from eq_params[] (declared in params.h).

// Must be called after params_init(). Reads initial parameter values and
// seeds both live and staged coefficients in each channel.
void eq_init();

// Foreground: read parameter values and write new coefficients into the
// staging fields of every channel. Does not touch live filters.
void eq_recompute_from_params();

// ISR: copy staging coefficients into live filters on every channel.
void eq_apply_new_coefficients();
