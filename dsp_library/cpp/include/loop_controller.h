#pragma once
#include <vector>
#include <string>
#include <cstdint>

using std::vector;
using std::string;

// LoopController — Pitch Shift Loop Point Detection and Crossfade Management
//
// Owns the delay ramp for both taps. Receives ZC impulses from the ZC Detector
// and attack impulses from the Attack Detector, and outputs the delay times and
// crossfade gains for the Dual Tap Delay.
//
// Algorithm: output-side detection (see Pitch Shifter concept.md).
//   - Input ZCs are recorded into a ring buffer as absolute sample-index ATs.
//   - On every output sample, AT_out = sample_index - DT_active is compared
//     against the head of the ring buffer. When AT_out reaches head.AT, we
//     are emitting that zero crossing and may fire a loop transition.
//   - Bailout runs per-sample (not gated on input ZC arrival), so the active
//     delay can never grow unboundedly past the upper threshold.
//
// No dynamic memory allocation in process(). All state is statically declared.
//
// Inputs  (5): zc_impulse, attack_impulse,
//              P_samples, sigma_samples, qualified
//              (the last three come from HarmonicRejector; when qualified < 0.5
//              or P_samples <= 0, the integer-multiple gate is disabled and
//              candidate selection falls back to "newest DT-valid".)
// Outputs (9): tap1_delay_ms, tap2_delay_ms, gain1, gain2,
//              latency_ms (probe), loop_event (probe),
//              active_tap (probe), bailout_event (probe),
//              gated_event (probe; 1 when integer-multiple gate caused us
//              to pick something other than newest DT-valid)
//
// Parameters: pitch_ratio (adjustable at runtime; flushes ZC history on change)

class LoopController {
public:
    // ------------------------------------------------------------------
    // Constants
    // ------------------------------------------------------------------

    // ZC ring buffer size. Worst case: 200 ms / 3.2 ms ≈ 63 records.
    static const int ZC_HISTORY_SIZE = 128;

    // Latency thresholds
    static constexpr float LOWER_THRESHOLD_MS = 60.0f;
    static constexpr float UPPER_THRESHOLD_MS = 200.0f;

    // Minimum delay after any tap reset (avoids zero-delay artifacts)
    static constexpr float MIN_DELAY_SAMPLES = 4.0f;

    // Crossfade durations
    static constexpr float LOOP_CROSSFADE_MS      = 5.0f;   // relaxed
    static constexpr float ATTACK_FADEIN_MS        = 1.0f;   // short — preserve transient
    static constexpr float BAILOUT_CROSSFADE_MULT  = 3.0f;   // bailout = 3× loop crossfade

    // Integer-multiple candidate gate (see concept doc, Harmonic Rejection +
    // Urgency and relaxed matching). Base margin = max(MARGIN_FRAC_P * P, sigma);
    // multiplied by an urgency factor scaling from 1 at the lower threshold to
    // URGENCY_MAX_MULT at the upper threshold.
    static constexpr float MARGIN_FRAC_P     = 0.05f;
    static constexpr float URGENCY_MAX_MULT  = 3.0f;

    // ------------------------------------------------------------------
    // Public interface
    // ------------------------------------------------------------------
    LoopController();

    void init(int sample_rate);
    void set_pitch_ratio(float ratio);
    float get_pitch_ratio() const { return pitch_ratio_; }

    int get_num_inputs()  const { return 5; }
    int get_num_outputs() const { return 9; }
    int get_sample_rate() const { return (int)sample_rate_; }

    void process(const vector<vector<float>>& inputs,
                       vector<vector<float>>& outputs);

    void set_param(const string& name, float value);
    float get_param(const string& name) const;
    vector<string> get_param_names() const;

private:
    // ------------------------------------------------------------------
    // Per-sample compute (called by process())
    // ------------------------------------------------------------------
    void compute(float zc_impulse, float attack_impulse,
                 float P_samples, float sigma_samples, float qualified,
                 float& tap1_delay_ms, float& tap2_delay_ms,
                 float& gain1, float& gain2,
                 float& latency_ms, float& loop_event,
                 float& active_tap_out, float& bailout_event,
                 float& gated_event);

    // ------------------------------------------------------------------
    // Internal state — all statically declared
    // ------------------------------------------------------------------

    float   sample_rate_;
    float   pitch_ratio_;
    float   dd_;                    // delay delta per sample = 1 - pitch_ratio

    // Tap delays in samples. The active tap always ramps; the inactive tap
    // ramps only when live (during a cross-fade). Outside a cross-fade the
    // inactive tap is parked at zero.
    float   tap_delay_[2];
    int     active_tap_;            // index of currently active (full-gain) tap

    // Crossfade state
    bool    in_crossfade_;
    float   cf_gain_[2];
    int     cf_elapsed_;
    int     cf_duration_;

    // ZC ring buffer: absolute sample-index of each qualified zero crossing.
    // No playback time stored — firing is detected on the output side.
    int32_t zc_history_[ZC_HISTORY_SIZE];
    int     zc_head_;               // next write position
    int     zc_count_;              // number of valid entries

    // Sample counter (absolute, since init)
    int32_t sample_index_;

    // Derived constants (recomputed in set_pitch_ratio / init)
    float lower_threshold_;         // in samples
    float upper_threshold_;         // in samples
    int   loop_cf_samples_;
    int   attack_cf_samples_;
    int   bailout_cf_samples_;

    // ------------------------------------------------------------------
    // Helpers
    // ------------------------------------------------------------------
    void  add_zc_record(int32_t at);
    void  pop_oldest();
    void  flush_zc_history();
    void  start_crossfade(float new_delay_override, int cf_duration);
    void  update_derived_constants();

    // True if any record exists; if so writes the oldest AT to `out`.
    bool  peek_oldest(int32_t& out) const;
};
