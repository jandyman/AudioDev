// eq_gen.cpp — Generalized 5-stage EQ implementation.
//
// Filter types are fixed by stage position; only the parameters change at runtime.
// eq_gen_recompute() runs filter_design() (trig, foreground-safe) then hands off
// the resulting CascadeCoeffs to FilterChannel::update() or update_with_reset()
// (brief IRQ-disable window for the struct copy).

#include "eq_gen.h"
#include "eq_design.h"
#include "params.h"

// Stage type is fixed at design time — firmware and Swift app both know this mapping.
static const FilterType kStageTypes[N_GEN_EQ_STAGES] = {
  FilterType::LP,   // stage 0
  FilterType::HP,   // stage 1
  FilterType::LS,   // stage 2
  FilterType::HS,   // stage 3
  FilterType::BP,   // stage 4
};

FilterChannel eq_gen_stages[2][N_GEN_EQ_STAGES];

void eq_gen_recompute(int ch, int stage, bool reset) {
  CascadeCoeffs cc{};  // n_sections=0 by default — pass-through when disabled

  float enabled = gen_eq_params[ch][stage][FIELD_ENABLED].value;
  if (enabled >= 0.5f) {
    FilterParams p;
    p.type    = kStageTypes[stage];
    p.fc_hz   = gen_eq_params[ch][stage][FIELD_FC_HZ].value;
    p.fs_hz   = 48000.f;
    p.order   = (int)gen_eq_params[ch][stage][FIELD_ORDER].value;
    p.gain_db = gen_eq_params[ch][stage][FIELD_GAIN_DB].value;
    p.q       = gen_eq_params[ch][stage][FIELD_Q].value;
    if (p.order < 1) p.order = 1;
    if (p.order > 4) p.order = 4;
    filter_design(p, cc);
  }

  if (reset)
    eq_gen_stages[ch][stage].update_with_reset(cc);
  else
    eq_gen_stages[ch][stage].update(cc);
}

void eq_gen_init(void) {
  for (int ch = 0; ch < 2; ++ch)
    for (int stage = 0; stage < N_GEN_EQ_STAGES; ++stage)
      eq_gen_recompute(ch, stage, true);
}
