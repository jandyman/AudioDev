// eq.h — stereo EQ: 2-pole high-shelf + 1-pole low-pass per channel
//
// Coefficients are recomputed in eq_update_from_params() only when a
// parameter value changes. Call eq_update_from_params() at the start of
// each audio block; call eq_process_* per sample.
//
// params_init() must be called before eq_init().

#ifndef DAISY_CLAUDE_EQ_H
#define DAISY_CLAUDE_EQ_H

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

// First-order IIR low-pass:
//   y[n] = b0*x[n] + a1*y[n-1]
//   b0 = 1 - exp(-2π*fc/fs),  a1 = exp(-2π*fc/fs)
typedef struct {
    float b0, a1;
    float y1;               // delay-line state
} OnePoleLP;

typedef struct {
    Biquad    hi_shelf;
    OnePoleLP lp;
} EqChannel;

extern EqChannel eq_ch[2];  // [0]=left, [1]=right

// Must be called after params_init(). Computes initial coefficients.
void eq_init(void);

// Check whether any parameter has changed; recompute coefficients if so.
// Safe to call from ISR — sinf/cosf/expf are reentrant.
void eq_update_from_params(void);

// Per-sample processing. Call after eq_update_from_params().
float eq_process_biquad(Biquad *bq, float x);
float eq_process_lp(OnePoleLP *lp, float x);

#endif // DAISY_CLAUDE_EQ_H
