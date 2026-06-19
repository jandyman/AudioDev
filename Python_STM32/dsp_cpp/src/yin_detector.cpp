/* @block
(define-block yin_detector
 (inputs in)
 (outputs f0 P aperiodicity decimated dprime)
 (params (fmin :default 40) (fmax :default 330) (threshold :default 0.12) (update_hop :default 256)))
*/

#include "yin_detector.h"
#include <cmath>
#include <cstring>
#include <algorithm>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// Out-of-class definitions for ODR-use
const int yin_detector::DECIM;
const int yin_detector::FIR_TAPS;
const int yin_detector::RING_SIZE;
const int yin_detector::RING_MASK;
const int yin_detector::MAX_TAU;

// ============================================================
// Constructor / init
// ============================================================

yin_detector::yin_detector() {
  memset(this, 0, sizeof(*this));
  sample_rate_ = 48000.0f;
  fmin_        = 40.0f;
  fmax_        = 330.0f;
  threshold_   = 0.12f;
  hop_decim_   = 256 / DECIM;   // from update_hop = 256 input samples
}

void yin_detector::init(int sample_rate) {
  sample_rate_ = (float)sample_rate;

  // Decimator + ring state
  memset(hist_, 0, sizeof(hist_));
  hist_pos_       = 0;
  decim_phase_    = 0;
  last_decimated_ = 0.0f;

  memset(ring_, 0, sizeof(ring_));
  ring_head_  = 0;
  ring_count_ = 0;

  memset(diff_, 0, sizeof(diff_));
  memset(dprime_, 0, sizeof(dprime_));
  hop_counter_ = 0;

  // Until the first estimate, report fully aperiodic (no confidence) rather than
  // a false 0 — otherwise confidence = 1 - aperiodicity reads as max at startup.
  P_ = f0_ = 0.0f;
  aperiodicity_ = 1.0f;

  design_decimator();
  update_lag_range();
}

// Windowed-sinc anti-alias low-pass for the ÷DECIM decimator. Cutoff sits just
// below the decimated Nyquist (0.5/DECIM of the input rate); a Blackman window
// gives ~-58 dB stopband — verified against the measured response in the demo.
void yin_detector::design_decimator() {
  const int   M  = FIR_TAPS - 1;
  const float fc = 0.45f / (float)DECIM;   // normalized to input rate (cycles/sample)
  float sum = 0.0f;
  for (int k = 0; k <= M; k++) {
    float m = (float)k - 0.5f * (float)M;
    float sinc = (fabsf(m) < 1e-6f) ? 2.0f * fc
                                    : sinf(2.0f * (float)M_PI * fc * m) / ((float)M_PI * m);
    // Blackman window
    float w = 0.42f - 0.5f * cosf(2.0f * (float)M_PI * k / M)
                    + 0.08f * cosf(4.0f * (float)M_PI * k / M);
    fir_[k] = sinc * w;
    sum += fir_[k];
  }
  // Normalize to unity DC gain
  if (sum > 1e-12f) for (int k = 0; k <= M; k++) fir_[k] /= sum;
}

// Lag range + integration window from the search band at the decimated rate.
// window_ = tau_max_ → the analysis frame spans ~2 cycles of the lowest note.
void yin_detector::update_lag_range() {
  float decim_rate = sample_rate_ / (float)DECIM;
  tau_max_ = (int)ceilf(decim_rate / fmin_);
  tau_min_ = (int)floorf(decim_rate / fmax_);
  if (tau_min_ < 2) tau_min_ = 2;
  if (tau_max_ > MAX_TAU) tau_max_ = MAX_TAU;
  if (tau_max_ <= tau_min_) tau_max_ = tau_min_ + 1;
  window_ = tau_max_;
  // Frame = window_ + tau_max_ decimated samples; must fit the ring.
  if (window_ + tau_max_ > RING_SIZE) window_ = RING_SIZE - tau_max_;
}

// ============================================================
// YIN core — one control-rate estimate over the decimated ring
// ============================================================

