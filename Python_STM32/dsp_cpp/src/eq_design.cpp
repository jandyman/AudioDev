// eq_design.cpp — Biquad filter coefficient generation.
//
// LP/HP: Butterworth cascade. Each 2nd-order section uses the k-th Butterworth
// Q value; odd orders add a 1st-order section.
//
// LS/HS: Shelf filters using Butterworth-derived Q values per section.
// Gain is distributed proportionally to the pole count of each section
// (1st-order gets gain*1/N, each 2nd-order gets gain*2/N), so the total
// plateau gain equals gain_db when sections are cascaded.
//
// BP: Audio EQ Cookbook peaking EQ, fixed order 2.
//
// Storage convention: cookbook a1/a2 (minus-sign terms) stored negated —
// process() uses additions throughout. See biquad.h.
//
// No <math.h> include: GCC __builtin_* intrinsics lower to VFP on Cortex-M7
// and work on macOS/clang without a header.

#include "eq_design.h"

namespace {

constexpr float kPi = 3.14159265358979323846f;

// Butterworth Q for the k-th 2nd-order section of an N-th order filter.
// k in [1 .. floor(N/2)]. Formula: Q_k = 1 / (2 * sin(pi*(2k-1)/(2N))).
float bw_q(int k, int N) {
  return 1.0f / (2.0f * __builtin_sinf(kPi * (float)(2*k - 1) / (float)(2*N)));
}

// ---- First-order sections --------------------------------------------------

BiquadCoeffs lp1(float K) {
  // H(z) = K/(1+K) * (1+z^-1) / (1 - (K-1)/(K+1)*z^-1)
  float inv = 1.0f / (1.0f + K);
  BiquadCoeffs c{};
  c.b0 =  K * inv;
  c.b1 =  K * inv;
  c.a1 = (1.0f - K) * inv;  // negated: -(K-1)/(1+K)
  return c;
}

BiquadCoeffs hp1(float K) {
  // Same pole as lp1, numerator flipped.
  float inv = 1.0f / (1.0f + K);
  BiquadCoeffs c{};
  c.b0 =  inv;
  c.b1 = -inv;
  c.a1 = (1.0f - K) * inv;
  return c;
}

BiquadCoeffs loshelf1(float K, float A) {
  // H(z) = ((1+AK) + (AK-1)z^-1) / ((1+K) + (K-1)z^-1)
  float inv = 1.0f / (1.0f + K);
  BiquadCoeffs c{};
  c.b0 = (1.0f + A * K) * inv;
  c.b1 = (A * K - 1.0f) * inv;
  c.a1 = (1.0f - K) * inv;
  return c;
}

BiquadCoeffs hishelf1(float K, float A) {
  // H(z) = ((A+K) + (K-A)z^-1) / ((1+K) + (K-1)z^-1)
  float inv = 1.0f / (1.0f + K);
  BiquadCoeffs c{};
  c.b0 = (A + K) * inv;
  c.b1 = (K - A) * inv;
  c.a1 = (1.0f - K) * inv;
  return c;
}

// ---- Second-order sections -------------------------------------------------

BiquadCoeffs lp2(float K, float Q) {
  float norm = 1.0f + K / Q + K * K;
  float inv  = 1.0f / norm;
  BiquadCoeffs c{};
  c.b0 =  K * K * inv;
  c.b1 =  2.0f * K * K * inv;
  c.b2 =  K * K * inv;
  c.a1 = -(2.0f * (K * K - 1.0f)) * inv;
  c.a2 = -(1.0f - K / Q + K * K) * inv;
  return c;
}

BiquadCoeffs hp2(float K, float Q) {
  // Same denominator as lp2, numerator is 1, -2, 1 (zeros at DC).
  float norm = 1.0f + K / Q + K * K;
  float inv  = 1.0f / norm;
  BiquadCoeffs c{};
  c.b0 =  inv;
  c.b1 = -2.0f * inv;
  c.b2 =  inv;
  c.a1 = -(2.0f * (K * K - 1.0f)) * inv;
  c.a2 = -(1.0f - K / Q + K * K) * inv;
  return c;
}

// Audio EQ Cookbook lo-shelf with externally supplied alpha = sin(w0)/(2*Q).
// Passing alpha instead of S lets each section use its Butterworth-derived Q.
BiquadCoeffs loshelf2(float w0, float A, float alpha) {
  float cw   = __builtin_cosf(w0);
  float sqA  = __builtin_sqrtf(A);
  float Am1  = A - 1.0f, Ap1 = A + 1.0f;
  float tsa  = 2.0f * sqA * alpha;

  float b0    =   A * (Ap1 - Am1 * cw + tsa);
  float b1    = 2.0f * A * (Am1 - Ap1 * cw);
  float b2    =   A * (Ap1 - Am1 * cw - tsa);
  float a0    =         Ap1 + Am1 * cw + tsa;
  float a1_ck =  -2.0f * (Am1 + Ap1 * cw);
  float a2_ck =          Ap1 + Am1 * cw - tsa;

  float inv = 1.0f / a0;
  BiquadCoeffs c{};
  c.b0 =  b0 * inv;
  c.b1 =  b1 * inv;
  c.b2 =  b2 * inv;
  c.a1 = -a1_ck * inv;
  c.a2 = -a2_ck * inv;
  return c;
}

BiquadCoeffs hishelf2(float w0, float A, float alpha) {
  float cw   = __builtin_cosf(w0);
  float sqA  = __builtin_sqrtf(A);
  float Am1  = A - 1.0f, Ap1 = A + 1.0f;
  float tsa  = 2.0f * sqA * alpha;

  float b0    =    A * (Ap1 + Am1 * cw + tsa);
  float b1    = -2.0f * A * (Am1 + Ap1 * cw);
  float b2    =    A * (Ap1 + Am1 * cw - tsa);
  float a0    =          Ap1 - Am1 * cw + tsa;
  float a1_ck =   2.0f * (Am1 - Ap1 * cw);
  float a2_ck =          Ap1 - Am1 * cw - tsa;

  float inv = 1.0f / a0;
  BiquadCoeffs c{};
  c.b0 =  b0 * inv;
  c.b1 =  b1 * inv;
  c.b2 =  b2 * inv;
  c.a1 = -a1_ck * inv;
  c.a2 = -a2_ck * inv;
  return c;
}

} // namespace

