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

  // Bridge: vector<vector<double>> -> FAUSTFLOAT** -> compute -> vector<vector<double>>
  void process(const vector<vector<double>>& inputs, vector<vector<double>>& outputs) {
    if (!faust_dsp_) return;

    int num_samples = 0;
    if (!inputs.empty()) {
      num_samples = (int)inputs[0].size();
    } else if (!outputs.empty()) {
      num_samples = (int)outputs[0].size();
    }
    if (num_samples == 0) return;

    // Build pointer arrays for Faust compute()
    // Faust compute() takes non-const input pointers, but doesn't modify them
    vector<FAUSTFLOAT*> in_ptrs(inputs.size());
    for (size_t i = 0; i < inputs.size(); i++) {
      in_ptrs[i] = const_cast<FAUSTFLOAT*>(inputs[i].data());
    }

    vector<FAUSTFLOAT*> out_ptrs(outputs.size());
    for (size_t i = 0; i < outputs.size(); i++) {
      out_ptrs[i] = outputs[i].data();
    }

    faust_dsp_->compute(num_samples, in_ptrs.data(), out_ptrs.data());
  }

  int get_num_inputs() const { return faust_dsp_->getNumInputs(); }
  int get_num_outputs() const { return faust_dsp_->getNumOutputs(); }
  int get_sample_rate() const { return sample_rate_; }

  void set_param(const string& name, double value) {
    faust_ui_.setParamValue(name.c_str(), value);
  }

  double get_param(const string& name) const {
    return faust_ui_.getParamValue(name.c_str());
  }

  vector<string> get_param_names() const {
    return faust_ui_.getParamNames();
  }
};
