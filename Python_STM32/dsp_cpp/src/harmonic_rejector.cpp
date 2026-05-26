#include "harmonic_rejector.h"
#include <cmath>
#include <cstring>
#include <algorithm>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// Out-of-class definitions for ODR-use (pybind def_readonly_static needs these)
const int HarmonicRejector::NUM_FILTERS;
const int HarmonicRejector::NUM_OUTPUTS;
const int HarmonicRejector::MIN_INTERVALS_FOR_QUALIFIED;

static const float DEFAULT_FCS[HarmonicRejector::NUM_FILTERS] = { 60.0f, 120.0f, 240.0f };

// ============================================================
// Constructor / init
// ============================================================

HarmonicRejector::HarmonicRejector() {
    memset(this, 0, sizeof(*this));
    for (int k = 0; k < NUM_FILTERS; k++) filters_[k].fc = DEFAULT_FCS[k];
    peak_frac_           = 0.65f;
    ema_tau_intervals_   = 4.0f;
    cleanness_thresh_    = 0.50f;
    amp_thresh_          = 0.15f;
    env_fc_hz_           = 30.0f;
    min_peak_distance_ms_ = 1.0f;
    sample_rate_         = 48000.0f;
}

void HarmonicRejector::init(int sample_rate) {
    sample_rate_  = (float)sample_rate;
    sample_index_ = 0;
    env_raw_      = 0.0f;

    for (int k = 0; k < NUM_FILTERS; k++) {
        FilterState& f = filters_[k];
        f.x1 = f.x2 = f.y1 = f.y2 = 0.0f;
        f.env_filt = 0.0f;
        f.x_filt_prev = 0.0f;
        f.x_filt_two_ago = 0.0f;
        f.env_filt_prev = 0.0f;
        f.last_peak_sample = 0;
        f.samples_since_last_peak = 0;
        f.intervals_seen = 0;
        f.mu = 0.0f;
        f.sigma_sq = 0.0f;
        f.cleanness = 0.0f;
        update_filter_coefs(k);
    }

    update_envelope_coef();
    update_ema_alpha();
    update_min_peak_distance_samples();
}

// 2nd-order Butterworth LPF (RBJ cookbook, Q = 1/sqrt(2))
void HarmonicRejector::update_filter_coefs(int k) {
    FilterState& f = filters_[k];
    if (f.fc <= 0.0f || sample_rate_ <= 0.0f) return;

    const float Q     = 0.70710678f;   // 1/sqrt(2), Butterworth
    float w0          = 2.0f * (float)M_PI * f.fc / sample_rate_;
    float cos_w0      = cosf(w0);
    float sin_w0      = sinf(w0);
    float alpha       = sin_w0 / (2.0f * Q);

    float b0u = (1.0f - cos_w0) * 0.5f;
    float b1u =  1.0f - cos_w0;
    float b2u = (1.0f - cos_w0) * 0.5f;
    float a0u =  1.0f + alpha;
    float a1u = -2.0f * cos_w0;
    float a2u =  1.0f - alpha;

    f.b0 = b0u / a0u;
    f.b1 = b1u / a0u;
    f.b2 = b2u / a0u;
    f.a1 = a1u / a0u;
    f.a2 = a2u / a0u;
}

void HarmonicRejector::update_envelope_coef() {
    if (sample_rate_ <= 0.0f) return;
    // One-pole: alpha = 1 - exp(-2*pi*fc/fs)
    float w = 2.0f * (float)M_PI * env_fc_hz_ / sample_rate_;
    env_alpha_ = 1.0f - expf(-w);
    if (env_alpha_ < 0.0f) env_alpha_ = 0.0f;
    if (env_alpha_ > 1.0f) env_alpha_ = 1.0f;
}

void HarmonicRejector::update_ema_alpha() {
    if (ema_tau_intervals_ <= 0.5f) ema_tau_intervals_ = 0.5f;
    ema_alpha_ = 1.0f - expf(-1.0f / ema_tau_intervals_);
}

void HarmonicRejector::update_min_peak_distance_samples() {
    min_peak_distance_samples_ = (int)(min_peak_distance_ms_ * sample_rate_ / 1000.0f);
    if (min_peak_distance_samples_ < 1) min_peak_distance_samples_ = 1;
}

// ============================================================
// process()
// ============================================================