// ---------------------------------------------------------------------------

void filter_design(const FilterParams& p, CascadeCoeffs& out) {
  const float K  = __builtin_tanf(kPi * p.fc_hz / p.fs_hz);
  const float w0 = 2.0f * kPi * p.fc_hz / p.fs_hz;
  const int   N  = (p.type == FilterType::BP) ? 2 : p.order;
  const int   n1 = N & 1;       // 1 if odd order (first-order section needed)
  const int   n2 = N / 2;       // number of 2nd-order sections

  out.n_sections = n1 + n2;
  int sec = 0;

  switch (p.type) {

    case FilterType::LP:
      if (n1) out.bq[sec++] = lp1(K);
      for (int k = 1; k <= n2; ++k)
        out.bq[sec++] = lp2(K, bw_q(k, N));
      break;

    case FilterType::HP:
      if (n1) out.bq[sec++] = hp1(K);
      for (int k = 1; k <= n2; ++k)
        out.bq[sec++] = hp2(K, bw_q(k, N));
      break;

    case FilterType::LS: {
      // Gain per section proportional to its pole count so cascade total = gain_db.
      // 1st-order: gain_db * 1/N;  each 2nd-order: gain_db * 2/N.
      if (n1) {
        float A = __builtin_powf(10.0f, p.gain_db / (float)N * 0.025f);
        out.bq[sec++] = loshelf1(K, A);
      }
      for (int k = 1; k <= n2; ++k) {
        float A     = __builtin_powf(10.0f, p.gain_db * 2.0f / (float)N * 0.025f);
        float alpha = __builtin_sinf(w0) / (2.0f * bw_q(k, N));
        out.bq[sec++] = loshelf2(w0, A, alpha);
      }
      break;
    }

    case FilterType::HS: {
      if (n1) {
        float A = __builtin_powf(10.0f, p.gain_db / (float)N * 0.025f);
        out.bq[sec++] = hishelf1(K, A);
      }
      for (int k = 1; k <= n2; ++k) {
        float A     = __builtin_powf(10.0f, p.gain_db * 2.0f / (float)N * 0.025f);
        float alpha = __builtin_sinf(w0) / (2.0f * bw_q(k, N));
        out.bq[sec++] = hishelf2(w0, A, alpha);
      }
      break;
    }

    case FilterType::BP: {
      // Peaking EQ: gain A at fc, unity away from fc.
      float A     = __builtin_powf(10.0f, p.gain_db * 0.025f);
      float sw0   = __builtin_sinf(w0);
      float cw0   = __builtin_cosf(w0);
      float alpha = sw0 / (2.0f * p.q);
      float a0    = 1.0f + alpha / A;
      float inv   = 1.0f / a0;

      BiquadCoeffs c{};
      c.b0 =  (1.0f + alpha * A) * inv;
      c.b1 =  (-2.0f * cw0)     * inv;
      c.b2 =  (1.0f - alpha * A) * inv;
      c.a1 =  (2.0f * cw0)      * inv;   // negated: -(-2*cw0/a0)
      c.a2 = -(1.0f - alpha / A) * inv;  // negated: -(1-alpha/A)/a0
      out.bq[sec++] = c;
      out.n_sections = 1;  // set directly (N forced to 2 above but BP is 1 section)
      break;
    }
  }
}
