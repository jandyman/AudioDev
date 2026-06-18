#pragma once
#include <cstdint>
#ifndef BARE_METAL
#include <vector>
#include <string>
using std::vector;
using std::string;
#endif

// loop_controller — pitch-shift loop-point detection + crossfade management.
// Three-tap variant: owns all delay ramps and tap gains, turning ZC + attack
// impulses (and the pitch detector's period estimate) into the three tap
// delays and crossfade gains for the triple tap delay. No dynamic allocation in
// process(). Design, tap roles, and the active_gain gate: loop_controller.md.

class loop_controller {
public:
  // ------------------------------------------------------------------
  // Constants
  // ------------------------------------------------------------------

  static const int NUM_TAPS = 3;

  // ZC ring buffer size. Worst case: 200 ms / 3.2 ms ≈ 63 records.
  static const int ZC_HISTORY_SIZE = 128;

  // Latency thresholds. Lower = earliest a loop may fire (operating point, since
  // per-cycle loops keep latency hovering just above it); upper = bailout ceiling
  // (decoupled safety, rarely reached). Lower latency = fresher looped material =
  // less timbral modulation on an evolving note. See loop_controller.md.
  static constexpr float LOWER_THRESHOLD_MS = 50.0f;
  static constexpr float UPPER_THRESHOLD_MS = 200.0f;

  // Minimum delay after any tap reset (avoids zero-delay artifacts)
  static constexpr float MIN_DELAY_SAMPLES = 4.0f;

  // Crossfade durations
  static constexpr float LOOP_CROSSFADE_MS      = 5.0f;   // relaxed
  static constexpr float ATTACK_FADEIN_MS       = 1.0f;   // short — preserve transient
  static constexpr float ATTACK_FADEOUT_MS      = 10.0f;  // slow tail-out of previous note
  static constexpr float BAILOUT_CROSSFADE_MULT = 3.0f;   // bailout = 3× loop crossfade

  // Integer-multiple candidate gate (see concept doc, Harmonic Rejection +
  // Urgency and relaxed matching). Base margin = max(MARGIN_FRAC_P * P, sigma);
  // multiplied by an urgency factor scaling from 1 at the lower threshold to
  // URGENCY_MAX_MULT at the upper threshold.
  static constexpr float MARGIN_FRAC_P     = 0.05f;
  static constexpr float URGENCY_MAX_MULT  = 3.0f;

  // Absolute floor on the gate margin (ms). The ZC stream jitters by a roughly
  // CONSTANT absolute amount (~1 ms, set by the waveform/LPF, not the period).
  // A purely fractional margin (MARGIN_FRAC_P * P) shrinks below that jitter on
  // short high-note periods (e.g. ~0.38 ms on a 131 Hz note), so the correct
  // one-period (k=1) candidate keeps failing and the nearest-first scan leaps to
  // a far, coincidentally-aligned ZC — the erratic high-note loop points. Flooring
  // the margin in absolute time keeps k=1 choosable regardless of pitch. We always
  // splice on a real ZC, so value-continuity holds; the floor only governs which
  // k is accepted. Sized from the measured ~1 ms C3 jitter. See loop_controller.md.
  static constexpr float MARGIN_FLOOR_MS   = 1.5f;

  // ------------------------------------------------------------------
  // Public interface
  // ------------------------------------------------------------------
  loop_controller();

  void init(int sample_rate);
  void set_pitch_ratio(float ratio);
  float get_pitch_ratio() const { return pitch_ratio_; }

  int get_num_inputs()  const { return 6; }
  int get_num_outputs() const { return 12; }
  int get_sample_rate() const { return (int)sample_rate_; }

  void process(const float* const* inputs, float* const* outputs, int n);

  void set_param(const char* name, float value);
  float get_param(const char* name) const;
#ifndef BARE_METAL
  vector<string> get_param_names() const;
#endif

private:
  // ------------------------------------------------------------------
  // Mode (attack-response state machine)
  // ------------------------------------------------------------------
  enum mode_t {
    MODE_LOOP_ONLY      = 0,
    MODE_ATTACK_FADEIN  = 1,
    MODE_ATTACK_FADEOUT = 2,
  };

