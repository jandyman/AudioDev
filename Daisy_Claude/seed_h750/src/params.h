// params.h — Flat EQ parameter table.
//
// 50 parameters: 2 channels × 5 stages × 5 fields.
// Wire param_id: id = channel*25 + stage*5 + field.
//   channel: 0=L, 1=R
//   stage:   0=LP, 1=HP, 2=LS, 3=HS, 4=BP
//   field:   see FIELD_* constants below
//
// Defaults match DaisyControl defaultStages() so both sides agree at startup
// without a full-push sync on connect.

#ifndef DAISY_CLAUDE_PARAMS_H
#define DAISY_CLAUDE_PARAMS_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define N_GEN_EQ_STAGES  5
#define N_GEN_EQ_FIELDS  5

// Field indices within a stage (used by rtt_cmd.cpp and eq_gen.cpp)
#define FIELD_ENABLED  0  // 0.0 = bypass, 1.0 = active
#define FIELD_FC_HZ    1  // cutoff / centre frequency in Hz
#define FIELD_ORDER    2  // filter order 1–4 (BP ignores this)
#define FIELD_GAIN_DB  3  // shelf / peak gain in dB (LP/HP ignore this)
#define FIELD_Q        4  // Q factor (BP only; LP/HP/LS/HS ignore this)

typedef struct {
  volatile float value;
  float          min;
  float          max;
  float          default_val;
} GenEqParam;

// Flat param table [channel][stage][field] — 2×5×5 = 50 params total.
extern GenEqParam gen_eq_params[2][N_GEN_EQ_STAGES][N_GEN_EQ_FIELDS];

// Fill gen_eq_params with defaults and ranges. Call before eq_gen_init().
void params_init(void);

#ifdef __cplusplus
}
#endif

#endif // DAISY_CLAUDE_PARAMS_H
