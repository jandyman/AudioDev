#pragma once
#include <vector>
#include <cstdint>
#include "platform.h"
using std::vector;

struct BiquadChainState {
  vector<float> dlybuf;
  P_BiquadChainState c_state;
};

struct BiquadChainParams {
  int n_stages;
  vector<float> coefs;
};

struct BiquadChain {
  BiquadChainState state;
  BiquadChainParams params;
  void init();
  void proc(vector<vector<float>>& buffers);
};

struct BiquadChain64State {
  vector<double> dlybuf;
  arm_biquad_cascade_df2T_instance_f64 c_state;
};

struct BiquadChain64Params {
  int n_stages;
  vector<double> coefs;
};

struct BiquadChain64 {
  BiquadChain64State state;
  BiquadChain64Params params;
  void init();
  void proc(vector<vector<double>>& buffers);
};

struct XCoupledPolesState {
  float a1;
  float a2;
  float s1;
  float s2;
};