void HarmonicRejector::process(const float* const* inputs, float* const* outputs, int num_samples) {
    const int N = NUM_FILTERS;
    const float EPS = 1e-6f;

    for (int n = 0; n < num_samples; n++) {
        float audio = inputs[0][n];
        sample_index_++;

        // Raw envelope follower
        float abs_audio = fabsf(audio);
        env_raw_ += env_alpha_ * (abs_audio - env_raw_);

        // Selector pass over filters (lowest-cutoff first)
        int   selected = -1;
        float P_sel    = 0.0f;
        float sig_sel  = 0.0f;

        for (int k = 0; k < N; k++) {
            FilterState& f = filters_[k];

            // Biquad LPF
            float x_filt = f.b0 * audio + f.b1 * f.x1 + f.b2 * f.x2
                         - f.a1 * f.y1 - f.a2 * f.y2;
            f.x2 = f.x1; f.x1 = audio;
            f.y2 = f.y1; f.y1 = x_filt;

            // Envelope follower
            f.env_filt += env_alpha_ * (fabsf(x_filt) - f.env_filt);

            // Peak detection (1-sample-delayed): is x_filt_prev a local max?
            float tall_impulse = 0.0f;
            f.samples_since_last_peak++;

            if (f.x_filt_two_ago < f.x_filt_prev && f.x_filt_prev > x_filt &&
                f.samples_since_last_peak >= min_peak_distance_samples_ &&
                f.x_filt_prev >= peak_frac_ * f.env_filt_prev) {

                int32_t peak_sample = sample_index_ - 1;   // peak was last sample
                if (f.intervals_seen == 0 && f.last_peak_sample == 0) {
                    // first ever peak — initialise reference, no interval yet
                    f.last_peak_sample = peak_sample;
                } else {
                    float interval = (float)(peak_sample - f.last_peak_sample);
                    if (interval > 0.0f) {
                        if (f.intervals_seen == 0) {
                            f.mu       = interval;
                            f.sigma_sq = 0.0f;
                        } else {
                            float delta = interval - f.mu;        // use pre-update mu
                            f.mu       += ema_alpha_ * delta;
                            f.sigma_sq += ema_alpha_ * (delta * delta - f.sigma_sq);
                        }
                        f.intervals_seen++;
                        if (f.mu > EPS) {
                            float sigma = sqrtf(f.sigma_sq);
                            f.cleanness = 1.0f / (1.0f + sigma / f.mu);
                        } else {
                            f.cleanness = 0.0f;
                        }
                        f.last_peak_sample = peak_sample;
                    }
                }

                f.samples_since_last_peak = 0;
                tall_impulse = 1.0f;
            }

            // Shift peak-detection memory
            f.x_filt_two_ago = f.x_filt_prev;
            f.x_filt_prev    = x_filt;
            f.env_filt_prev  = f.env_filt;

            // Per-filter outputs
            float sigma     = sqrtf(f.sigma_sq);
            float amplitude = f.env_filt / (env_raw_ > EPS ? env_raw_ : EPS);

            outputs[0 * N + k][n] = x_filt;
            outputs[1 * N + k][n] = f.env_filt;
            outputs[2 * N + k][n] = tall_impulse;
            outputs[3 * N + k][n] = f.mu;
            outputs[4 * N + k][n] = sigma;
            outputs[5 * N + k][n] = f.cleanness;
            outputs[6 * N + k][n] = amplitude;

            // Selector: lowest-cutoff filter qualifying both gates wins
            if (selected < 0
                && f.intervals_seen >= MIN_INTERVALS_FOR_QUALIFIED
                && f.cleanness >= cleanness_thresh_
                && amplitude   >= amp_thresh_) {
                selected = k;
                P_sel    = f.mu;
                sig_sel  = sigma;
            }
        }

        // Aggregate outputs
        outputs[7 * N + 0][n] = (float)selected;        // -1 if none
        outputs[7 * N + 1][n] = P_sel;
        outputs[7 * N + 2][n] = sig_sel;
        outputs[7 * N + 3][n] = (selected >= 0) ? 1.0f : 0.0f;
    }
}

// ============================================================
// Parameters
// ============================================================

void HarmonicRejector::set_param(const string& name, float value) {
    if (name == "fc_0") { filters_[0].fc = value; update_filter_coefs(0); }
    else if (name == "fc_1" && NUM_FILTERS > 1) { filters_[1].fc = value; update_filter_coefs(1); }
    else if (name == "fc_2" && NUM_FILTERS > 2) { filters_[2].fc = value; update_filter_coefs(2); }
    else if (name == "peak_frac")          peak_frac_ = value;
    else if (name == "ema_tau_intervals")  { ema_tau_intervals_ = value; update_ema_alpha(); }
    else if (name == "cleanness_thresh")   cleanness_thresh_ = value;
    else if (name == "amp_thresh")         amp_thresh_ = value;
    else if (name == "env_fc_hz")          { env_fc_hz_ = value; update_envelope_coef(); }
    else if (name == "min_peak_distance_ms") { min_peak_distance_ms_ = value; update_min_peak_distance_samples(); }
}

float HarmonicRejector::get_param(const string& name) const {
    if (name == "fc_0") return filters_[0].fc;
    if (name == "fc_1" && NUM_FILTERS > 1) return filters_[1].fc;
    if (name == "fc_2" && NUM_FILTERS > 2) return filters_[2].fc;
    if (name == "peak_frac")           return peak_frac_;
    if (name == "ema_tau_intervals")   return ema_tau_intervals_;
    if (name == "cleanness_thresh")    return cleanness_thresh_;
    if (name == "amp_thresh")          return amp_thresh_;
    if (name == "env_fc_hz")           return env_fc_hz_;
    if (name == "min_peak_distance_ms") return min_peak_distance_ms_;
    return 0.0f;
}

vector<string> HarmonicRejector::get_param_names() const {
    return {"fc_0", "fc_1", "fc_2",
            "peak_frac", "ema_tau_intervals",
            "cleanness_thresh", "amp_thresh",
            "env_fc_hz", "min_peak_distance_ms"};
}
