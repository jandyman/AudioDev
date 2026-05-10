#include "loop_controller.h"
#include <cmath>
#include <cstring>
#include <stdexcept>
#include <algorithm>

// ============================================================
// Constructor / init
// ============================================================

LoopController::LoopController() {
    memset(this, 0, sizeof(*this));
    pitch_ratio_ = 0.5f;
    active_tap_  = 0;
    cf_gain_[0]  = 1.0f;
    cf_gain_[1]  = 0.0f;
}

void LoopController::init(int sample_rate) {
    sample_rate_  = (float)sample_rate;
    sample_index_ = 0;

    tap_delay_[0] = MIN_DELAY_SAMPLES;
    tap_delay_[1] = MIN_DELAY_SAMPLES;
    active_tap_   = 0;
    cf_gain_[0]   = 1.0f;
    cf_gain_[1]   = 0.0f;
    in_crossfade_ = false;
    cf_elapsed_   = 0;
    cf_duration_  = 1;

    transition_scheduled_ = false;
    transition_fire_pt_   = 0.0f;

    zc_head_  = 0;
    zc_count_ = 0;

    set_pitch_ratio(pitch_ratio_);
}

void LoopController::set_pitch_ratio(float ratio) {
    // Clamp to a safe range (must be < 1 for downward pitch shift)
    pitch_ratio_ = std::max(0.1f, std::min(ratio, 0.99f));
    dd_          = 1.0f - pitch_ratio_;

    update_derived_constants();

    // Flush ZC history: stored PT values are invalid with the new ratio
    flush_zc_history();
    transition_scheduled_ = false;
}

void LoopController::update_derived_constants() {
    // Output-domain period range: T_output = T_input / pitch_ratio
    // T_input = sample_rate / freq, so T_output = sample_rate / (freq * pitch_ratio)
    min_period_ = sample_rate_ / FREQ_HIGH_HZ / pitch_ratio_;
    max_period_ = sample_rate_ / FREQ_LOW_HZ  / pitch_ratio_;

    lower_threshold_ = LOWER_THRESHOLD_MS * sample_rate_ / 1000.0f;
    upper_threshold_ = UPPER_THRESHOLD_MS * sample_rate_ / 1000.0f;

    loop_cf_samples_    = (int)(LOOP_CROSSFADE_MS   * sample_rate_ / 1000.0f);
    attack_cf_samples_  = (int)(ATTACK_FADEIN_MS    * sample_rate_ / 1000.0f);
    bailout_cf_samples_ = (int)(LOOP_CROSSFADE_MS * BAILOUT_CROSSFADE_MULT * sample_rate_ / 1000.0f);

    if (loop_cf_samples_    < 1) loop_cf_samples_    = 1;
    if (attack_cf_samples_  < 1) attack_cf_samples_  = 1;
    if (bailout_cf_samples_ < 1) bailout_cf_samples_ = 1;
}

// ============================================================
// process() — buffer loop, calls compute() per sample
// ============================================================

void LoopController::process(const vector<vector<float>>& inputs,
                                   vector<vector<float>>& outputs) {
    if (inputs.size() < 2) return;

    int num_samples = (int)inputs[0].size();

    // Resize outputs if needed
    for (auto& ch : outputs) {
        if ((int)ch.size() != num_samples)
            ch.assign(num_samples, 0.0f);
    }

    for (int n = 0; n < num_samples; n++) {
        float zc_impulse     = inputs[0][n];
        float attack_impulse = inputs[1][n];

        compute(zc_impulse, attack_impulse,
                outputs[0][n], outputs[1][n],   // tap1_delay_ms, tap2_delay_ms
                outputs[2][n], outputs[3][n],   // gain1, gain2
                outputs[4][n], outputs[5][n],   // latency_ms, loop_event
                outputs[6][n], outputs[7][n]);  // active_tap, bailout_event
    }
}

// ============================================================
// compute() — per-sample logic
// ============================================================

