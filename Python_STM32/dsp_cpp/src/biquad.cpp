// biquad.cpp — Biquad coefficient computation + EqChannel implementation.
//
// Hi-shelf: Audio EQ Cookbook (R. Bristow-Johnson), shelf slope S=1.
// Low-pass: cookbook LPF biquad with Butterworth Q = 1/√2. Double zero at
// z=-1 (Nyquist), so the filter goes to full attenuation there.
//
// Storage convention: cookbook's a1/a2 appear with a minus sign in the
// difference equation, so we negate them at store time. The per-sample
// loop in Biquad::process() uses additions for all five terms.
//
// NOTE: We deliberately do NOT include <math.h> or <cmath> for the STM32
// build. Under -ffreestanding, libstdc++ 14's <math.h> drags in TR1
// special-function templates that fail to compile in hosted mode.
// GCC __builtin_* intrinsics (sinf, cosf, powf, sqrtf) lower to VFP
// instructions on Cortex-M7 without any header. On macOS/clang these
// builtins also work without the header.

#include "biquad.h"

namespace {
constexpr float kPi       = 3.14159265358979323846f;
constexpr float kInvSqrt2 = 0.70710678118654752440f;  // 1/√2 — Butterworth Q
}

BiquadCoeffs biquad_compute_hishelf(float gain_db, float fc_hz, float sample_rate) {
  // A = 10^(dBgain/40); w0 in radians; alpha = sin(w0)/√2 for S=1.
  const float A    = __builtin_powf(10.0f, gain_db * 0.025f);
  const float w0   = 2.0f * kPi * fc_hz / sample_rate;
  const float sw0  = __builtin_sinf(w0);
  const float cw0  = __builtin_cosf(w0);
  const float alp  = sw0 * kInvSqrt2;
  const float sqA  = __builtin_sqrtf(A);
  const float Am1  = A - 1.0f;
  const float Ap1  = A + 1.0f;
  const float tsa  = 2.0f * sqA * alp;

  const float b0    =  A * (Ap1 + Am1 * cw0 + tsa);
  const float b1    = -2.0f * A * (Am1 + Ap1 * cw0);
  const float b2    =  A * (Ap1 + Am1 * cw0 - tsa);
  const float a0    =        Ap1 - Am1 * cw0 + tsa;
  const float a1_ck =  2.0f * (Am1 - Ap1 * cw0);
  const float a2_ck =         Ap1 - Am1 * cw0 - tsa;

  const float inv_a0 = 1.0f / a0;
  BiquadCoeffs c;
  c.b0 =  b0    * inv_a0;
  c.b1 =  b1    * inv_a0;
  c.b2 =  b2    * inv_a0;
  c.a1 = -a1_ck * inv_a0;
  c.a2 = -a2_ck * inv_a0;
  return c;
}

BiquadCoeffs biquad_compute_lpf_butterworth(float fc_hz, float sample_rate) {
  // Cookbook LPF with Q = 1/√2. Double zero at z=-1 → full attenuation at Nyquist.
  const float w0   = 2.0f * kPi * fc_hz / sample_rate;
  const float sw0  = __builtin_sinf(w0);
  const float cw0  = __builtin_cosf(w0);
  const float alp  = sw0 * kInvSqrt2;
  const float omc  = 1.0f - cw0;

  const float b0    =  0.5f * omc;
  const float b1    =         omc;
  const float b2    =  0.5f * omc;
  const float a0    =  1.0f + alp;
  const float a1_ck = -2.0f * cw0;
  const float a2_ck =  1.0f - alp;

  const float inv_a0 = 1.0f / a0;
  BiquadCoeffs c;
  c.b0 =  b0    * inv_a0;
  c.b1 =  b1    * inv_a0;
  c.b2 =  b2    * inv_a0;
  c.a1 = -a1_ck * inv_a0;
  c.a2 = -a2_ck * inv_a0;
  return c;
}

void EqChannel::init(float shelf_gain_db, float shelf_fc_hz, float lp_fc_hz,
                     float sample_rate) {
  const BiquadCoeffs shelf_c = biquad_compute_hishelf(shelf_gain_db, shelf_fc_hz, sample_rate);
  const BiquadCoeffs lp_c    = biquad_compute_lpf_butterworth(lp_fc_hz, sample_rate);
  shelf_.set_coeffs(shelf_c);
  lp_.set_coeffs(lp_c);
  staged_shelf_ = shelf_c;
  staged_lp_    = lp_c;
}

void EqChannel::recompute(float shelf_gain_db, float shelf_fc_hz, float lp_fc_hz,
                          float sample_rate) {
  staged_shelf_ = biquad_compute_hishelf(shelf_gain_db, shelf_fc_hz, sample_rate);
  staged_lp_    = biquad_compute_lpf_butterworth(lp_fc_hz, sample_rate);
}
