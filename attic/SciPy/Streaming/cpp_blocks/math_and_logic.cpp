#include "platform.h"
#include "math_and_logic.h"
#include <algorithm>
#include <functional>
using namespace std;

void Square::proc(vector<vector<float>>& bufs) {
  auto& x = bufs[0];
  auto& out = bufs[1];
  arm_mult_f32(&x[0], &x[0], &out[0], (uint32_t)x.size());
}

void Sqrt::proc(vector<vector<float>>& bufs) {
  auto& in = bufs[0];
  auto& out = bufs[1];
  for (int i = 0; i < in.size(); i++) {
    auto val = max(in[i], (float)0);
    arm_sqrt_f32(val, &out[i]);
  }
}

void Log::proc(vector<vector<float>>& bufs) {
  auto& x = bufs[0];
  auto& out = bufs[1];
  arm_vlog_f32(&x[0], &out[0], (uint32_t)x.size());
}

void Exp::proc(vector<vector<float>>& bufs) {
  auto& x = bufs[0];
  auto& out = bufs[1];
  arm_vexp_f32(&x[0], &out[0], (uint32_t)x.size());
}

void Abs::proc(vector<vector<float>>& bufs) {
  auto& x = bufs[0];
  auto& out = bufs[1];
  arm_abs_f32(&x[0], &out[0], (uint32_t)x.size());
}

void Add::proc(vector<vector<float>>& bufs) {
  auto& x = bufs[0];
  auto& y = bufs[1];
  auto& out = bufs[2];
  arm_add_f32(&x[0], &y[0], &out[0], (uint32_t)x.size());
}

void Sub::proc(vector<vector<float>>& bufs) {
  auto& x = bufs[0];
  auto& y = bufs[1];
  auto& out = bufs[2];
  arm_sub_f32(&x[0], &y[0], &out[0], (uint32_t)x.size());
}

void Mult::proc(vector<vector<float>>& bufs) {
  auto& x = bufs[0];
  auto& y = bufs[1];
  auto& out = bufs[2];
  arm_mult_f32(&x[0], &y[0], &out[0], (uint32_t)x.size());
}

void Comparator::proc(vector<vector<float>>& bufs) {
  for (int i=0; i<bufs[0].size(); i++) {
    bufs[2][i] = (int)(bufs[0][i] > bufs[1][i]);
  }
}

void EdgeDetector::proc(vector<vector<float>>& bufs) {
  auto& p = params;
  auto& s = state;
  std::function<bool(float)> f;
  switch (p.mode) {
    case 1:   // EdgeDetector.Mode.Rising
      f = [p,s](float x) { return x > p.thresh && s.prev_samp <= p.thresh; };
    case -1:  // EdgeDetector.Mode.Falling:
      f = [p,s](float x) { return x < p.thresh && s.prev_samp >= p.thresh; };
    case 0:   // EdgeDetector.Mode.Either:
    f = [p,s](float x) { return x > p.thresh != s.prev_samp > p.thresh; };
  }
  for (int i=0; i<bufs[0].size(); i++) {
    auto cond = f(bufs[0][i]);
    bufs[1][i] = (cond) ? bufs[0][i] - s.prev_samp : 0;
    s.prev_samp = bufs[0][i];
  }
}
