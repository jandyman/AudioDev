/* @block
(define-block loop_controller
 (inputs zc_impulse attack_impulse P_samples sigma_samples qualified active_gain)
 (outputs tap1_delay_ms tap2_delay_ms tap3_delay_ms
          gain1 gain2 gain3
          latency_ms loop_event active_tap bailout_event gated_event attack_event)
 (params (pitch_ratio :default 0.5)))
*/

#include "loop_controller.h"
#include <cmath>
#include <cstring>
#include <algorithm>

// ============================================================
// Constructor / init
// ============================================================

loop_controller::loop_controller() {
  memset(this, 0, sizeof(*this));
  pitch_ratio_       = 0.5f;
  active_tap_        = 0;
  loop_incoming_tap_ = -1;
  attack_tap_        = -1;
  mode_              = MODE_LOOP_ONLY;
  gain_[0]           = 1.0f;
  gain_target_[0]    = 1.0f;
  live_[0]           = true;
}

void loop_controller::init(int sample_rate) {
  sample_rate_  = (float)sample_rate;
  sample_index_ = 0;

  for (int i = 0; i < NUM_TAPS; i++) {
    tap_delay_[i]   = 0.0f;
    live_[i]        = false;
    gain_[i]        = 0.0f;
    gain_target_[i] = 0.0f;
    gain_rate_[i]   = 0.0f;
  }
  tap_delay_[0]   = MIN_DELAY_SAMPLES;
  live_[0]        = true;
  gain_[0]        = 1.0f;
  gain_target_[0] = 1.0f;

  active_tap_        = 0;
  loop_incoming_tap_ = -1;
  attack_tap_        = -1;
  in_loop_crossfade_ = false;
  mode_              = MODE_LOOP_ONLY;

  zc_head_  = 0;
  zc_count_ = 0;

  set_pitch_ratio(pitch_ratio_);
}

void loop_controller::set_pitch_ratio(float ratio) {
  pitch_ratio_ = std::max(0.1f, std::min(ratio, 0.99f));
  dd_          = 1.0f - pitch_ratio_;
  update_derived_constants();
  flush_zc_history();
}

void loop_controller::update_derived_constants() {
  lower_threshold_        = LOWER_THRESHOLD_MS * sample_rate_ / 1000.0f;
  upper_threshold_        = UPPER_THRESHOLD_MS * sample_rate_ / 1000.0f;
  loop_cf_samples_        = (int)(LOOP_CROSSFADE_MS   * sample_rate_ / 1000.0f);
  attack_fadein_samples_  = (int)(ATTACK_FADEIN_MS    * sample_rate_ / 1000.0f);
  attack_fadeout_samples_ = (int)(ATTACK_FADEOUT_MS   * sample_rate_ / 1000.0f);
  bailout_cf_samples_     = (int)(LOOP_CROSSFADE_MS * BAILOUT_CROSSFADE_MULT * sample_rate_ / 1000.0f);

  if (loop_cf_samples_        < 1) loop_cf_samples_        = 1;
  if (attack_fadein_samples_  < 1) attack_fadein_samples_  = 1;
  if (attack_fadeout_samples_ < 1) attack_fadeout_samples_ = 1;
  if (bailout_cf_samples_     < 1) bailout_cf_samples_     = 1;
}

// ============================================================
// process() — buffer loop, calls compute() per sample
// ============================================================

void loop_controller::process(const float* const* inputs, float* const* outputs, int n) {
  for (int i = 0; i < n; i++) {
    compute(inputs[0][i], inputs[1][i],
            inputs[2][i], inputs[3][i], inputs[4][i],
            outputs[0][i], outputs[1][i], outputs[2][i],   // tapN_delay_ms
            outputs[3][i], outputs[4][i], outputs[5][i],   // gainN
            outputs[6][i], outputs[7][i],                  // latency_ms, loop_event
            outputs[8][i], outputs[9][i],                  // active_tap, bailout_event
            outputs[10][i], outputs[11][i]);               // gated_event, attack_event

    // Loop-tap gating: multiply loop-pair gains (gain1, gain2) by active_gain
    // so the buffer-bleed has no audible path during silence and the new
    // attack's crossfade. Attack tap (gain3) is intentionally NOT gated —
    // it must carry the new transient at full level.
    const float active_gain = inputs[5][i];
    outputs[3][i] *= active_gain;   // gain1
    outputs[4][i] *= active_gain;   // gain2
  }
}

// ============================================================
// advance_tap_state() — one sample of delay-ramp + gain-ramp per tap.
// Parks taps that reach gain=0.
// ============================================================

void loop_controller::advance_tap_state() {
  for (int i = 0; i < NUM_TAPS; i++) {
    if (live_[i]) tap_delay_[i] += dd_;

    if (gain_[i] != gain_target_[i]) {
      float diff = gain_target_[i] - gain_[i];
      if (diff > gain_rate_[i]) {
        gain_[i] += gain_rate_[i];
      } else if (diff < -gain_rate_[i]) {
        gain_[i] -= gain_rate_[i];
      } else {
        gain_[i] = gain_target_[i];
        if (gain_[i] == 0.0f) {
          live_[i]      = false;
          tap_delay_[i] = 0.0f;
        }
      }
    }
  }
}

