#pragma once
#include <vector>
#include <cstdint>
using std::vector;

struct DelayBufState {
  vector<float> data;
  int wr_idx;
};

struct DelayBuf {
  DelayBufState state;
  void push(vector<float>& samples);
  void get_values(int delay, vector<float>& output);
};
