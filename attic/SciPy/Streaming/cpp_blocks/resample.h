#pragma once
#include <vector>
#include <cstdint>
#include "platform.h"
#include "delaybuf.h"
using std::vector;

struct JosFractDelayParams {
  vector<float> buffer;
  vector<vector<float>> h_coef_set;
  int oversamp_bits;
  bool allow_overflow;
};

struct JosFractDelay {
  JosFractDelayParams params;
  float fixed_delay(DelayBuf& delaybuf, float delay);
};

struct ResamplerState {
  JosFractDelay frac_dly;
  DelayBuf dly_buf;
};

struct Resampler {
  ResamplerState state;
  void proc(vector<vector<float>>& bufs);
};
