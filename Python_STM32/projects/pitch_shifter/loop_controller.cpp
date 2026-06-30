/* @block
(define-block loop_controller
 (inputs attack_impulse P_samples aperiodicity active_gain)
 (outputs tap1_delay_ms tap2_delay_ms tap3_delay_ms
          gain1 gain2 gain3
          latency_ms loop_event active_tap bailout_event gated_event attack_event
          active_gain_mean)
 (params (pitch_ratio :default 0.5)))
*/

#include "loop_controller.h"
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

  P_latched_           = 0.0f;
  have_P_              = false;
  loop_lockout_counter_ = 0;

  for (int i = 0; i < MEAN_MAX_SAMPLES; i++) ag_ring_[i] = 1.0f;
  ag_mean_w_      = 0;
  ag_mean_len_    = 1;
  ag_mean_stored_ = 0;
  ag_mean_sum_    = 0.0;

  set_pitch_ratio(pitch_ratio_);
}

void loop_controller::set_pitch_ratio(float ratio) {
  pitch_ratio_ = std::max(0.1f, std::min(ratio, 0.99f));
  dd_          = 1.0f - pitch_ratio_;
  update_derived_constants();
}

void loop_controller::update_derived_constants() {
  lower_threshold_        = LOWER_THRESHOLD_MS * sample_rate_ / 1000.0f;
  upper_threshold_        = UPPER_THRESHOLD_MS * sample_rate_ / 1000.0f;
  loop_cf_samples_        = (int)(LOOP_CROSSFADE_MS   * sample_rate_ / 1000.0f);
  attack_fadein_samples_  = (int)(ATTACK_FADEIN_MS    * sample_rate_ / 1000.0f);
  attack_fadeout_samples_ = (int)(ATTACK_FADEOUT_MS   * sample_rate_ / 1000.0f);
  bailout_cf_samples_     = (int)(LOOP_CROSSFADE_MS * BAILOUT_CROSSFADE_MULT * sample_rate_ / 1000.0f);
  loop_lockout_samples_   = (int)(LOOP_LOCKOUT_MS     * sample_rate_ / 1000.0f);

  if (loop_cf_samples_        < 1) loop_cf_samples_        = 1;
  if (attack_fadein_samples_  < 1) attack_fadein_samples_  = 1;
  if (attack_fadeout_samples_ < 1) attack_fadeout_samples_ = 1;
  if (bailout_cf_samples_     < 1) bailout_cf_samples_     = 1;
  if (loop_lockout_samples_   < 1) loop_lockout_samples_   = 1;
}

// ============================================================
// process() — buffer loop, calls compute() per sample
// ============================================================

