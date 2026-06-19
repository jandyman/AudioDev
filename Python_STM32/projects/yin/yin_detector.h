#pragma once
#include <cstdint>
#ifndef BARE_METAL
#include <vector>
#include <string>
using std::vector;
using std::string;
#endif

// yin_detector — decimated brute-force YIN pitch estimator (de Cheveigné &
// Kawahara 2002). An anti-alias FIR decimator (÷DECIM) feeds a power-of-two
// decimated ring buffer; YIN's difference function + cumulative-mean-normalized
// difference + absolute-threshold pick + parabolic interpolation run at control
// rate over that ring. Robust to weak-fundamental / 2nd-harmonic-dominant notes
// where a fundamental-amplitude tracker octave-errors. Design + plan:
// yin_detector.md.

class yin_detector {
public:
  // ---- fixed sizes (static allocation; no malloc in the render path) ----
  static const int DECIM     = 16;    // decimation factor (power of two)
  static const int FIR_TAPS  = 129;   // anti-alias FIR length (odd, linear phase)
  static const int RING_SIZE = 512;   // decimated ring length (power of two)
  static const int RING_MASK = RING_SIZE - 1;
  static const int MAX_TAU   = 200;   // largest lag the difference function spans

  // Output channel layout (must match the @block (outputs ...) order in the .cpp)
  enum {
    OUT_F0 = 0,        // estimated fundamental (Hz), held between updates
    OUT_P,             // period at FULL rate (fractional samples), held
    OUT_APERIODICITY,  // d' at the chosen dip (low = confident/periodic), held
    OUT_DECIMATED,     // zero-order-hold of the decimated signal (probe)
    OUT_DPRIME,        // head [0..tau_max] holds the latest d'(τ) curve (probe)
    NUM_OUTPUTS
  };

  yin_detector();

  void init(int sample_rate);

  int get_num_inputs()  const { return 1; }
  int get_num_outputs() const { return NUM_OUTPUTS; }
  int get_sample_rate() const { return (int)sample_rate_; }

  void process(const float* const* inputs, float* const* outputs, int n);

  void set_param(const char* name, float value);
  float get_param(const char* name) const;
#ifndef BARE_METAL
  vector<string> get_param_names() const;
#endif

private:
  // ---- helpers ----
  void design_decimator();    // fill fir_[] (windowed sinc), recompute on sr change
  void update_lag_range();    // tau_min_/tau_max_/window_ from sr + fmin/fmax
  void run_yin();             // one control-rate estimate over the decimated ring

  // ---- decimator state ----
  float fir_[FIR_TAPS];
  float hist_[2 * FIR_TAPS];  // double-length sliding window (contiguous read)
  int   hist_pos_;
  int   decim_phase_;
  float last_decimated_;

  // ---- decimated ring ----
  float    ring_[RING_SIZE];
  uint32_t ring_head_;        // index of NEXT write (monotonic; mask on read)
  uint32_t ring_count_;       // total decimated samples seen (saturates logically)

  // ---- YIN scratch / results ----
  float diff_[MAX_TAU + 1];   // d(τ)
  float dprime_[MAX_TAU + 1]; // d'(τ) — cumulative-mean-normalized difference
  int   tau_min_, tau_max_, window_;
  int   hop_counter_;

  float P_;            // last period, full-rate fractional samples
  float f0_;           // last f0, Hz
  float aperiodicity_; // last d' at the chosen dip

  // ---- parameters ----
  float sample_rate_;
  float fmin_, fmax_;  // search range, Hz
  float threshold_;    // absolute-threshold for the first qualifying dip
  int   hop_decim_;    // control-rate period, in decimated samples
};
