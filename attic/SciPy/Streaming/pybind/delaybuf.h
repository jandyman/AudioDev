#pragma once
#include "pybind_support.h"

struct DelayBufState {
  vector<float> data;
  vector<float> output;
  int wr_idx;
};

struct DelayBuf {
  DelayBufState state;
  void push(vector<float> samples);
  void get_values(int delay, int cnt);
};
