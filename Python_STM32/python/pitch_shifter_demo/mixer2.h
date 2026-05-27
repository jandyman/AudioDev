#pragma once
#ifndef BARE_METAL
#include <vector>
#include <string>
using std::vector;
using std::string;
#endif

// mixer2 — two-input crossfade mixer
//
// Computes out[n] = in1[n]*gain1[n] + in2[n]*gain2[n] per sample.
// Gains are per-sample inputs so time-varying crossfades are handled correctly.
// Stateless — no internal memory between chunks.
//
// Inputs  (4): in1, in2, gain1, gain2
// Outputs (1): out

class mixer2 {
public:
  void init(int sample_rate) { sample_rate_ = sample_rate; }

  int get_num_inputs()  const { return 4; }
  int get_num_outputs() const { return 1; }
  int get_sample_rate() const { return sample_rate_; }

  void process(const float* const* inputs, float* const* outputs, int n);

  void  set_param(const char* name, float value) {}
  float get_param(const char* name) const { return 0.0f; }
#ifndef BARE_METAL
  vector<string> get_param_names() const { return {}; }
#endif

private:
  int sample_rate_ = 48000;
};
