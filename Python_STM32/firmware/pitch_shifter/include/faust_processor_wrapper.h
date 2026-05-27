#pragma once

// Bare-metal version of FaustProcessorWrapper — uses MapUI from our
// bare-metal faust_minimal.h, no std::string / std::vector.
// Overrides python/bindings/faust_processor_wrapper.h via include path order.

#include "faust_minimal.h"

class FaustProcessorWrapper {
  dsp* faust_dsp_;
  MapUI faust_ui_;
  int sample_rate_;
public:
  FaustProcessorWrapper(dsp* d) : faust_dsp_(d), sample_rate_(0) {}
  ~FaustProcessorWrapper() { delete faust_dsp_; }

  void init(int sr) {
    sample_rate_ = sr;
    faust_dsp_->init(sr);
    faust_dsp_->buildUserInterface(&faust_ui_);
  }

  void process(const float* const* inputs, float* const* outputs, int n) {
    faust_dsp_->compute(n,
      const_cast<FAUSTFLOAT**>(inputs),
      const_cast<FAUSTFLOAT**>(outputs));
  }

  int get_num_inputs()  const { return faust_dsp_->getNumInputs(); }
  int get_num_outputs() const { return faust_dsp_->getNumOutputs(); }
  int get_sample_rate() const { return sample_rate_; }

  void  set_param(const char* name, float value) { faust_ui_.setParamValue(name, value); }
  float get_param(const char* name) const { return faust_ui_.getParamValue(name); }
};
