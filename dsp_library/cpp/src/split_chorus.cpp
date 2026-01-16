#include "split_chorus.h"
#include <stdexcept>
#include <cmath>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

SplitChorus::SplitChorus()
  : sample_rate_(0),
    num_inputs_(1),
    num_outputs_(1),
    crossover_freq_(300.0f),
    delay_center_ms_(25.0f),
    lfo_rate_hz_(2.0f),
    depth_(0.5f),
    wet_(0.5f),
    svf_low_state1_(0.0f),
    svf_low_state2_(0.0f),
    svf_high_state1_(0.0f),
    svf_high_state2_(0.0f),
    rng_(12345),
    dist_(-1.0f, 1.0f),
    lfo_phase_(0.0f),
    current_lfo_value_(0.0f),
    lfo_smoothing_coeff_(0.0f),
    smoothed_lfo_(0.0f),
    delay_write_pos_(0),
    svf_f_(0.0f),
    svf_q_(0.707f) {
  delay_buffer_.resize(MAX_DELAY_SAMPLES, 0.0f);
}

void SplitChorus::init(int sample_rate) {
  sample_rate_ = sample_rate;

  // Clear filter state
  svf_low_state1_ = 0.0f;
  svf_low_state2_ = 0.0f;
  svf_high_state1_ = 0.0f;
  svf_high_state2_ = 0.0f;

  // Clear delay buffer
  std::fill(delay_buffer_.begin(), delay_buffer_.end(), 0.0f);
  delay_write_pos_ = 0;

  // Initialize LFO smoothing (20ms time constant)
  float smoothing_time_ms = 20.0f;
  lfo_smoothing_coeff_ = 1.0f - std::exp(-1.0f / (sample_rate * smoothing_time_ms / 1000.0f));

  update_filter_coefficients();
}

void SplitChorus::update_filter_coefficients() {
  // State variable filter frequency coefficient
  // f = 2 * sin(pi * fc / fs)
  svf_f_ = 2.0f * std::sin(M_PI * crossover_freq_ / sample_rate_);

  // Clamp to stable range
  if (svf_f_ > 1.0f) svf_f_ = 1.0f;
}

void SplitChorus::update_lfo() {
  // Random LFO: sample-and-hold at LFO rate with smoothing
  if (lfo_rate_hz_ > 0.0f) {
    float samples_per_cycle = sample_rate_ / lfo_rate_hz_;
    lfo_phase_ += 1.0f;

    if (lfo_phase_ >= samples_per_cycle) {
      lfo_phase_ -= samples_per_cycle;
      // Generate new random target value
      current_lfo_value_ = dist_(rng_);
    }
  }

  // Smooth the random values to avoid zipper noise
  smoothed_lfo_ += lfo_smoothing_coeff_ * (current_lfo_value_ - smoothed_lfo_);
}

float SplitChorus::interpolated_read(float delay_samples) {
  // Linear interpolation for fractional delay
  float read_pos_float = delay_write_pos_ - delay_samples;
  while (read_pos_float < 0.0f) {
    read_pos_float += MAX_DELAY_SAMPLES;
  }

  int read_pos_int = static_cast<int>(read_pos_float);
  float frac = read_pos_float - read_pos_int;

  int pos1 = read_pos_int % MAX_DELAY_SAMPLES;
  int pos2 = (read_pos_int + 1) % MAX_DELAY_SAMPLES;

  return delay_buffer_[pos1] * (1.0f - frac) + delay_buffer_[pos2] * frac;
}

void SplitChorus::process(const vector<vector<float>>& inputs,
                              vector<vector<float>>& outputs) {
  const vector<float>& input = inputs[0];
  vector<float>& output = outputs[0];

  for (size_t i = 0; i < input.size(); i++) {
    float in_sample = input[i];

    // State variable filter: split into low and high bands
    // Low pass output
    svf_low_state1_ += svf_f_ * svf_low_state2_;
    float low_out = svf_low_state1_;

    // High pass output
    float high_in = in_sample - low_out - svf_q_ * svf_low_state2_;
    svf_low_state2_ += svf_f_ * high_in;
    float high_out = high_in;

    // Update LFO
    update_lfo();

    // Calculate modulated delay time for chorus effect
    // Delay = center ± (depth * LFO * range)
    float delay_range_ms = 10.0f;  // ±10ms around center
    float delay_ms = delay_center_ms_ + (depth_ * smoothed_lfo_ * delay_range_ms);

    // Clamp delay to valid range
    if (delay_ms < 5.0f) delay_ms = 5.0f;
    if (delay_ms > 45.0f) delay_ms = 45.0f;

    float delay_samples = (delay_ms / 1000.0f) * sample_rate_;

    // Write high band to delay buffer
    delay_buffer_[delay_write_pos_] = high_out;

    // Read delayed high band
    float delayed_high = interpolated_read(delay_samples);

    // Mix: low band passes through, high band uses wet/dry mix
    float dry_high = high_out;
    float wet_high = dry_high * (1.0f - wet_) + delayed_high * wet_;

    // Combine bands
    output[i] = low_out + wet_high;

    // Advance delay write position
    delay_write_pos_ = (delay_write_pos_ + 1) % MAX_DELAY_SAMPLES;
  }
}

void SplitChorus::set_param(const string& name, float value) {
  if (name == "crossover") {
    crossover_freq_ = value;
    if (sample_rate_ > 0) {
      update_filter_coefficients();
    }
  } else if (name == "delay") {
    delay_center_ms_ = value;
  } else if (name == "rate") {
    lfo_rate_hz_ = value;
  } else if (name == "depth") {
    depth_ = value;
  } else if (name == "wet") {
    wet_ = value;
  } else {
    throw std::runtime_error("Parameter '" + name + "' not found");
  }
}

float SplitChorus::get_param(const string& name) const {
  if (name == "crossover") {
    return crossover_freq_;
  } else if (name == "delay") {
    return delay_center_ms_;
  } else if (name == "rate") {
    return lfo_rate_hz_;
  } else if (name == "depth") {
    return depth_;
  } else if (name == "wet") {
    return wet_;
  } else {
    throw std::runtime_error("Parameter '" + name + "' not found");
  }
}

vector<string> SplitChorus::get_param_names() const {
  return {"crossover", "delay", "rate", "depth", "wet"};
}