void LoopController::compute(float zc_impulse, float attack_impulse,
                              float& tap1_delay_ms, float& tap2_delay_ms,
                              float& gain1, float& gain2,
                              float& latency_ms, float& loop_event,
                              float& active_tap_out, float& bailout_event) {
    loop_event    = 0.0f;
    bailout_event = 0.0f;

    // 1. Advance sample counter
    sample_index_++;

    // 2. Ramp both tap delays — this is the pitch-shift mechanism
    tap_delay_[0] += dd_;
    tap_delay_[1] += dd_;

    // 3. Advance crossfade
    if (in_crossfade_) {
        cf_elapsed_++;
        float t = (float)cf_elapsed_ / (float)cf_duration_;
        if (t >= 1.0f) {
            // Complete: commit the incoming tap as active
            int incoming      = 1 - active_tap_;
            active_tap_       = incoming;
            cf_gain_[active_tap_]     = 1.0f;
            cf_gain_[1 - active_tap_] = 0.0f;
            in_crossfade_     = false;
        } else {
            int incoming           = 1 - active_tap_;
            cf_gain_[incoming]     = t;
            cf_gain_[active_tap_]  = 1.0f - t;
        }
    }

    // 4. Fire a scheduled loop transition if it's time
    //    (delay on inactive tap was already set at scheduling time — it has
    //     been ramping since then and now reads from the target zero crossing)
    if (transition_scheduled_ && (float)sample_index_ >= transition_fire_pt_) {
        start_crossfade(-1.0f, loop_cf_samples_);  // -1: delay already set
        loop_event = 1.0f;
        transition_scheduled_ = false;
    }

    // 5. Attack (highest priority — preempts any pending transition)
    if (attack_impulse > 0.5f) {
        transition_scheduled_ = false;
        flush_zc_history();
        start_crossfade(MIN_DELAY_SAMPLES, attack_cf_samples_);
    }

    // 6. Handle qualified zero crossing
    if (zc_impulse > 0.5f) {
        // Compute playback time: PT = AT + DI / pitch_ratio
        // AT = sample_index_ (now), DI = active tap delay (now)
        float di = tap_delay_[active_tap_];
        float pt = (float)sample_index_ + di / pitch_ratio_;

        add_zc_record(sample_index_, pt);
        prune_zc_history();

        // Only search for loop candidates when:
        // - not mid-crossfade (avoid double-scheduling)
        // - no transition already pending
        float latency = tap_delay_[active_tap_];

        if (!in_crossfade_ && !transition_scheduled_) {
            if (latency > upper_threshold_) {
                // Bailout: fire immediately at this ZC input sample.
                // Waiting for the output ZC at PT is not viable — the inactive
                // tap ramps at dd, so by PT its delay equals time_until_fire,
                // which matches the active tap at fire time: no latency reduction.
                // Fire now with the long crossfade to reduce the artifact.
                start_crossfade(MIN_DELAY_SAMPLES, bailout_cf_samples_);
                flush_zc_history();   // old records are invalid after delay reset
                bailout_event = 1.0f;

            } else if (latency > lower_threshold_) {
                float new_delay_now, fire_pt;
                if (find_candidate(new_delay_now, fire_pt)) {
                    // Set inactive tap now so it ramps to the correct position by fire time
                    int incoming         = 1 - active_tap_;
                    tap_delay_[incoming] = new_delay_now;
                    transition_fire_pt_  = fire_pt;
                    transition_scheduled_ = true;
                }
            }
        }
    }

    // 7. Write outputs
    float ms_per_sample = 1000.0f / sample_rate_;
    tap1_delay_ms  = tap_delay_[0] * ms_per_sample;
    tap2_delay_ms  = tap_delay_[1] * ms_per_sample;
    gain1          = cf_gain_[0];
    gain2          = cf_gain_[1];
    latency_ms     = tap_delay_[active_tap_] * ms_per_sample;
    active_tap_out = (float)active_tap_;
}

// ============================================================
// Helpers
// ============================================================

void LoopController::add_zc_record(int32_t at, float pt) {
    zc_history_[zc_head_] = {at, pt};
    zc_head_ = (zc_head_ + 1) % ZC_HISTORY_SIZE;
    if (zc_count_ < ZC_HISTORY_SIZE) zc_count_++;
}

