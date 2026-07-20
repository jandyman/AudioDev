#include "filters.h"
#include "filtering_functions.h"

void BiquadChain::init() {
  auto c_ptr = &params.coefs[0];
  auto d_ptr = &state.dlybuf[0];
  arm_biquad_cascade_df1_init_f32(&state.c_state, params.n_stages, c_ptr, d_ptr);
}

void BiquadChain::proc(vector<vector<float>>& bufs) {
  auto& S = state.c_state;
  arm_biquad_cascade_df1_f32(&S, &bufs[0][0],  &bufs[1][0], bufs[0].size());
}

void BiquadChain64::init() {
  auto c_ptr = &params.coefs[0];
  auto d_ptr = &state.dlybuf[0];
  arm_biquad_cascade_df2T_init_f64(&state.c_state, params.n_stages, c_ptr, d_ptr);
}

void BiquadChain64::proc(vector<vector<double>>& bufs) {
  auto& S = state.c_state;
  arm_biquad_cascade_df2T_f64(&S, &bufs[0][0],  &bufs[1][0], bufs[0].size());
}

// void BiquadChain::proc(vector<vector<float>>& bufs) {
//   // arm_biquad_cascade_df1_init_f32(&fStruct, 2, nullptr, nullptr);	
//   auto& s = state;
//   auto& p = params;
//   auto& in = bufs[0];
//   auto& out = bufs[1];
//   auto n_samps = bufs[0].size();
//   for (int si=0; si<n_samps; si++) {
//     float samp = in[si];
//     for (int i=0; i<p.n_stages; i++) {
//       float* c = &p.coefs[i*5];
//       float* d = &s.dlybuf[i*4];
//       float sum = samp*c[0] + d[0]*c[1] + d[1]*c[2] - d[2]*c[3] - d[3]*c[4];
//       d[3]=d[2]; d[2]=sum; d[1]=d[0]; d[0]=samp;
//       samp = sum;
//     }
//     out[si] = samp;
//   }
// }