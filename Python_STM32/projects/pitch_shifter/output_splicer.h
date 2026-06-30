#pragma once
#ifndef BARE_METAL
#include <vector>
#include <string>
using std::vector;
using std::string;
#endif

// output_splicer — dry/wet crossfade on the output, driven by the attack
// detector's two events. The unprocessed (dry) signal is made live on a note
// end (the dive detector) and on an attack; in both cases the output blends
// back to the shifted (wet) signal. Doc: output_splicer.md.
//
//   out = dry * m + wet * (1 - m),   m in [0,1]  (1 = dry live, 0 = full wet)
//
// m = max(e_attack, e_noteend), two independent envelopes that don't fight:
//   e_attack  — snaps live on an attack edge (fast ATTACK_RISE_MS ramp to 1),
//               then crossfades back to wet over attack_to_wet_ms. Sharpens the
//               attack transient by letting the natural pluck through; it does
//               NOT mask the YIN/loop latency — with a longer crossfade the
//               shifted note is audibly arriving underneath the dry tail.
//   e_noteend — slews toward dive_strength at note_end_fade_ms; reveals the
//               natural dry decay as a note dies.
// During the pluck dive is low so e_attack dominates; as the note dies e_attack
// is long gone so e_noteend dominates; mid-sustain both ~0 → full wet.

class output_splicer {
public:
  // Fast rise to full-dry on an attack edge — short enough to keep the natural
  // transient, long enough to avoid a coefficient-jump click.
  static constexpr float ATTACK_RISE_MS = 1.0f;

  output_splicer();

  void init(int sample_rate);

  int get_num_inputs()  const { return 4; }   // dry, wet, attack_trigger, dive_strength
  int get_num_outputs() const { return 2; }   // out, dry_mix
  int get_sample_rate() const { return (int)sample_rate_; }

  void process(const float* const* inputs, float* const* outputs, int n);

  void set_param(const char* name, float value);
  float get_param(const char* name) const;
#ifndef BARE_METAL
  vector<string> get_param_names() const;
#endif

private:
  // Attack envelope phase.
  enum atk_phase_t {
    ATK_IDLE   = 0,
    ATK_RISING = 1,   // ramping up to full dry
    ATK_FALLING = 2,  // crossfading back to wet
  };

  void update_derived_constants();

  float sample_rate_;

  // Params (ms) + derived per-sample rates.
  float attack_to_wet_ms_;
  float note_end_fade_ms_;
  float attack_rise_rate_;     // per-sample step, 0->1 over ATTACK_RISE_MS
  float attack_fall_rate_;     // per-sample step, 1->0 over attack_to_wet_ms
  float note_end_rate_;        // per-sample slew cap toward dive_strength

  // Attack envelope state.
  atk_phase_t atk_phase_;
  float e_attack_;

  // Note-end envelope state.
  float e_noteend_;

  // Rising-edge detection on the attack impulse.
  float prev_trigger_;
};
