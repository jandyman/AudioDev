// eq.cpp — Biquad coefficient computation + EqChannel implementation.
//
// Hi-shelf: Audio EQ Cookbook (R. Bristow-Johnson), shelf slope S=1.
// Low-pass: cookbook LPF biquad with Butterworth Q = 1/√2. Double zero at
// z=-1 (Nyquist), so the filter goes to 0 there.
//
// Storage convention: cookbook's a1/a2 appear with a minus sign in the
// difference equation, so we negate them at store time. The per-sample
// loop in Biquad::process() then uses additions for all five terms —
// slightly faster and matches the way ARM CMSIS DSP stores biquads too.

// We deliberately do NOT include <math.h> or <cmath>. Under -ffreestanding,
// libstdc++ 14's <math.h> drags in TR1 special-function templates (Bessel,
// gamma, Riemann zeta...) that require hosted mode and fail to compile.
// All we need is sin/cos/pow/sqrt for biquad coefficient calc — GCC exposes
// these as __builtin_* intrinsics that lower to single VFP instructions on
// Cortex-M7 (VSIN/VCOS/VSQRT) or call into libm (powf) without any header.

#include "eq.h"
#include "params.h"

EqChannel eq_ch[2];

namespace {
constexpr float kPi       = 3.14159265358979323846f;
constexpr float kInvSqrt2 = 0.70710678118654752440f;  // 1/√2 — Butterworth Q
}

// ---------------------------------------------------------------------------
// Free-function coefficient generators (pure math, no state)
// ---------------------------------------------------------------------------

BiquadCoeffs biquad_compute_hishelf(float gain_db, float fc_hz) {
  // A = 10^(dBgain/40); w0 in radians; alpha = sin(w0)/√2 for S=1.
  const float A    = __builtin_powf(10.0f, gain_db * 0.025f);
  const float w0   = 2.0f * kPi * fc_hz / AUDIO_SAMPLE_RATE;
  const float sw0  = __builtin_sinf(w0);
  const float cw0  = __builtin_cosf(w0);
  const float alp  = sw0 * kInvSqrt2;
  const float sqA  = __builtin_sqrtf(A);     // VSQRT.F32 — no libm wrapper
  const float Am1  = A - 1.0f;
  const float Ap1  = A + 1.0f;
  const float tsa  = 2.0f * sqA * alp;

  const float b0    =  A * (Ap1 + Am1 * cw0 + tsa);
  const float b1    = -2.0f * A * (Am1 + Ap1 * cw0);
  const float b2    =  A * (Ap1 + Am1 * cw0 - tsa);
  const float a0    =        Ap1 - Am1 * cw0 + tsa;
  const float a1_ck =  2.0f * (Am1 - Ap1 * cw0);   // cookbook sign
  const float a2_ck =         Ap1 - Am1 * cw0 - tsa;

  const float inv_a0 = 1.0f / a0;
  BiquadCoeffs c;
  c.b0 =  b0    * inv_a0;
  c.b1 =  b1    * inv_a0;
  c.b2 =  b2    * inv_a0;
  c.a1 = -a1_ck * inv_a0;     // negate: cookbook subtract → additive storage
  c.a2 = -a2_ck * inv_a0;
  return c;
}

BiquadCoeffs biquad_compute_lpf_butterworth(float fc_hz) {
  // Cookbook LPF with Q = 1/√2. Numerator (1 + 2z^-1 + z^-2)·(1-cos w0)/2
  // has a double zero at z=-1 → full attenuation at Nyquist.
  const float w0   = 2.0f * kPi * fc_hz / AUDIO_SAMPLE_RATE;
  const float sw0  = __builtin_sinf(w0);
  const float cw0  = __builtin_cosf(w0);
  const float alp  = sw0 * kInvSqrt2;        // sin(w0)/(2Q) with Q=1/√2
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

// ---------------------------------------------------------------------------
// EqChannel methods
// ---------------------------------------------------------------------------

void EqChannel::init(float shelf_gain_db, float shelf_fc_hz, float lp_fc_hz) {
  const BiquadCoeffs shelf_c = biquad_compute_hishelf(shelf_gain_db, shelf_fc_hz);
  const BiquadCoeffs lp_c    = biquad_compute_lpf_butterworth(lp_fc_hz);

  // Live and staging start identical — so an early ISR firing of READY
  // (shouldn't happen, but cheap to be safe) is a no-op.
  shelf_.set_coeffs(shelf_c);
  lp_.set_coeffs(lp_c);
  staged_shelf_ = shelf_c;
  staged_lp_    = lp_c;
}

void EqChannel::recompute(float shelf_gain_db, float shelf_fc_hz,
                          float lp_fc_hz) {
  staged_shelf_ = biquad_compute_hishelf(shelf_gain_db, shelf_fc_hz);
  staged_lp_    = biquad_compute_lpf_butterworth(lp_fc_hz);
}

// ---------------------------------------------------------------------------
// Free-function fan-out used by main.cpp and audio.cpp
// ---------------------------------------------------------------------------

void eq_init() {
  for (int ch = 0; ch < 2; ++ch) {
    eq_ch[ch].init(eq_params[ch].shelf_gain->value,
                   eq_params[ch].shelf_fc->value,
                   eq_params[ch].lp_fc->value);
  }
}

void eq_recompute_from_params() {
  for (int ch = 0; ch < 2; ++ch) {
    eq_ch[ch].recompute(eq_params[ch].shelf_gain->value,
                        eq_params[ch].shelf_fc->value,
                        eq_params[ch].lp_fc->value);
  }
}

void eq_apply_new_coefficients() {
  for (int ch = 0; ch < 2; ++ch) {
    eq_ch[ch].apply_new_coefficients();
  }
}
