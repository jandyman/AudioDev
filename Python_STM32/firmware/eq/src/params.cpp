// params.cpp — EQ parameter table initialisation.

#include "params.h"

GenEqParam gen_eq_params[2][N_GEN_EQ_STAGES][N_GEN_EQ_FIELDS];

// Default values per stage [enabled, fc_hz, order, gain_db, q].
// Matches DaisyControl defaultStages() so firmware and app agree at startup.
static const float kDefaults[N_GEN_EQ_STAGES][N_GEN_EQ_FIELDS] = {
  {1.f, 20000.f, 2.f, 0.f, 0.7071f},  // LP
  {1.f,    20.f, 1.f, 0.f, 0.7071f},  // HP
  {1.f,   200.f, 2.f, 0.f, 0.7071f},  // LS
  {1.f,  8000.f, 2.f, 0.f, 0.7071f},  // HS
  {1.f,  1000.f, 2.f, 0.f, 0.7071f},  // BP
};

// Min/max per field — same for every stage.
static const float kMin[N_GEN_EQ_FIELDS] = {0.f,  20.f, 1.f, -24.f, 0.1f};
static const float kMax[N_GEN_EQ_FIELDS] = {1.f, 20000.f, 4.f, 24.f, 10.f};

void params_init(void) {
  for (int ch = 0; ch < 2; ++ch) {
    for (int s = 0; s < N_GEN_EQ_STAGES; ++s) {
      for (int f = 0; f < N_GEN_EQ_FIELDS; ++f) {
        gen_eq_params[ch][s][f].value       = kDefaults[s][f];
        gen_eq_params[ch][s][f].min         = kMin[f];
        gen_eq_params[ch][s][f].max         = kMax[f];
        gen_eq_params[ch][s][f].default_val = kDefaults[s][f];
      }
    }
  }
}
