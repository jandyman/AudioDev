#pragma once
#include <cstdint>
#ifndef BARE_METAL
#include <vector>
#include <string>
using std::vector;
using std::string;
#endif

// loop_controller — pitch-shift loop-point detection + crossfade management.
// Three-tap variant: owns all delay ramps and tap gains, turning a precise
// period estimate P (from the YIN detector) + the attack impulse into the three
// tap delays and crossfade gains for the triple tap delay. No dynamic allocation
// in process(). Design, tap roles, and the active_gain gate: loop_controller.md.
//
// Loop policy (YIN-driven): the active tap's delay IS the latency; it grows by
// dd_ = 1 - pitch_ratio each sample. When latency exceeds the operating point
// and a confident P is in hand, jump the read back by exactly k*P (k = 1) — a
// jump of an integer number of periods is phase-matched by periodicity, so loop
// POINT no longer matters, only that the jump length ≈ P. A fixed lockout (an
// absolute time ≥ crossfade + settle, independent of P) prevents re-looping
// before the last crossfade has settled.

class loop_controller {
public:
  // ------------------------------------------------------------------
  // Constants
  // ------------------------------------------------------------------

  static const int NUM_TAPS = 3;

  // Latency thresholds. Lower = operating point (earliest a loop may fire;
  // per-cycle k=1 loops keep latency hovering just above it); upper = bailout
  // ceiling (decoupled safety, rarely reached). Lower latency = fresher looped
  // material = less timbral modulation on an evolving note. See loop_controller.md.
  static constexpr float LOWER_THRESHOLD_MS = 50.0f;
  static constexpr float UPPER_THRESHOLD_MS = 200.0f;

  // Minimum delay after any tap reset (avoids zero-delay artifacts)
  static constexpr float MIN_DELAY_SAMPLES = 4.0f;

  // Crossfade durations
  static constexpr float LOOP_CROSSFADE_MS      = 5.0f;   // relaxed
  static constexpr float ATTACK_FADEIN_MS       = 1.0f;   // short — preserve transient
  static constexpr float ATTACK_FADEOUT_MS      = 10.0f;  // slow tail-out of previous note
  static constexpr float BAILOUT_CROSSFADE_MULT = 3.0f;   // bailout = 3× loop crossfade

  // Loop lockout: minimum time between loop fires. Absolute (crossfade + settle
  // margin), NOT a multiple of P — the jump length must be ≈ P, but the settle
  // time has nothing to do with the period.
  static constexpr float LOOP_LOCKOUT_MS = 7.0f;

  // Gate smoothing: the per-tap active_gain gate is ramped, not applied as a hard
  // per-sample multiply. Without this, promoting the (gate-exempt) attack tap to
  // the active role steps its gain from 1.0 straight to the gate value in one
  // sample — an audible click. The ramp turns that into a short glide.
  static constexpr float GATE_SMOOTH_MS = 10.0f;

  // Confidence gate: accept/latch P only when YIN is confident. The detector
  // emits aperiodicity (d' at the dip); low = confident. Latch P while
  // aperiodicity <= this, hold the last good P through brief dips.
  static constexpr float APERIODICITY_THRESH = 0.40f;

  // Period-synchronous mean of active_gain (the wet-tap gate). active_gain
  // ripples at the note fundamental on low notes; a running mean over exactly
  // one period P is a comb that nulls f0 and all its harmonics, removing the
  // gate ripple while passing the slow note-end envelope (~P/2 group delay).
  // Ring sized for the longest expected period: ~23 Hz at 48 kHz (low notes
  // below the bass range never occur; if P exceeds this the window is clamped,
  // giving partial rejection). Tied to sample_rate only through the index.
  static const int MEAN_MAX_SAMPLES = 2048;

  // ------------------------------------------------------------------
  // Public interface
  // ------------------------------------------------------------------
  loop_controller();

  void init(int sample_rate);
  void set_pitch_ratio(float ratio);
  float get_pitch_ratio() const { return pitch_ratio_; }

  int get_num_inputs()  const { return 4; }
  int get_num_outputs() const { return 13; }
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
    float& gated_event;     // loop wanted (latency over threshold) but suppressed
    float& attack_event;
  };

  void compute(float attack_impulse, float P_samples, float aperiodicity,
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
  float tap_gate_[NUM_TAPS];          // smoothed active_gain gate applied per tap

  // Role indices. -1 means "no tap currently holds this role".
  int active_tap_;                    // {0,1,2}
  int loop_incoming_tap_;             // {0,1,2,-1}; valid iff in_loop_crossfade_
  int attack_tap_;                    // {0,1,2,-1}; valid iff mode_ != LOOP_ONLY
  bool in_loop_crossfade_;

  mode_t mode_;

  // Latched period (full-rate samples) + validity. Updated from P_samples while
  // confident; held through brief confidence dips. Invalidated on attack so a
  // new note doesn't loop on the previous note's period before YIN re-converges.
  float P_latched_;
  bool  have_P_;

  // Loop lockout countdown (samples). Loops may fire only when this hits 0.
  int   loop_lockout_counter_;

  // Period-synchronous running mean of active_gain. Ring of recent samples +
  // running sum over a window of ag_mean_len_ (≈ round(P)). See active_gain_mean().
  float  ag_ring_[MEAN_MAX_SAMPLES];
  int    ag_mean_w_;            // ring write index
  int    ag_mean_len_;          // current window length (samples)
  int    ag_mean_stored_;       // valid history depth (warmup)
  double ag_mean_sum_;          // running sum over the current window

  // Sample counter (absolute, since init)
  int32_t sample_index_;

  // Derived constants (recomputed in set_pitch_ratio / init)
  float lower_threshold_;             // samples
  float upper_threshold_;             // samples
  int   loop_cf_samples_;
  int   attack_fadein_samples_;
  int   attack_fadeout_samples_;
  int   bailout_cf_samples_;
  int   loop_lockout_samples_;
  float gate_smooth_rate_;            // per-sample step for the tap-gate ramp

  // ------------------------------------------------------------------
  // Helpers
  // ------------------------------------------------------------------
  void update_derived_constants();

  // Advance per-tap delay/gain one sample. Parks taps that reach gain=0.
  void advance_tap_state();

  // Push one active_gain sample and return its running mean over a window of
  // ≈ round(P_latched_) samples (one period). Nulls the per-period ripple.
  float active_gain_mean(float active_gain);

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
