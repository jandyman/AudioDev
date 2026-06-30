/* @block
(define-block output_splicer
 (inputs dry wet attack_trigger dive_strength)
 (outputs out dry_mix)
 (params (attack_to_wet_ms :default 50.0)
         (note_end_fade_ms :default 50.0)))
*/

#include "output_splicer.h"
#include <cstring>
#include <algorithm>

// ============================================================
// Constructor / init
// ============================================================

output_splicer::output_splicer() {
  memset(this, 0, sizeof(*this));
  attack_to_wet_ms_ = 50.0f;
  note_end_fade_ms_ = 50.0f;
  atk_phase_        = ATK_IDLE;
}

void output_splicer::init(int sample_rate) {
  sample_rate_      = (float)sample_rate;
  atk_phase_        = ATK_IDLE;
  e_attack_         = 0.0f;
  note_end_latched_ = false;
  e_noteend_        = 0.0f;
  prev_trigger_     = 0.0f;
  prev_dive_        = 0.0f;
  update_derived_constants();
}

void output_splicer::update_derived_constants() {
  // step = 1 / duration_samples; guard against sub-sample durations.
  float rise_samples    = std::max(1.0f, ATTACK_RISE_MS    * sample_rate_ / 1000.0f);
  float fall_samples    = std::max(1.0f, attack_to_wet_ms_ * sample_rate_ / 1000.0f);
  float noteend_samples = std::max(1.0f, note_end_fade_ms_ * sample_rate_ / 1000.0f);
  attack_rise_rate_ = 1.0f / rise_samples;
  attack_fall_rate_ = 1.0f / fall_samples;
  note_end_rate_    = 1.0f / noteend_samples;
}

// ============================================================
// process() — per-sample dry/wet blend
// ============================================================

void output_splicer::process(const float* const* inputs, float* const* outputs, int n) {
  const float* dry     = inputs[0];
  const float* wet     = inputs[1];
  const float* trigger = inputs[2];
  const float* dive    = inputs[3];
        float* out     = outputs[0];
        float* dry_mix = outputs[1];

  for (int i = 0; i < n; i++) {
    // Attack edge: re-arm the fast rise to full dry and clear the note-end
    // latch. Hand the latch's current dry level to e_attack so there is no dip
    // and the crossfade back to wet is governed solely by attack_to_wet_ms.
    if (trigger[i] > 0.5f && prev_trigger_ <= 0.5f) {
      e_attack_         = std::max(e_attack_, e_noteend_);
      atk_phase_        = ATK_RISING;
      note_end_latched_ = false;
      e_noteend_        = 0.0f;
    }
    prev_trigger_ = trigger[i];

    if (atk_phase_ == ATK_RISING) {
      e_attack_ += attack_rise_rate_;
      if (e_attack_ >= 1.0f) { e_attack_ = 1.0f; atk_phase_ = ATK_FALLING; }
    } else if (atk_phase_ == ATK_FALLING) {
      e_attack_ -= attack_fall_rate_;
      if (e_attack_ <= 0.0f) { e_attack_ = 0.0f; atk_phase_ = ATK_IDLE; }
    }

    // Note-end: latch on a rising edge of dive_strength past the threshold (a
    // discrete event — held until the next attack clears it). e_noteend ramps
    // toward full dry while latched, back toward wet once cleared.
    if (dive[i] > NOTE_END_THRESH && prev_dive_ <= NOTE_END_THRESH) note_end_latched_ = true;
    prev_dive_ = dive[i];

    float ne_target = note_end_latched_ ? 1.0f : 0.0f;
    if (ne_target > e_noteend_) e_noteend_ = std::min(ne_target, e_noteend_ + note_end_rate_);
    else                        e_noteend_ = std::max(ne_target, e_noteend_ - note_end_rate_);

    float m = std::max(e_attack_, e_noteend_);
    out[i]     = dry[i] * m + wet[i] * (1.0f - m);
    dry_mix[i] = m;
  }
}

// ============================================================
// Parameters
// ============================================================

void output_splicer::set_param(const char* name, float value) {
  if (!strcmp(name, "attack_to_wet_ms")) {
    attack_to_wet_ms_ = std::max(1.0f, value);
    update_derived_constants();
  } else if (!strcmp(name, "note_end_fade_ms")) {
    note_end_fade_ms_ = std::max(1.0f, value);
    update_derived_constants();
  }
}

float output_splicer::get_param(const char* name) const {
  if (!strcmp(name, "attack_to_wet_ms")) return attack_to_wet_ms_;
  if (!strcmp(name, "note_end_fade_ms")) return note_end_fade_ms_;
  return 0.0f;
}

#ifndef BARE_METAL
vector<string> output_splicer::get_param_names() const {
  return {"attack_to_wet_ms", "note_end_fade_ms"};
}
#endif
