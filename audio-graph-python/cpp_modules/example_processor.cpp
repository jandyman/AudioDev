#include "example_processor.h"
#include <stdexcept>

ExampleProcessor::ExampleProcessor()
  : sample_rate_(0), num_inputs_(1), num_outputs_(1) {
  // Initialize default parameters
  params_["gain"] = 1.0f;
}

void ExampleProcessor::init(int sample_rate) {
  sample_rate_ = sample_rate;
  // Perform any sample-rate-dependent initialization here
  // Allocate buffers, clear state, etc.
}

void ExampleProcessor::process(const vector<vector<float>>& inputs,
                               vector<vector<float>>& outputs) {
  // Simple gain processing
  float gain = params_["gain"];

  // Process each channel
  for (size_t ch = 0; ch < inputs.size(); ch++) {
    const vector<float>& input = inputs[ch];
    vector<float>& output = outputs[ch];

    // Apply gain to each sample
    for (size_t i = 0; i < input.size(); i++) {
      output[i] = input[i] * gain;
    }
  }
}

void ExampleProcessor::set_param(const string& name, float value) {
  auto it = params_.find(name);
  if (it != params_.end()) {
    params_[name] = value;
  } else {
    throw std::runtime_error("Parameter '" + name + "' not found");
  }
}

float ExampleProcessor::get_param(const string& name) const {
  auto it = params_.find(name);
  if (it != params_.end()) {
    return it->second;
  } else {
    throw std::runtime_error("Parameter '" + name + "' not found");
  }
}

vector<string> ExampleProcessor::get_param_names() const {
  vector<string> names;
  for (const auto& pair : params_) {
    names.push_back(pair.first);
  }
  return names;
}
