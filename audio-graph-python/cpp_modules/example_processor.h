#pragma once
#include <vector>
#include <string>
#include <map>

using std::vector;
using std::string;
using std::map;

// Example processor: Simple gain with parameter support
// Demonstrates the standard audio processor interface
class ExampleProcessor {
private:
  int sample_rate_;
  int num_inputs_;
  int num_outputs_;
  map<string, float> params_;

public:
  ExampleProcessor();

  // Lifecycle
  void init(int sample_rate);

  // Processing
  void process(const vector<vector<float>>& inputs, vector<vector<float>>& outputs);

  // Introspection
  int get_num_inputs() const { return num_inputs_; }
  int get_num_outputs() const { return num_outputs_; }
  int get_sample_rate() const { return sample_rate_; }

  // Parameters
  void set_param(const string& name, float value);
  float get_param(const string& name) const;
  vector<string> get_param_names() const;
};
