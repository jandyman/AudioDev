// eq.c — EQ filter coefficient computation and sample processing
//
// High-shelf formula from the Audio EQ Cookbook (R. Bristow-Johnson), shelf
// slope S=1. LP is a Butterworth biquad (Q = 1/sqrt(2)) from the same
// cookbook — double zero at z=-1 (Nyquist), so the filter goes to 0 there.
//
// Both filters share the positive-feedback storage convention: cookbook a1/a2
// (which appear with a minus sign in the difference equation) are negated at
// store time so the processing loop uses additions throughout.

#include <math.h>
#include "audio.h"
#include "eq.h"
#include "params.h"

EqChannel eq_ch[2];        // Live coefficients (ISR reads)
EqChannel eq_new_ch[2];    // Staging buffer (background writes)

static float prev_shelf_gain[2];
static float prev_shelf_fc[2];
static float prev_lp_fc[2];

#define PI_F           3.14159265358979323846f
#define INV_SQRT2_F    0.70710678118654752440f   // 1/sqrt(2) — Butterworth Q

static void compute_hishelf(Biquad *bq, float gain_db, float fc_hz) {
  // A = 10^(dBgain/40); w0 in radians; alpha = sin(w0)/sqrt(2) for S=1
  float A   = powf(10.0f, gain_db * 0.025f);
  float w0  = 2.0f * PI_F * fc_hz / AUDIO_SAMPLE_RATE;
  float sw0 = sinf(w0);
  float cw0 = cosf(w0);
  float alp = sw0 * INV_SQRT2_F;             // sin(w0) / sqrt(2)
  float sqA = __builtin_sqrtf(A);            // VSQRT.F32 — no libm wrapper
  float Am1 = A - 1.0f;
  float Ap1 = A + 1.0f;
  float tsa = 2.0f * sqA * alp;              // 2*sqrt(A)*alpha

  float b0    =  A * (Ap1 + Am1 * cw0 + tsa);
  float b1    = -2.0f * A * (Am1 + Ap1 * cw0);
  float b2    =  A * (Ap1 + Am1 * cw0 - tsa);
  float a0    =       Ap1 - Am1 * cw0 + tsa;
  float a1_ck =  2.0f * (Am1 - Ap1 * cw0);   // cookbook sign: subtract
  float a2_ck =         Ap1 - Am1 * cw0 - tsa;

  float inv_a0 = 1.0f / a0;
  bq->b0 =  b0    * inv_a0;
  bq->b1 =  b1    * inv_a0;
  bq->b2 =  b2    * inv_a0;
  bq->a1 = -a1_ck * inv_a0;                  // negate: convert subtract→add storage
  bq->a2 = -a2_ck * inv_a0;
}

// Cookbook LPF biquad with Q = 1/sqrt(2) (Butterworth, flat passband).
// Numerator (1 + 2z^-1 + z^-2)·(1-cos w0)/2 has a double zero at z=-1,
// giving full attenuation at Nyquist.
static void compute_lpf_biquad(Biquad *bq, float fc_hz) {
  float w0  = 2.0f * PI_F * fc_hz / AUDIO_SAMPLE_RATE;
  float sw0 = sinf(w0);
  float cw0 = cosf(w0);
  float alp = sw0 * INV_SQRT2_F;             // sin(w0)/(2Q) with Q=1/sqrt(2)
  float omc = 1.0f - cw0;

  float b0    =  0.5f * omc;
  float b1    =         omc;
  float b2    =  0.5f * omc;
  float a0    =  1.0f + alp;
  float a1_ck = -2.0f * cw0;                 // cookbook sign: subtract
  float a2_ck =  1.0f - alp;

  float inv_a0 = 1.0f / a0;
  bq->b0 =  b0    * inv_a0;
  bq->b1 =  b1    * inv_a0;
  bq->b2 =  b2    * inv_a0;
  bq->a1 = -a1_ck * inv_a0;                  // negate: subtract→add storage
  bq->a2 = -a2_ck * inv_a0;
}

float eq_process_biquad(Biquad *bq, float x) {
  float y = bq->b0 * x
          + bq->b1 * bq->x1 + bq->b2 * bq->x2
          + bq->a1 * bq->y1 + bq->a2 * bq->y2;
  bq->x2 = bq->x1;  bq->x1 = x;
  bq->y2 = bq->y1;  bq->y1 = y;
  return y;
}

void eq_recompute_from_params(void) {
  // Compute new coefficients into the staging buffer (eq_new_ch).
  // Called from foreground (main loop), NOT from ISR.
  // Any of the three parameters can trigger a recompute.
  for (int ch = 0; ch < 2; ch++) {
    float sg = eq_params[ch].shelf_gain->value;
    float sf = eq_params[ch].shelf_fc->value;
    float lf = eq_params[ch].lp_fc->value;

    if (sg != prev_shelf_gain[ch] || sf != prev_shelf_fc[ch]) {
      compute_hishelf(&eq_new_ch[ch].hi_shelf, sg, sf);
      prev_shelf_gain[ch] = sg;
      prev_shelf_fc[ch]   = sf;
    }
    if (lf != prev_lp_fc[ch]) {
      compute_lpf_biquad(&eq_new_ch[ch].lp, lf);
      prev_lp_fc[ch] = lf;
    }
  }
}

void eq_apply_new_coefficients(void) {
  // Atomically copy new coefficients from staging buffer into live buffer.
  // Called from ISR (process_audio) when params_dirty bit 1 (ready) is set.
  // After this, the ISR will clear both bits of params_dirty.
  for (int ch = 0; ch < 2; ch++) {
    eq_ch[ch].hi_shelf = eq_new_ch[ch].hi_shelf;
    eq_ch[ch].lp       = eq_new_ch[ch].lp;
  }
}

void eq_init(void) {
  // Initialize both live and staging buffers with current parameter values.
  for (int ch = 0; ch < 2; ch++) {
    float sg = eq_params[ch].shelf_gain->value;
    float sf = eq_params[ch].shelf_fc->value;
    float lf = eq_params[ch].lp_fc->value;

    compute_hishelf(&eq_ch[ch].hi_shelf, sg, sf);
    compute_lpf_biquad(&eq_ch[ch].lp, lf);

    compute_hishelf(&eq_new_ch[ch].hi_shelf, sg, sf);
    compute_lpf_biquad(&eq_new_ch[ch].lp, lf);

    prev_shelf_gain[ch] = sg;
    prev_shelf_fc[ch]   = sf;
    prev_lp_fc[ch]      = lf;
  }
}
