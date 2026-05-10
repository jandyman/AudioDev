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
// No dynamic memory allocation in process(). All state is statically declared.
//
// Inputs  (2): zc_impulse, attack_impulse
// Outputs (8): tap1_delay_ms, tap2_delay_ms, gain1, gain2,
//              latency_ms (probe), loop_event (probe),
//              active_tap (probe), bailout_event (probe)
//
// Parameters: pitch_ratio (adjustable at runtime; flushes ZC history on change)

class LoopController {
public:
    // ------------------------------------------------------------------
    // Constants
    // ------------------------------------------------------------------

    // ZC record ring buffer size. Worst case: 200ms / 3.2ms ≈ 63 records.
    static const int ZC_HISTORY_SIZE = 128;

    // Bass guitar frequency range for period matching:
    // A1 (55 Hz) to ~2.5 octaves above (~311 Hz)
    static constexpr float FREQ_LOW_HZ  = 55.0f;
    static constexpr float FREQ_HIGH_HZ = 311.0f;

    // Latency thresholds
    static constexpr float LOWER_THRESHOLD_MS = 100.0f;
    static constexpr float UPPER_THRESHOLD_MS = 200.0f;

    // Minimum delay on any tap reset (avoids zero-delay artifacts)
    static constexpr float MIN_DELAY_SAMPLES = 4.0f;

    // Period-matching tolerance (±fraction)
    static constexpr float PERIOD_TOLERANCE = 0.20f;

    // Crossfade durations
    static constexpr float LOOP_CROSSFADE_MS      = 5.0f;   // relaxed
    static constexpr float ATTACK_FADEIN_MS        = 1.0f;   // short — preserve transient
    static constexpr float BAILOUT_CROSSFADE_MULT  = 3.0f;   // bailout = 3× loop crossfade

    // ------------------------------------------------------------------
    // ZC record (stored per qualified zero crossing)
    // ------------------------------------------------------------------
    struct ZCRecord {
        int32_t at;  // arrival time (sample index when ZC entered delay buffer)
        float   pt;  // playback time: at + delay_at_arrival / pitch_ratio
    };

    // ------------------------------------------------------------------
    // Public interface
    // ------------------------------------------------------------------
    LoopController();

    void init(int sample_rate);
    void set_pitch_ratio(float ratio);
    float get_pitch_ratio() const { return pitch_ratio_; }

    int get_num_inputs()  const { return 2; }
    int get_num_outputs() const { return 8; }
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
                 float& tap1_delay_ms, float& tap2_delay_ms,
                 float& gain1, float& gain2,
                 float& latency_ms, float& loop_event,
                 float& active_tap_out, float& bailout_event);

    // ------------------------------------------------------------------
    // Internal state — all statically declared
    // ------------------------------------------------------------------

    float   sample_rate_;
    float   pitch_ratio_;
    float   dd_;                    // delay delta per sample = 1 - pitch_ratio

    // Tap delays in samples. Both taps ramp every sample.
    float   tap_delay_[2];
    int     active_tap_;            // index of currently active (full-gain) tap

    // Crossfade state
    bool    in_crossfade_;
    float   cf_gain_[2];
    int     cf_elapsed_;
    int     cf_duration_;

    // ZC record ring buffer (statically allocated)
    ZCRecord zc_history_[ZC_HISTORY_SIZE];
    int      zc_head_;              // next write position
    int      zc_count_;             // number of valid entries

    // Scheduled loop transition
    bool    transition_scheduled_;
    float   transition_fire_pt_;    // sample index at which to execute

    // Sample counter
    int32_t sample_index_;

    // Derived constants (recomputed in set_pitch_ratio / init)
    float lower_threshold_;         // in samples
    float upper_threshold_;         // in samples
    float min_period_;              // output-domain period for FREQ_HIGH_HZ, in samples
    float max_period_;              // output-domain period for FREQ_LOW_HZ,  in samples
    int   loop_cf_samples_;
    int   attack_cf_samples_;
    int   bailout_cf_samples_;

    // ------------------------------------------------------------------
    // Helpers
    // ------------------------------------------------------------------
    void  add_zc_record(int32_t at, float pt);
    void  prune_zc_history();
    void  flush_zc_history();
    bool  find_candidate(float& out_new_delay_now, float& out_fire_pt);
    void  start_crossfade(float new_delay_override, int cf_duration);
    void  update_derived_constants();
};