void yin_detector::run_yin() {
  const int W = window_, tmax = tau_max_, tmin = tau_min_;

  // Oldest sample of the analysis frame: the frame is the most recent
  // (W + tmax) decimated samples. x(i) is oldest→newest within the frame.
  uint32_t base = ring_head_ - (uint32_t)(W + tmax);

  // 1) Difference function d(τ) = Σ_j (x[j] − x[j+τ])²
  for (int tau = tmin; tau <= tmax; tau++) {
    float acc = 0.0f;
    for (int j = 0; j < W; j++) {
      float a = ring_[(base + j) & RING_MASK];
      float b = ring_[(base + j + tau) & RING_MASK];
      float dlt = a - b;
      acc += dlt * dlt;
    }
    diff_[tau] = acc;
  }

  // 2) Cumulative-mean-normalized difference d'(τ)
  dprime_[0] = 1.0f;
  for (int tau = 1; tau < tmin; tau++) dprime_[tau] = 1.0f;
  float cum = 0.0f;
  for (int tau = tmin; tau <= tmax; tau++) {
    cum += diff_[tau];
    dprime_[tau] = (cum > 0.0f) ? diff_[tau] * (float)tau / cum : 1.0f;
  }

  // 3) Absolute threshold: first τ whose dip falls below threshold_, walked to
  //    its local minimum (prefers the true fundamental over the half-period 2H
  //    dip). Fall back to the global min of d' if nothing crosses.
  int tau_star = -1;
  for (int tau = tmin; tau < tmax; tau++) {
    if (dprime_[tau] < threshold_) {
      while (tau + 1 <= tmax && dprime_[tau + 1] < dprime_[tau]) tau++;
      tau_star = tau;
      break;
    }
  }
  if (tau_star < 0) {
    int best = tmin; float bv = dprime_[tmin];
    for (int tau = tmin + 1; tau <= tmax; tau++)
      if (dprime_[tau] < bv) { bv = dprime_[tau]; best = tau; }
    tau_star = best;
  }

  // 4) Parabolic interpolation around the dip (on d') → sub-sample period
  float period = (float)tau_star;
  if (tau_star > tmin && tau_star < tmax) {
    float ym = dprime_[tau_star - 1], y0 = dprime_[tau_star], yp = dprime_[tau_star + 1];
    float denom = ym - 2.0f * y0 + yp;
    if (fabsf(denom) > 1e-12f) period += 0.5f * (ym - yp) / denom;
  }

  // 5) Outputs: period at FULL rate; f0; aperiodicity = d' at the dip
  P_            = period * (float)DECIM;
  f0_           = (P_ > 0.0f) ? sample_rate_ / P_ : 0.0f;
  aperiodicity_ = dprime_[tau_star];
}

// ============================================================
// process()
// ============================================================

void yin_detector::process(const float* const* inputs, float* const* outputs, int num_samples) {
  const int frame_ready = window_ + tau_max_;

  for (int n = 0; n < num_samples; n++) {
    float x = inputs[0][n];

    // Push into the decimator's double-length sliding window
    hist_pos_ = (hist_pos_ + 1) % FIR_TAPS;
    hist_[hist_pos_]            = x;
    hist_[hist_pos_ + FIR_TAPS] = x;

    // Every DECIM-th input sample, emit one anti-aliased decimated sample.
    if (++decim_phase_ >= DECIM) {
      decim_phase_ = 0;
      const float* w = &hist_[hist_pos_ + 1];   // oldest→newest, contiguous
      float acc = 0.0f;
      for (int k = 0; k < FIR_TAPS; k++) acc += fir_[k] * w[k];
      last_decimated_ = acc;

      ring_[ring_head_ & RING_MASK] = acc;
      ring_head_++;
      ring_count_++;

      // Control-rate YIN once the ring holds a full analysis frame.
      if (++hop_counter_ >= hop_decim_ && (int)ring_count_ >= frame_ready) {
        hop_counter_ = 0;
        run_yin();
      }
    }

    outputs[OUT_F0][n]           = f0_;
    outputs[OUT_P][n]            = P_;
    outputs[OUT_APERIODICITY][n] = aperiodicity_;
    outputs[OUT_DECIMATED][n]    = last_decimated_;   // zero-order hold
    outputs[OUT_DPRIME][n]       = 0.0f;
  }

  // Probe: stash the latest d'(τ) curve in the head of the dprime buffer (its
  // per-sample time series is not meaningful — the curve is). Read it in Python
  // with get_buffer('yd.dprime', tau_max+1) after a process_chunk.
  int curve_len = std::min(tau_max_ + 1, num_samples);
  for (int tau = 0; tau < curve_len; tau++) outputs[OUT_DPRIME][tau] = dprime_[tau];
}

// ============================================================
// Parameters
// ============================================================

void yin_detector::set_param(const char* name, float value) {
  if      (!strcmp(name, "fmin"))      { fmin_ = value; update_lag_range(); }
  else if (!strcmp(name, "fmax"))      { fmax_ = value; update_lag_range(); }
  else if (!strcmp(name, "threshold")) { threshold_ = value; }
  else if (!strcmp(name, "update_hop")) {
    hop_decim_ = (int)(value / (float)DECIM);
    if (hop_decim_ < 1) hop_decim_ = 1;
  }
}

float yin_detector::get_param(const char* name) const {
  if (!strcmp(name, "fmin"))       return fmin_;
  if (!strcmp(name, "fmax"))       return fmax_;
  if (!strcmp(name, "threshold"))  return threshold_;
  if (!strcmp(name, "update_hop")) return (float)(hop_decim_ * DECIM);
  return 0.0f;
}

#ifndef BARE_METAL
vector<string> yin_detector::get_param_names() const {
  return {"fmin", "fmax", "threshold", "update_hop"};
}
#endif
