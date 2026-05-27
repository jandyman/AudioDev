#pragma once

// Generic wrapper that adapts a Faust-generated dsp class to the
// CppProcessor-compatible interface (init, process, set_param, get_param).
//
// Usage: instantiate with a Faust dsp* pointer:
//   FaustProcessorWrapper wrapper(new FaustAttackDetector());
//   wrapper.init(44100);
//   wrapper.process(inputs, outputs);  // stateful, persists across calls

#include "faust_minimal.h"
#include <vector>
#include <string>
#include <stdexcept>

using std::vector;
using std::string;

class FaustProcessorWrapper {
private:
  dsp* faust_dsp_;
  MapUI faust_ui_;
  int sample_rate_;

public:
  FaustProcessorWrapper(dsp* d) : faust_dsp_(d), sample_rate_(0) {}

  ~FaustProcessorWrapper() {
    delete faust_dsp_;
  }

  void init(int sample_rate) {
    sample_rate_ = sample_rate;
    faust_dsp_->init(sample_rate);
    faust_dsp_->buildUserInterface(&faust_ui_);
  }

  // Bridge: forward straight to Faust's compute(). FAUSTFLOAT == float now;
  // Faust's signature wants non-const inner pointers, so cast through.
  void process(const float* const* inputs, float* const* outputs, int n) {
    if (!faust_dsp_) return;
    faust_dsp_->compute(n,
                        const_cast<FAUSTFLOAT**>(inputs),
                        const_cast<FAUSTFLOAT**>(outputs));
  }

  int get_num_inputs() const { return faust_dsp_->getNumInputs(); }
  int get_num_outputs() const { return faust_dsp_->getNumOutputs(); }
  int get_sample_rate() const { return sample_rate_; }

  void set_param(const char* name, float value) {
    faust_ui_.setParamValue(name, value);
  }

  float get_param(const char* name) const {
    return faust_ui_.getParamValue(name);
  }

  vector<string> get_param_names() const {
    return faust_ui_.getParamNames();
  }
};
