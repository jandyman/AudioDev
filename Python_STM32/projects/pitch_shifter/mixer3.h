#pragma once
#ifndef BARE_METAL
#include <vector>
#include <string>
using std::vector;
using std::string;
#endif

// mixer3 — three-input weighted mixer with master gate
//
// Computes out[n] = (in1[n]*gain1[n] + in2[n]*gain2[n] + in3[n]*gain3[n]) * gate[n].
// Gains are per-sample inputs so time-varying crossfades are handled correctly.
// gate is a 0..1 master multiplier (e.g. active_gain from attack_detector) that
// mutes output when no note is sounding. Stateless — no internal memory.
//
// Inputs  (7): in1, in2, in3, gain1, gain2, gain3, gate
// Outputs (1): out

class mixer3 {
public:
  void init(int sample_rate) { sample_rate_ = sample_rate; }

  int get_num_inputs()  const { return 7; }
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