// ============================================================
// pick_free_tap() — choose lowest-index tap not bound to a role.
// ============================================================

int loop_controller::pick_free_tap(bool exclude_loop_incoming) const {
  for (int i = 0; i < NUM_TAPS; i++) {
    if (i == active_tap_) continue;
    if (i == attack_tap_) continue;
    if (exclude_loop_incoming && i == loop_incoming_tap_) continue;
    return i;
  }
  return -1;   // shouldn't happen with NUM_TAPS=3 and at most 2 roles bound
}

// ============================================================
// start_loop_crossfade() — begin loop transition (or bailout) on a free tap.
// inactive_delay: the delay value to set on the chosen tap (in samples).
// cf_samples:     duration of the crossfade.
// ============================================================

void loop_controller::start_loop_crossfade(float inactive_delay, int cf_samples) {
  int target = pick_free_tap(false);
  if (target < 0) return;   // defensive — shouldn't happen in LOOP_ONLY mode

  tap_delay_[target]   = inactive_delay;
  live_[target]        = true;
  gain_[target]        = 0.0f;
  gain_target_[target] = 1.0f;
  gain_rate_[target]   = 1.0f / (float)cf_samples;

  // Active tap fades out at the same rate.
  gain_target_[active_tap_] = 0.0f;
  gain_rate_[active_tap_]   = 1.0f / (float)cf_samples;

  loop_incoming_tap_ = target;
  in_loop_crossfade_ = true;
}

// ============================================================
// start_attack_response() — engage the attack tap.
// ============================================================

void loop_controller::start_attack_response() {
  int target = pick_free_tap(true);
  if (target < 0) return;

  tap_delay_[target]   = MIN_DELAY_SAMPLES;
  live_[target]        = true;
  gain_[target]        = 0.0f;
  gain_target_[target] = 1.0f;
  gain_rate_[target]   = 1.0f / (float)attack_fadein_samples_;

  attack_tap_ = target;
  mode_       = MODE_ATTACK_FADEIN;
  flush_zc_history();
}

// ============================================================
// compute() — per-sample logic
//
// Order:
//   1. Advance sample counter.
//   2. Advance per-tap delay ramp + gain ramp (one sample).
//   3. Resolve role transitions on fade completion:
//        loop_incoming reaches 1     → becomes new active_tap
//        attack tap reaches 1        → mode = ATTACK_FADEOUT (ramp others down)
//        all non-attack gains = 0    → attack tap becomes new active_tap
//                                       (mode = LOOP_ONLY)
//   4. Attack impulse (only in LOOP_ONLY) — engage attack tap.
//   5. Record incoming ZC impulse.
//   6. Loop check (only in LOOP_ONLY).
//   7. Bailout (only in LOOP_ONLY).
//   8. Write outputs.
// ============================================================