  // ------------------------------------------------------------------
  // Per-sample compute (called by process())
  // ------------------------------------------------------------------

  // Diagnostic-only outputs. None are wired downstream in the graph (see
  // pitch_shifter.graph) — they exist purely as probe taps for Python plots.
  // Grouped here to keep compute()'s signature legible; each member is a
  // reference bound to the corresponding output buffer slot in process().
  struct Probes {
    float& latency_ms;
    float& loop_event;
    float& active_tap;
    float& bailout_event;
    float& gated_event;
    float& attack_event;
  };

  void compute(float zc_impulse, float attack_impulse,
               float P_samples, float sigma_samples, float qualified,
               float& tap1_delay_ms, float& tap2_delay_ms, float& tap3_delay_ms,
               float& gain1, float& gain2, float& gain3,
               Probes& p);

  // ------------------------------------------------------------------
  // Internal state — all statically declared
  // ------------------------------------------------------------------

  float sample_rate_;
  float pitch_ratio_;
  float dd_;                          // delay delta per sample = 1 - pitch_ratio

  // Per-tap state. Roles (active / loop_incoming / attack) attach to indices
  // via active_tap_, loop_incoming_tap_, attack_tap_ below.
  float tap_delay_[NUM_TAPS];         // delay in samples
  bool  live_[NUM_TAPS];              // delay ramps with dd_ when live; parked otherwise
  float gain_[NUM_TAPS];              // current gain (per-sample)
  float gain_target_[NUM_TAPS];       // 0.0 or 1.0
  float gain_rate_[NUM_TAPS];         // per-sample gain step magnitude

  // Role indices. -1 means "no tap currently holds this role".
  int active_tap_;                    // {0,1,2}
  int loop_incoming_tap_;             // {0,1,2,-1}; valid iff in_loop_crossfade_
  int attack_tap_;                    // {0,1,2,-1}; valid iff mode_ != LOOP_ONLY
  bool in_loop_crossfade_;

  mode_t mode_;

  // ZC ring buffer: absolute sample-index of each qualified zero crossing.
  int32_t zc_history_[ZC_HISTORY_SIZE];
  int     zc_head_;                   // next write position
  int     zc_count_;                  // number of valid entries

  // Sample counter (absolute, since init)
  int32_t sample_index_;

  // Derived constants (recomputed in set_pitch_ratio / init)
  float lower_threshold_;             // samples
  float upper_threshold_;             // samples
  float margin_floor_samples_;        // absolute gate-margin floor (samples)
  int   loop_cf_samples_;
  int   attack_fadein_samples_;
  int   attack_fadeout_samples_;
  int   bailout_cf_samples_;

  // ------------------------------------------------------------------
  // Helpers
  // ------------------------------------------------------------------
  void add_zc_record(int32_t at);
  void pop_oldest();
  void flush_zc_history();
  bool peek_oldest(int32_t& out) const;
  void update_derived_constants();

  // Advance per-tap delay/gain one sample. Parks taps that reach gain=0.
  void advance_tap_state();

  // Pick the lowest-index tap not currently bound to a role. `exclude_loop_incoming`
  // controls whether to exclude loop_incoming_tap_ (true for picking an attack tap
  // during an in-progress loop crossfade).
  int  pick_free_tap(bool exclude_loop_incoming) const;

  // Begin a loop crossfade from active_tap_ to a chosen free tap, with the
  // inactive tap's delay pre-set (loop) or overridden to MIN_DELAY (bailout).
  // `inactive_delay` is in samples and is set on the chosen tap. Duration is
  // in samples.
  void start_loop_crossfade(float inactive_delay, int cf_samples);

  // Begin attack response: pick a free tap, set MIN_DELAY, start fast fade-in.
  void start_attack_response();
};
