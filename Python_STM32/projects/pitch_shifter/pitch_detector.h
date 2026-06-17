#pragma once
#include <cstdint>
#ifndef BARE_METAL
#include <vector>
#include <string>
using std::vector;
using std::string;
#endif

// pitch_detector — multi-filter LPF bank with per-filter cleanness scoring
// and a selector that outputs a trusted period estimate (P, sigma_sel,
// qualified) for the loop controller. Design, outputs, and parameters:
// pitch_detector.md.

class pitch_detector {
public:
    static const int NUM_FILTERS = 3;
    static const int NUM_OUTPUTS = 7 * NUM_FILTERS + 4;

    // A filter is "qualified" (eligible for selection) only after this many
    // intervals have been observed — guards against acting on uninitialised
    // mu/sigma from EMA warmup.
    static const int MIN_INTERVALS_FOR_QUALIFIED = 3;

    pitch_detector();

    void init(int sample_rate);

    int get_num_inputs()  const { return 2; }
    int get_num_outputs() const { return NUM_OUTPUTS; }
    int get_sample_rate() const { return (int)sample_rate_; }

    void process(const float* const* inputs, float* const* outputs, int n);

    void set_param(const char* name, float value);
    float get_param(const char* name) const;
#ifndef BARE_METAL
    vector<string> get_param_names() const;
#endif

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
