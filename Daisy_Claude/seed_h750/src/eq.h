// eq.h — stereo EQ: 2-pole high-shelf + 2-pole low-pass per channel
//
// Both filters are biquads in Direct Form I. The hi-shelf uses the Audio EQ
// Cookbook formula with shelf slope S=1. The LP is a Butterworth biquad
// (Q = 1/sqrt(2)) — double zero at z=-1 (Nyquist), full attenuation there.
//
// Coefficients are recomputed in eq_update_from_params() only when a
// parameter value changes. Call eq_update_from_params() at the start of
// each audio block; call eq_process_biquad per sample.
//
// params_init() must be called before eq_init().

#ifndef DAISY_CLAUDE_EQ_H
#define DAISY_CLAUDE_EQ_H

#ifdef __cplusplus
extern "C" {
#endif

// Biquad in Direct Form I.
// Difference equation (positive-feedback storage convention):
//   y[n] = b0*x[n] + b1*x[n-1] + b2*x[n-2] + a1*y[n-1] + a2*y[n-2]
// Note: a1/a2 are stored negated relative to the Audio EQ Cookbook sign
// convention (where they appear with a minus sign). See eq.c for derivation.
typedef struct {
  float b0, b1, b2;
  float a1, a2;
  float x1, x2, y1, y2;  // delay-line state
} Biquad;

typedef struct {
  Biquad hi_shelf;
  Biquad lp;
} EqChannel;

extern EqChannel eq_ch[2];        // [0]=left, [1]=right — live (audio ISR reads)
extern EqChannel eq_new_ch[2];    // staging buffer — background writes new coeffs here

// Must be called after params_init(). Computes initial coefficients.
void eq_init(void);

// Compute new coefficients from current parameter values. Call from background task
// (foreground loop in main.c, NOT from ISR). Writes to eq_new_ch[].
// Can use sinf/cosf/expf — not performance-critical.
void eq_recompute_from_params(void);

// Atomically swap the new coefficients into the live buffers. Call from ISR only,
// after params_dirty bit 1 (ready) is set.
void eq_apply_new_coefficients(void);

// Per-sample processing. Call from ISR during process_audio(). Uses live eq_ch[].
float eq_process_biquad(Biquad *bq, float x);

#ifdef __cplusplus
}  // extern "C"
#endif

#endif // DAISY_CLAUDE_EQ_H
