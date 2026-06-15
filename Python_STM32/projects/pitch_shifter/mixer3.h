#pragma once
#ifndef BARE_METAL
#include <vector>
#include <string>
using std::vector;
using std::string;
#endif

// mixer3 — stateless three-input weighted summer
// (out = in1*gain1 + in2*gain2 + in3*gain3). Doc: mixer3.md.

class mixer3 {
public:
  void init(int sample_rate) { sample_rate_ = sample_rate; }

  int get_num_inputs()  const { return 6; }
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
