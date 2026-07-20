#pragma once
#include <vector>
#include <cstdint>
#include "platform.h"
using std::vector;

struct Abs {
  void proc(vector<vector<float>>& buffers);
};

struct Add {
  void proc(vector<vector<float>>& buffers);
};

struct Comparator {
  void proc(vector<vector<float>>& bufs);
};

struct EdgeDetectorState {
  float prev_samp;
};

struct EdgeDetectorParams {
  float thresh;
  int mode;
};

struct EdgeDetector {
  EdgeDetectorState state;
  EdgeDetectorParams params;
  void proc(vector<vector<float>>& bufs);
};

struct Exp {
  void proc(vector<vector<float>>& buffers);
};

struct Log {
  void proc(vector<vector<float>>& buffers);
};

struct Mult {
  void proc(vector<vector<float>>& buffers);
};

struct Sqrt {
  void proc(vector<vector<float>>& buffers);
};

struct Square {
  void proc(vector<vector<float>>& buffers);
};

struct Sub {
  void proc(vector<vector<float>>& buffers);
};
