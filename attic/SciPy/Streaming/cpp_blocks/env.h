#pragma once
#include <vector>
#include <cstdint>
#include "platform.h"
using std::vector;

struct AttRelState {
  float lastout;
};

struct AttRelParams {
  float fs;
  float attTime;
  float relTime;
  float attCoef;
  float relCoef;
};

struct AttRel {
  AttRelState state;
  AttRelParams params;
  void init();
  void proc(vector<vector<float>>& buffers);
};

struct FollowPeaksState {
  float lastpeak;
  float lastout;
  float sampSincePeak;
};

struct FollowPeaksParams {
  float attCoef;
  float div;
};

struct FollowPeaks {
  FollowPeaksState state;
  FollowPeaksParams params;
  void init();
  void proc(vector<vector<float>>& buffers);
};
