#pragma once
#include <vector>
#include <string>
#include <cstdint>

using std::vector;
using std::string;

// HarmonicRejector — multi-filter LPF bank with cleanness scoring and a
// selector that outputs a trusted period estimate (P) for the loop controller.
//
// See "Harmonic rejection" in Pitch Shifter concept.md for the design rationale.
//
// Per filter k:
//   - 2nd-order Butterworth LPF (12 dB/oct), causal biquad
//   - One-pole envelope follower on |x_filt|
//   - Tall-peak detection (1-sample delay): local max of x_filt above
//     peak_frac * env_filt, with minimum spacing constraint
//   - EMA over inter-tall-peak intervals → mu (period in samples), sigma (std)
//   - cleanness = 1 / (1 + sigma/mu)
//   - amplitude = env_filt / env_raw
//
// Selector picks the lowest-cutoff filter where cleanness >= cleanness_thresh
// AND amplitude >= amp_thresh AND at least min_intervals_for_qualified
// inter-peak intervals have been observed (so the EMA has settled).
// Selected mu becomes P for the loop controller.
//
// Inputs (1): audio
// Outputs (7 * NUM_FILTERS + 4 = 25 for NUM_FILTERS=3):
//   per filter k in [0, NUM_FILTERS):
//     0*N + k : x_filt
//     1*N + k : env_filt
//     2*N + k : tall_peak (impulse 0/1)
//     3*N + k : mu (samples)
//     4*N + k : sigma (samples)
//     5*N + k : cleanness
//     6*N + k : amplitude
//   7*N + 0 : selected_filter_index (-1.0 if none)
//   7*N + 1 : P (selected mu, samples; 0 if none)
//   7*N + 2 : sigma_sel (selected sigma; 0 if none)
//   7*N + 3 : qualified (1.0 if a filter is selected else 0.0)
//
// Parameters (set_param / get_param):
//   fc_0, fc_1, fc_2          per-filter LPF cutoffs (Hz)
//   peak_frac                 tall-peak threshold as fraction of envelope
//   ema_tau_intervals         EMA time constant, expressed in # of intervals
//   cleanness_thresh, amp_thresh   selector qualification thresholds
//   env_fc_hz                 envelope follower cutoff (Hz)
//   min_peak_distance_ms      minimum spacing between consecutive peaks (ms)

class HarmonicRejector {
public:
    static const int NUM_FILTERS = 3;
    static const int NUM_OUTPUTS = 7 * NUM_FILTERS + 4;

    // A filter is "qualified" (eligible for selection) only after this many
    // intervals have been observed — guards against acting on uninitialised
    // mu/sigma from EMA warmup.
    static const int MIN_INTERVALS_FOR_QUALIFIED = 3;

    HarmonicRejector();

    void init(int sample_rate);

    int get_num_inputs()  const { return 1; }
    int get_num_outputs() const { return NUM_OUTPUTS; }
    int get_sample_rate() const { return (int)sample_rate_; }

    void process(const float* const* inputs, float* const* outputs, int n);

    void set_param(const string& name, float value);
    float get_param(const string& name) const;
    vector<string> get_param_names() const;

private:
    struct FilterState {
        // Biquad coefficients (recomputed when fc changes)
        float fc;
        float b0, b1, b2, a1, a2;
        // Biquad delay-line state
        float x1, x2, y1, y2;

        // Envelope follower
        float env_filt;

        // Peak detection — we look back one sample to confirm a local max,
        // so we keep two samples of (x_filt, env_filt) plus current.
        float x_filt_prev;       // x_filt one sample ago
        float x_filt_two_ago;    // x_filt two samples ago
        float env_filt_prev;     // env_filt one sample ago

        // Inter-peak interval tracking
        int32_t last_peak_sample;       // absolute sample index of last tall peak
        int     samples_since_last_peak;
        int     intervals_seen;

        // Running EMA stats (defined once intervals_seen >= 1 for mu, >= 2 for sigma)
        float mu;        // samples
        float sigma_sq;  // EMA of squared residual against pre-update mu
        float cleanness; // 1/(1+sigma/mu); held between peak events
    };

    // ---- helpers ----
    void update_filter_coefs(int k);
    void update_envelope_coef();
    void update_ema_alpha();
    void update_min_peak_distance_samples();

    // ---- state ----
    FilterState filters_[NUM_FILTERS];

    float env_raw_;     // one-pole envelope of |audio|
    float sample_rate_;
    int32_t sample_index_;

    // Parameters
    float peak_frac_;
    float ema_tau_intervals_;
    float ema_alpha_;
    float cleanness_thresh_;
    float amp_thresh_;
    float env_fc_hz_;
    float env_alpha_;
    float min_peak_distance_ms_;
    int   min_peak_distance_samples_;
};
