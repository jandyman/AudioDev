#pragma once
#include <vector>
#include <string>
#include <cmath>
#include <random>

using std::vector;
using std::string;

// Split Chorus
// Splits signal into low and high bands
// Lows: pass through unchanged
// Highs: chorus effect with random modulation
class SplitChorus {
private:
  int sample_rate_;
  const int num_inputs_;
  const int num_outputs_;

  // Parameters
  float crossover_freq_;   // 20-480 Hz
  float delay_center_ms_;  // 5-45 ms
  float lfo_rate_hz_;      // 0-20 Hz
  float depth_;            // 0-1
  float wet_;              // 0-1

  // State variable filter state (2-pole, produces low and high outputs)
  float svf_low_state1_;
  float svf_low_state2_;
  float svf_high_state1_;
  float svf_high_state2_;

  // Random LFO state
  std::mt19937 rng_;
  std::uniform_real_distribution<float> dist_;
  float lfo_phase_;
  float current_lfo_value_;
  float lfo_smoothing_coeff_;
  float smoothed_lfo_;

  // Delay line state (simple ring buffer)
  static const int MAX_DELAY_SAMPLES = 48000;  // 1 second at 48kHz
  vector<float> delay_buffer_;
  int delay_write_pos_;

  // Filter coefficients
  float svf_f_;  // frequency coefficient
  float svf_q_;  // resonance coefficient

  void update_filter_coefficients();
  void update_lfo();
  float interpolated_read(float delay_samples);

public:
  SplitChorus();

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
