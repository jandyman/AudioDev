// biquad.h — Direct Form I biquad filter + Audio EQ Cookbook coefficient generators.
//
// BiquadCoeffs: five filter coefficients, no state.
// Biquad: owns the delay line; process() inlines into the ISR hot path.
// EqChannel: hi-shelf → low-pass chain with foreground/ISR staging handshake.
//
// Coefficient storage convention: cookbook a1/a2 (which appear with a minus
// sign in the difference equation) are negated at store time, so process()
// uses additions throughout. Matches ARM CMSIS-DSP biquad storage.
//
// Threading model:
//   process()               — audio ISR, must inline
//   recompute()             — foreground main loop, trig is fine
//   apply_new_coefficients() — audio ISR, plain struct assignment

#pragma once

// Just the five filter coefficients — no delay-line state.
struct BiquadCoeffs {
  float b0 = 0.f;
  float b1 = 0.f;
  float b2 = 0.f;
  float a1 = 0.f;  // stored negated relative to cookbook
  float a2 = 0.f;
};

// Audio EQ Cookbook formulas. sample_rate is passed explicitly so these
// functions compile identically for STM32 and Mac-native targets.
BiquadCoeffs biquad_compute_hishelf(float gain_db, float fc_hz, float sample_rate);
BiquadCoeffs biquad_compute_lpf_butterworth(float fc_hz, float sample_rate);

// Direct Form I biquad: five coefficients + four-sample delay line.
// process() is in the header so the ISR can always_inline it.
// set_coeffs() replaces coefficients without touching the delay line —
// this prevents clicks on live parameter updates.
class Biquad {
 public:
  __attribute__((always_inline))
  float process(float x) {
    const float y = c_.b0 * x
                  + c_.b1 * x1_ + c_.b2 * x2_
                  + c_.a1 * y1_ + c_.a2 * y2_;
    x2_ = x1_; x1_ = x;
    y2_ = y1_; y1_ = y;
    return y;
  }

  void set_coeffs(const BiquadCoeffs& c) { c_ = c; }

 private:
  BiquadCoeffs c_{};
  float x1_ = 0.f, x2_ = 0.f, y1_ = 0.f, y2_ = 0.f;
};

// One audio channel: hi-shelf → low-pass biquad chain.
// Holds live filters AND staged coefficients for the foreground/ISR handshake.
// recompute() (foreground) writes staging; apply_new_coefficients() (ISR) commits.
class EqChannel {
 public:
  __attribute__((always_inline))
  float process(float x) {
    return lp_.process(shelf_.process(x));
  }

  // Seed both live and staged coefficients. Call once before audio ISR starts.
  void init(float shelf_gain_db, float shelf_fc_hz, float lp_fc_hz, float sample_rate);

  // Write new coefficients into staging fields. Foreground only.
  void recompute(float shelf_gain_db, float shelf_fc_hz, float lp_fc_hz, float sample_rate);

  // Commit staged coefficients into live filters. ISR only.
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
