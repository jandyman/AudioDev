/* @block
(define-block LoopController
 (inputs zc_impulse attack_impulse P_samples sigma_samples qualified)
 (outputs tap1_delay_ms tap2_delay_ms gain1 gain2 latency_ms loop_event active_tap bailout_event gated_event)
 (params (pitch_ratio :default 0.5)))
*/

#include "loop_controller.h"
#include <cmath>
#include <cstring>
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
    tap_delay_[1] = 0.0f;                // inactive tap starts parked
    active_tap_   = 0;
    cf_gain_[0]   = 1.0f;
    cf_gain_[1]   = 0.0f;
    in_crossfade_ = false;
    cf_elapsed_   = 0;
    cf_duration_  = 1;

    zc_head_  = 0;
    zc_count_ = 0;

    set_pitch_ratio(pitch_ratio_);
}

void LoopController::set_pitch_ratio(float ratio) {
    // Clamp to a safe range (must be < 1 for downward pitch shift)
    pitch_ratio_ = std::max(0.1f, std::min(ratio, 0.99f));
    dd_          = 1.0f - pitch_ratio_;

    update_derived_constants();
    flush_zc_history();
}

void LoopController::update_derived_constants() {
    lower_threshold_    = LOWER_THRESHOLD_MS * sample_rate_ / 1000.0f;
    upper_threshold_    = UPPER_THRESHOLD_MS * sample_rate_ / 1000.0f;

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

void LoopController::process(const float* const* inputs, float* const* outputs, int n) {
    for (int i = 0; i < n; i++) {
        compute(inputs[0][i], inputs[1][i],
                inputs[2][i], inputs[3][i], inputs[4][i],
                outputs[0][i], outputs[1][i],   // tap1_delay_ms, tap2_delay_ms
                outputs[2][i], outputs[3][i],   // gain1, gain2
                outputs[4][i], outputs[5][i],   // latency_ms, loop_event
                outputs[6][i], outputs[7][i],   // active_tap, bailout_event
                outputs[8][i]);                 // gated_event
    }
}

// ============================================================
// compute() — per-sample logic
//
// The order matters:
//   1. Advance sample counter.
//   2. Ramp tap delays (active always; inactive only when live).
//   3. Advance any in-progress cross-fade.
//   4. Handle attack (highest priority).
//   5. Record incoming ZC impulse.
//   6. Loop check / cross-fade fire (output-side detection).
//   7. Bailout check (per-sample, not gated on input ZC arrival).
//   8. Write outputs.
// ============================================================

void LoopController::compute(float zc_impulse, float attack_impulse,
                              float P_samples, float sigma_samples, float qualified,
                              float& tap1_delay_ms, float& tap2_delay_ms,
                              float& gain1, float& gain2,
                              float& latency_ms, float& loop_event,
                              float& active_tap_out, float& bailout_event,
                              float& gated_event) {
    loop_event    = 0.0f;
    bailout_event = 0.0f;
    gated_event   = 0.0f;

    // 1. Advance sample counter
    sample_index_++;

    // 2. Ramp tap delays — pitch-shift mechanism.
    //    Inactive tap ramps only when it's "live" (in cross-fade);
    //    otherwise it stays parked at zero.
    if (in_crossfade_) {
        tap_delay_[0] += dd_;
        tap_delay_[1] += dd_;
    } else {
        tap_delay_[active_tap_] += dd_;
    }

    // 3. Advance cross-fade
    if (in_crossfade_) {
        cf_elapsed_++;
        float t = (float)cf_elapsed_ / (float)cf_duration_;
        if (t >= 1.0f) {
            int incoming               = 1 - active_tap_;
            active_tap_                = incoming;
            cf_gain_[active_tap_]      = 1.0f;
            cf_gain_[1 - active_tap_]  = 0.0f;
            tap_delay_[1 - active_tap_] = 0.0f;   // park outgoing tap
            in_crossfade_              = false;
        } else {
            int incoming           = 1 - active_tap_;
            cf_gain_[incoming]     = t;
            cf_gain_[active_tap_]  = 1.0f - t;
        }
    }

    // 4. Attack (highest priority — preempts everything)
    if (attack_impulse > 0.5f) {
        flush_zc_history();
        start_crossfade(MIN_DELAY_SAMPLES, attack_cf_samples_);
    }

    // 5. Record incoming ZC impulse
    if (zc_impulse > 0.5f) {
        add_zc_record(sample_index_);
    }

    // 6. Loop check — per-output-sample.
    //    AT_out is the absolute input-time of the sample being emitted now.
    //    While the head has been reached or passed by AT_out, decide
    //    whether to fire and pop. Strict less-than pruning would drop
    //    the head before we got a chance to act on it; the while-loop
    //    here combines prune and fire into a single check.
    float AT_out = (float)sample_index_ - tap_delay_[active_tap_];

    while (zc_count_ > 0) {
        int32_t head_at;
        peek_oldest(head_at);
        if (AT_out < (float)head_at) break;     // not yet reached this ZC

        // AT_out has reached (or just crossed) head.AT.
        if (in_crossfade_) {
            // (a) mid-cross-fade — can't fire again; just discard the entry.
            pop_oldest();
            continue;
        }

        float DT_active = tap_delay_[active_tap_];

        // (b) fire if latency above threshold and we have a usable candidate.
        //     Scan from newest (tail) toward head+1. Each candidate must
        //     satisfy DT_inactive >= MIN_DELAY_SAMPLES (existing
        //     latency-reduction constraint). When the integer-multiple gate is
        //     active (qualified > 0.5 and P > 0), additionally require the
        //     period-alignment condition:
        //         | delta − round(delta/P) * P | <= margin,  k = round(...) >= 1
        //     where margin = base * urgency, base = max(MARGIN_FRAC_P*P, sigma),
        //     and urgency scales from 1 at the lower threshold to URGENCY_MAX_MULT
        //     at the upper threshold.
        //     If we find a gate-passing candidate, fire it. Otherwise fall back
        //     to the newest DT-valid candidate (the original behaviour) — this
        //     is purely additive over the prior algorithm.
        bool fired = false;
        if (DT_active > lower_threshold_ && zc_count_ >= 2) {
            // Margin (samples). gate_active iff we have a usable estimate.
            bool gate_active = (qualified > 0.5f) && (P_samples > 1.0f);
            float margin = 0.0f;
            if (gate_active) {
                float base = MARGIN_FRAC_P * P_samples;
                if (sigma_samples > base) base = sigma_samples;
                float urgency_t = (DT_active - lower_threshold_) /
                                  (upper_threshold_ - lower_threshold_);
                if (urgency_t < 0.0f) urgency_t = 0.0f;
                if (urgency_t > 1.0f) urgency_t = 1.0f;
                float urgency_mult = 1.0f + urgency_t * (URGENCY_MAX_MULT - 1.0f);
                margin = base * urgency_mult;
            }

            int head_idx     = (zc_head_ - zc_count_ + ZC_HISTORY_SIZE) % ZC_HISTORY_SIZE;
            int fallback_i   = -1;     // newest DT-valid candidate (existing pick)
            int match_i      = -1;     // newest DT-valid AND gate-passing
            float fb_inactive = 0.0f, match_inactive = 0.0f;
            for (int i = zc_count_ - 1; i > 0; i--) {
                int idx = (head_idx + i) % ZC_HISTORY_SIZE;
                int32_t at_new = zc_history_[idx];
                float delta_samples = (float)(at_new - head_at);
                float new_inactive = DT_active - delta_samples;
                if (new_inactive < MIN_DELAY_SAMPLES) continue;

                if (fallback_i < 0) {
                    fallback_i  = i;
                    fb_inactive = new_inactive;
                }

                if (gate_active) {
                    float k = roundf(delta_samples / P_samples);
                    if (k < 1.0f) continue;
                    float misalign = fabsf(delta_samples - k * P_samples);
                    if (misalign > margin) continue;
                }

                match_i        = i;
                match_inactive = new_inactive;
                break;   // first scanning newest -> oldest wins
            }

            int    fire_i        = (match_i >= 0) ? match_i        : fallback_i;
            float  fire_inactive = (match_i >= 0) ? match_inactive : fb_inactive;
            if (fire_i >= 0) {
                tap_delay_[1 - active_tap_] = fire_inactive;
                start_crossfade(-1.0f, loop_cf_samples_);
                loop_event = 1.0f;
                if (gate_active && match_i >= 0 && match_i != fallback_i) {
                    gated_event = 1.0f;   // gate picked a different candidate than fallback
                }
                pop_oldest();
                fired = true;
            }
            if (fired) break;   // exit the while-loop; we're in cross-fade
        }

        // (c) latency below threshold, or no usable candidate — skip this ZC
        pop_oldest();
    }

    // 7. Bailout — per-sample, regardless of whether a ZC is at the output.
    //    This catches cases where AT_out has no candidate to align to
    //    (silence, noise tails, unpitched content) so the active delay
    //    can never run away unboundedly past the upper threshold.
    if (!in_crossfade_ && tap_delay_[active_tap_] > upper_threshold_) {
        start_crossfade(MIN_DELAY_SAMPLES, bailout_cf_samples_);
        flush_zc_history();    // ring buffer is stale after a delay reset
        bailout_event = 1.0f;
    }

    // 8. Write outputs
    float ms_per_sample = 1000.0f / sample_rate_;
    tap1_delay_ms  = tap_delay_[0] * ms_per_sample;
    tap2_delay_ms  = tap_delay_[1] * ms_per_sample;
    gain1          = cf_gain_[0];
    gain2          = cf_gain_[1];
    latency_ms     = tap_delay_[active_tap_] * ms_per_sample;
    active_tap_out = (float)active_tap_;
}

// ============================================================
// Ring buffer helpers
// ============================================================

void LoopController::add_zc_record(int32_t at) {
    zc_history_[zc_head_] = at;
    zc_head_ = (zc_head_ + 1) % ZC_HISTORY_SIZE;
    if (zc_count_ < ZC_HISTORY_SIZE) zc_count_++;
}

void LoopController::pop_oldest() {
    if (zc_count_ > 0) zc_count_--;
}

void LoopController::flush_zc_history() {
    zc_head_  = 0;
    zc_count_ = 0;
}

bool LoopController::peek_oldest(int32_t& out) const {
    if (zc_count_ == 0) return false;
    int idx = (zc_head_ - zc_count_ + ZC_HISTORY_SIZE) % ZC_HISTORY_SIZE;
    out = zc_history_[idx];
    return true;
}

void LoopController::start_crossfade(float new_delay_override, int cf_duration) {
    int incoming = 1 - active_tap_;

    if (new_delay_override >= 0.0f) {
        // Override delay (used for attack and bailout firing)
        tap_delay_[incoming] = new_delay_override;
    }
    // For loop transitions new_delay_override == -1: the inactive tap delay
    // was already set by the caller (`DT_inactive = DT_active − (AT_new − AT_old)`).

    if (!in_crossfade_) {
        cf_gain_[active_tap_] = 1.0f;
        cf_gain_[incoming]    = 0.0f;
    } else {
        // Redirecting an in-progress crossfade (attack preempting loop):
        // keep current outgoing gain so there's no gain discontinuity;
        // reset incoming gain to 0 and restart the fade.
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
