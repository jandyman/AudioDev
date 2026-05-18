// eq_gen.h — Generalized 5-stage EQ per channel: LP → HP → LS → HS → BP.
//
// Each stage is a FilterChannel (dsp_cpp/include/param_update.h): a BiquadCascade
// whose coefficients can be updated atomically from the foreground using a brief
// IRQ-disable window. The audio ISR calls cascade.process() directly — no flag
// checks, no branches in the hot path.
//
// Enabled stages run filter_design() to populate the cascade; disabled stages
// get CascadeCoeffs.n_sections=0, making cascade.process() a pass-through (the
// for-loop body never executes).
//
// Threading:
//   eq_gen_process()   — audio ISR, always_inline into the hot path
//   eq_gen_recompute() — foreground (RTT command handler), trig is fine here;
//                        the IRQ-disable window is just the struct copy in
//                        FilterChannel::update() / update_with_reset()

#pragma once
#include <stdint.h>
#include "param_update.h"  // FilterChannel, BiquadCascade
#include "params.h"        // N_GEN_EQ_STAGES

// Live filter state — ISR reads cascade.process() directly.
// rtt_cmd.cpp writes via eq_gen_recompute() (IRQ-safe).
extern FilterChannel eq_gen_stages[2][N_GEN_EQ_STAGES];

// Seed all stages from gen_eq_params[]. Call after params_init(), before audio starts.
void eq_gen_init(void);

// Recompute one stage's FilterChannel from its current params.
// Pass reset=true when order or enabled changes to zero stale delay lines.
// Pass reset=false for fc/gain/q changes to avoid clicks.
void eq_gen_recompute(int ch, int stage, bool reset);

// Process one sample through all 5 stages for one channel.
// Inlined into the ISR — each stage's BiquadCascade::process() is also inlined.
__attribute__((always_inline))
inline float eq_gen_process(int ch, float x) {
  for (int i = 0; i < N_GEN_EQ_STAGES; ++i)
    x = eq_gen_stages[ch][i].cascade.process(x);
  return x;
}