void LoopController::prune_zc_history() {
    // Remove oldest records whose PT has already passed
    while (zc_count_ > 0) {
        int oldest_idx = (zc_head_ - zc_count_ + ZC_HISTORY_SIZE) % ZC_HISTORY_SIZE;
        if (zc_history_[oldest_idx].pt <= (float)sample_index_) {
            zc_count_--;
        } else {
            break;
        }
    }
}

void LoopController::flush_zc_history() {
    zc_head_  = 0;
    zc_count_ = 0;
}

bool LoopController::find_candidate(float& out_new_delay_now, float& out_fire_pt) {
    // PT of the current ZC just arrived
    float pt_new       = (float)sample_index_ + tap_delay_[active_tap_] / pitch_ratio_;
    float current_delay = tap_delay_[active_tap_];

    int start = (zc_head_ - zc_count_ + ZC_HISTORY_SIZE) % ZC_HISTORY_SIZE;

    // Iterate oldest to newest: first valid hit gives minimum time_until_fire
    // (new delay at fire = PT_old - S = time_until_fire; older records have smaller PT_old)
    for (int i = 0; i < zc_count_; i++) {
        int idx = (start + i) % ZC_HISTORY_SIZE;
        const ZCRecord& rec = zc_history_[idx];

        float time_until_fire = rec.pt - (float)sample_index_;
        if (time_until_fire <= 0.0f) continue;   // already past

        // New delay at fire time = time_until_fire (derived in spec).
        // Must reduce latency.
        if (time_until_fire * pitch_ratio_ >= current_delay) continue;

        // Check period alignment: pt_new - rec.pt ≈ N × T_output_period
        float pt_diff = pt_new - rec.pt;
        if (pt_diff <= 0.0f) continue;

        float tol_lo = PERIOD_TOLERANCE;
        float tol_hi = PERIOD_TOLERANCE;
        float n_lo = pt_diff / (max_period_ * (1.0f + tol_lo));
        float n_hi = pt_diff / (min_period_ * (1.0f - tol_hi));

        int n_min = (int)ceilf(n_lo);
        int n_max = (int)floorf(n_hi);

        if (n_min >= 1 && n_min <= n_max) {
            // Valid: set inactive tap now to ramp to correct position by fire time.
            // At scheduling time t=0, delay = D0. At fire time t=time_until_fire:
            //   delay = D0 + time_until_fire * dd = time_until_fire (desired)
            // Solving: D0 = time_until_fire * (1 - dd) = time_until_fire * pitch_ratio
            out_new_delay_now = std::max(MIN_DELAY_SAMPLES,
                                         time_until_fire * pitch_ratio_);
            out_fire_pt = rec.pt;
            return true;
        }
    }
    return false;
}

void LoopController::start_crossfade(float new_delay_override, int cf_duration) {
    int incoming = 1 - active_tap_;

    if (new_delay_override >= 0.0f) {
        // Override delay (used for attack and bailout firing)
        tap_delay_[incoming] = new_delay_override;
    }
    // For loop transitions new_delay_override == -1: delay was already set
    // at scheduling time and has been ramping to the correct position.

    // If we're interrupting a crossfade in progress (attack preempting loop):
    // keep current gains so there's no gain discontinuity; reset elapsed
    // to restart the fade from the current gain state toward the new target.
    // (This is the two-tap approximation of the deferred three-tap problem.)
    if (!in_crossfade_) {
        cf_gain_[active_tap_] = 1.0f;
        cf_gain_[incoming]    = 0.0f;
    } else {
        // Redirect crossfade: reset incoming gain to 0 so it fades in cleanly.
        // Outgoing continues fading from wherever it is.
        cf_gain_[incoming] = 0.0f;
    }

    in_crossfade_ = true;
    cf_elapsed_   = 0;
    cf_duration_  = (cf_duration > 0) ? cf_duration : 1;
}

// ============================================================
// Parameters
// ============================================================

void LoopController::set_param(const string& name, float value) {
    if (name == "pitch_ratio") {
        set_pitch_ratio(value);
    }
}

float LoopController::get_param(const string& name) const {
    if (name == "pitch_ratio") return pitch_ratio_;
    return 0.0f;
}

vector<string> LoopController::get_param_names() const {
    return {"pitch_ratio"};
}