void loop_controller::compute(float zc_impulse, float attack_impulse,
                              float P_samples, float sigma_samples, float qualified,
                              float& tap1_delay_ms, float& tap2_delay_ms, float& tap3_delay_ms,
                              float& gain1, float& gain2, float& gain3,
                              float& latency_ms, float& loop_event,
                              float& active_tap_out, float& bailout_event,
                              float& gated_event, float& attack_event) {
  loop_event    = 0.0f;
  bailout_event = 0.0f;
  gated_event   = 0.0f;
  attack_event  = 0.0f;

  // 1. Advance sample counter
  sample_index_++;

  // 2. Per-tap delay + gain ramp
  advance_tap_state();

  // 3. Role transitions on fade completion
  if (in_loop_crossfade_ && loop_incoming_tap_ >= 0 &&
      gain_[loop_incoming_tap_] >= 1.0f) {
    active_tap_        = loop_incoming_tap_;
    loop_incoming_tap_ = -1;
    in_loop_crossfade_ = false;
  }

  if (mode_ == MODE_ATTACK_FADEIN && attack_tap_ >= 0 &&
      gain_[attack_tap_] >= 1.0f) {
    // Attack at full gain. Ramp every other tap down. Abandon any in-progress
    // loop crossfade (its taps just join the fade-out pool).
    for (int i = 0; i < NUM_TAPS; i++) {
      if (i == attack_tap_) continue;
      if (gain_[i] > 0.0f || gain_target_[i] > 0.0f) {
        gain_target_[i] = 0.0f;
        gain_rate_[i]   = 1.0f / (float)attack_fadeout_samples_;
      }
    }
    in_loop_crossfade_ = false;
    loop_incoming_tap_ = -1;
    mode_              = MODE_ATTACK_FADEOUT;
  }

  if (mode_ == MODE_ATTACK_FADEOUT) {
    bool others_silent = true;
    for (int i = 0; i < NUM_TAPS; i++) {
      if (i == attack_tap_) continue;
      if (gain_[i] > 0.0f) { others_silent = false; break; }
    }
    if (others_silent) {
      active_tap_ = attack_tap_;
      attack_tap_ = -1;
      mode_       = MODE_LOOP_ONLY;
    }
  }

  // 4. Attack impulse (priority — but only while not already responding)
  if (attack_impulse > 0.5f && mode_ == MODE_LOOP_ONLY) {
    start_attack_response();
    attack_event = 1.0f;
  }

  // 5. Record incoming ZC impulse
  if (zc_impulse > 0.5f) {
    add_zc_record(sample_index_);
  }

  // 6. Loop check (LOOP_ONLY only). Same algorithm as the 2-tap version,
  //    just operating on active_tap_ ∈ {0,1,2} and firing onto a free tap.
  if (mode_ == MODE_LOOP_ONLY) {
    float AT_out = (float)sample_index_ - tap_delay_[active_tap_];

    while (zc_count_ > 0) {
      int32_t head_at;
      peek_oldest(head_at);
      if (AT_out < (float)head_at) break;     // not yet reached this ZC

      if (in_loop_crossfade_) {
        // Mid loop crossfade — can't fire again; just discard.
        pop_oldest();
        continue;
      }

      float DT_active = tap_delay_[active_tap_];

      bool fired = false;
      if (DT_active > lower_threshold_ && zc_count_ >= 2) {
        bool  gate_active = (qualified > 0.5f) && (P_samples > 1.0f);
        float margin      = 0.0f;
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

        int   head_idx     = (zc_head_ - zc_count_ + ZC_HISTORY_SIZE) % ZC_HISTORY_SIZE;
        int   fallback_i   = -1;
        int   match_i      = -1;
        float fb_inactive  = 0.0f, match_inactive = 0.0f;
        for (int i = zc_count_ - 1; i > 0; i--) {
          int     idx          = (head_idx + i) % ZC_HISTORY_SIZE;
          int32_t at_new       = zc_history_[idx];
          float   delta_samples = (float)(at_new - head_at);
          float   new_inactive  = DT_active - delta_samples;
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
          break;
        }

        int   fire_i        = (match_i >= 0) ? match_i        : fallback_i;
        float fire_inactive = (match_i >= 0) ? match_inactive : fb_inactive;
        if (fire_i >= 0) {
          start_loop_crossfade(fire_inactive, loop_cf_samples_);
          loop_event = 1.0f;
          if (gate_active && match_i >= 0 && match_i != fallback_i) {
            gated_event = 1.0f;
          }
          pop_oldest();
          fired = true;
        }
        if (fired) break;
      }

      pop_oldest();
    }

    // 7. Bailout — per-sample, regardless of input ZC.
    if (!in_loop_crossfade_ && tap_delay_[active_tap_] > upper_threshold_) {
      start_loop_crossfade(MIN_DELAY_SAMPLES, bailout_cf_samples_);
      flush_zc_history();
      bailout_event = 1.0f;
    }
  }

  // 8. Write outputs
  float ms_per_sample = 1000.0f / sample_rate_;
  tap1_delay_ms  = tap_delay_[0] * ms_per_sample;
  tap2_delay_ms  = tap_delay_[1] * ms_per_sample;
  tap3_delay_ms  = tap_delay_[2] * ms_per_sample;
  gain1          = gain_[0];
  gain2          = gain_[1];
  gain3          = gain_[2];
  latency_ms     = tap_delay_[active_tap_] * ms_per_sample;
  active_tap_out = (float)active_tap_;
}

// ============================================================
// Ring buffer helpers
// ============================================================

void loop_controller::add_zc_record(int32_t at) {
  zc_history_[zc_head_] = at;
  zc_head_              = (zc_head_ + 1) % ZC_HISTORY_SIZE;
  if (zc_count_ < ZC_HISTORY_SIZE) zc_count_++;
}

void loop_controller::pop_oldest() {
  if (zc_count_ > 0) zc_count_--;
}

void loop_controller::flush_zc_history() {
  zc_head_  = 0;
  zc_count_ = 0;
}

bool loop_controller::peek_oldest(int32_t& out) const {
  if (zc_count_ == 0) return false;
  int idx = (zc_head_ - zc_count_ + ZC_HISTORY_SIZE) % ZC_HISTORY_SIZE;
  out = zc_history_[idx];
  return true;
}

// ============================================================
// Parameters
// ============================================================

void loop_controller::set_param(const char* name, float value) {
  if (!strcmp(name, "pitch_ratio")) {
    set_pitch_ratio(value);
  }
}

float loop_controller::get_param(const char* name) const {
  if (!strcmp(name, "pitch_ratio")) return pitch_ratio_;
  return 0.0f;
}

#ifndef BARE_METAL
vector<string> loop_controller::get_param_names() const {
  return {"pitch_ratio"};
}
#endif