void loop_controller::process(const float* const* inputs, float* const* outputs, int n) {
  for (int i = 0; i < n; i++) {
    Probes p { outputs[6][i], outputs[7][i], outputs[8][i],     // latency_ms, loop_event, active_tap
               outputs[9][i], outputs[10][i], outputs[11][i] }; // bailout_event, gated_event, attack_event
    compute(inputs[0][i], inputs[1][i], inputs[2][i],           // attack_impulse, P_samples, aperiodicity
            outputs[0][i], outputs[1][i], outputs[2][i],        // tapN_delay_ms
            outputs[3][i], outputs[4][i], outputs[5][i],        // gainN
            p);

    // Loop-tap gating: multiply every NON-attack tap's gain by active_gain so
    // buffer-bleed has no audible path during silence / the attack crossfade.
    // The attack tap must carry the new transient at full level, so it is NOT
    // gated — otherwise active_gain (still recovering from the prior note-end)
    // drags its 1 ms fade-in out to ~10 ms. Gate by ROLE, not a fixed index:
    // pick_free_tap can place the attack tap on any of {0,1,2}, so gain1/gain2
    // is the wrong thing to key on (attack_tap_ == -1 in LOOP_ONLY → all gated).
    //
    // Use the period-synchronous MEAN of active_gain, not the raw sample: on low
    // notes active_gain ripples at the fundamental, which would amplitude-
    // modulate the looped taps. The one-period running mean nulls that ripple.
    const float gate = active_gain_mean(inputs[3][i]);
    for (int tap = 0; tap < NUM_TAPS; tap++) {
      if (tap == attack_tap_) continue;
      outputs[3 + tap][i] *= gate;          // outputs[3..5] = gain1..gain3
    }
    outputs[12][i] = gate;                   // probe: smoothed gate
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
// active_gain_mean() — running mean of active_gain over one period (≈round P).
// A boxcar of length P is a comb that nulls the per-period gate ripple (f0 and
// harmonics) while passing the slow note-end envelope. O(1) per sample via a
// running sum; rebuilds only when the window length changes (rare — held notes
// have a stable P, and a 2-sample hysteresis absorbs round(P) jitter).
// ============================================================

float loop_controller::active_gain_mean(float active_gain) {
  // Target window = one period when a confident P is in hand; hold otherwise.
  int L = ag_mean_len_;
  if (have_P_) {
    int target = (int)(P_latched_ + 0.5f);
    if (target < 1)                 target = 1;
    if (target > MEAN_MAX_SAMPLES)  target = MEAN_MAX_SAMPLES;
    if (target > ag_mean_len_ + 1 || target < ag_mean_len_ - 1) L = target;
  }

  // Write newest sample into the ring.
  ag_ring_[ag_mean_w_] = active_gain;
  int w = ag_mean_w_;
  ag_mean_w_ = (ag_mean_w_ + 1) % MEAN_MAX_SAMPLES;
  if (ag_mean_stored_ < MEAN_MAX_SAMPLES) ag_mean_stored_++;

  int eff = (L < ag_mean_stored_) ? L : ag_mean_stored_;   // window capped by history

  if (L != ag_mean_len_) {
    // Window length changed: rebuild the sum over the newest `eff` samples.
    double s = 0.0;
    for (int k = 0; k < eff; k++) {
      int idx = w - k; if (idx < 0) idx += MEAN_MAX_SAMPLES;
      s += ag_ring_[idx];
    }
    ag_mean_sum_ = s;
    ag_mean_len_ = L;
  } else {
    // Same length: add the newest, drop the sample that fell out of the window.
    ag_mean_sum_ += active_gain;
    if (ag_mean_stored_ > eff) {
      int idx = w - eff; if (idx < 0) idx += MEAN_MAX_SAMPLES;
      ag_mean_sum_ -= ag_ring_[idx];
    }
  }
  return (float)(ag_mean_sum_ / (double)eff);
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

  // New note: the previous note's period is meaningless now, and YIN needs
  // ~one window (~50 ms) to converge. Disengage looping until a fresh confident
  // P arrives; the attack tap (fast fade-in) carries the onset meanwhile.
  have_P_               = false;
  loop_lockout_counter_ = 0;
}

// ============================================================
// compute() — per-sample logic
//
// Order:
//   1. Advance sample counter + lockout countdown.
//   2. Advance per-tap delay ramp + gain ramp (one sample).
//   3. Resolve role transitions on fade completion.
//   4. Attack impulse (only in LOOP_ONLY) — engage attack tap.
//   5. Latch P while confident.
//   6. Loop check (only in LOOP_ONLY): k=1 jump by P, gated by lockout.
//   7. Bailout (only in LOOP_ONLY).
//   8. Write outputs.
// ============================================================

void loop_controller::compute(float attack_impulse, float P_samples, float aperiodicity,
                              float& tap1_delay_ms, float& tap2_delay_ms, float& tap3_delay_ms,
                              float& gain1, float& gain2, float& gain3,
                              Probes& p) {
  p.loop_event    = 0.0f;
  p.bailout_event = 0.0f;
  p.gated_event   = 0.0f;
  p.attack_event  = 0.0f;

  // 1. Advance sample counter + lockout
  sample_index_++;
  if (loop_lockout_counter_ > 0) loop_lockout_counter_--;

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
    p.attack_event = 1.0f;
  }

  // 5. Latch P while YIN is confident (low aperiodicity). Hold the last good P
  //    through brief dips so a transient un-confidence doesn't drop the loop.
  if (aperiodicity <= APERIODICITY_THRESH && P_samples > 2.0f * MIN_DELAY_SAMPLES) {
    P_latched_ = P_samples;
    have_P_    = true;
  }

  // 6. Loop check (LOOP_ONLY only). Once latency passes the operating point and
  //    a confident P is in hand, jump the read back by exactly one period (k=1).
  //    Phase is preserved by periodicity, so no peak/splice point is needed —
  //    only the jump length ≈ P. Lockout (absolute settle time) paces re-fires.
  if (mode_ == MODE_LOOP_ONLY && !in_loop_crossfade_) {
    float DT = tap_delay_[active_tap_];
    if (DT > lower_threshold_) {
      bool ready = have_P_ && loop_lockout_counter_ == 0;
      float new_inactive = DT - P_latched_;
      if (ready && new_inactive >= MIN_DELAY_SAMPLES) {
        start_loop_crossfade(new_inactive, loop_cf_samples_);
        loop_lockout_counter_ = loop_lockout_samples_;
        p.loop_event = 1.0f;
      } else {
        // Wanted to loop but couldn't: no confident P yet, still in lockout, or
        // less than one period of headroom above MIN_DELAY. Hold — bailout is
        // the safety if latency keeps climbing.
        p.gated_event = 1.0f;
      }
    }

    // 7. Bailout — per-sample safety, independent of P.
    if (!in_loop_crossfade_ && tap_delay_[active_tap_] > upper_threshold_) {
      start_loop_crossfade(MIN_DELAY_SAMPLES, bailout_cf_samples_);
      loop_lockout_counter_ = loop_lockout_samples_;
      p.bailout_event = 1.0f;
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
  p.latency_ms   = tap_delay_[active_tap_] * ms_per_sample;
  p.active_tap   = (float)active_tap_;
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
