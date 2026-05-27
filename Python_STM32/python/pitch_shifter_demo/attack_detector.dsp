/* @block
(define-block attack_detector
 (inputs in)
 (outputs trigger threshold fast_env slow_env note_ended med_env))
*/

// Attack Detector - Bass Guitar Transient Detection
//
// Designed for bass guitar (E1=41Hz to D4=294Hz)
//
// Two detection paths:
//
//   1. Armed trigger (derivative-based):
//      When fast_env drops below slow_env * end_ratio, a note has ended.
//      Any energy rise (fast_deriv > armed_thresh) fires immediately.
//      Works well for intentional note endings (finger damp, new pick).
//
//   2. Retrigger (absolute level-based):
//      During inhibition after a trigger, if fast_env jumps substantially
//      above med_env (the "current energy"), fire again. This catches
//      real attacks that follow false triggers from bass cycle peaks.
//      The previous crossfade stands; the retrigger starts a fresh one.
//      Only one retrigger allowed per inhibition window.
//
// Input 1:  audio signal
// Output 1: attack impulse (0 or 1)
// Output 2: adaptive threshold (probe)
// Output 3: fast envelope (probe)
// Output 4: slow envelope (probe)
// Output 5: note-ended flag (probe: 1 = armed, 0 = sustaining)
// Output 6: medium envelope (probe)

import("stdfaust.lib");

// ============================================================
// Parameters
// ============================================================

// RMS front-end: smooths per-cycle peaks
rms_window = 0.008;  // 8ms - ~1/3 of lowest bass period

// Fast envelope on RMS signal
fast_attack  = 0.001;   // 1ms
fast_release = 0.010;   // 10ms

// Medium envelope on RMS signal (tracks current energy level)
med_attack   = 0.005;   // 5ms
med_release  = 0.050;   // 50ms

// Slow envelope on RMS signal
slow_attack  = 0.050;   // 50ms
slow_release = 0.200;   // 200ms

// Note-end detection: when fast/slow ratio drops below this, arm the trigger
end_ratio = 0.75;  // fast has dropped to 75% of slow -> note has ended

// Attack sensitivity once armed (derivative-based, proportional to med_env)
armed_floor   = 0.00005; // Minimum threshold in silence
armed_scale   = 0.003;   // armed_thresh = med_env * this (trades latency for fewer false triggers)
active_thresh = 0.02;    // High - only big transients trigger during sustain

// Retrigger: absolute level comparison (fast_env vs med_env)
retrigger_ratio = 1.4;   // fast_env must exceed med_env * this

// Inhibition: prevent re-triggering on first cycles of a new note
inhibit_time = 0.050;  // 50ms

// ============================================================
// RMS envelope (one-pole lowpass on squared signal, then sqrt)
// ============================================================

rms_env(window_s, x) = x * x : onepole : sqrt
with {
    coeff = exp(-1.0 / (window_s * ma.SR));
    onepole(y) = y * (1.0 - coeff) : (+ ~ *(coeff));
};

// ============================================================
// Asymmetric one-pole envelope follower
// ============================================================

env_ar(att_s, rel_s, x) = loop ~ _
with {
    att_c = exp(-1.0 / (att_s * ma.SR));
    rel_c = exp(-1.0 / (rel_s * ma.SR));
    loop(prev) = ba.if(x > prev,
                       att_c * prev + (1.0 - att_c) * x,
                       rel_c * prev);
};

// ============================================================
// Main process
// ============================================================

process(audio) = trigger, threshold, fast_env, slow_env, note_ended, med_env
with {
    // RMS front-end
    rms = rms_env(rms_window, audio);

    // Envelope followers on RMS
    fast_env = env_ar(fast_attack, fast_release, rms);
    med_env  = env_ar(med_attack, med_release, rms);
    slow_env = env_ar(slow_attack, slow_release, rms);

    // Derivative of fast envelope
    fast_deriv = fast_env - fast_env';

    // Note-end detection: fast has dropped well below slow
    epsilon = 0.0001;
    note_ended = fast_env < (slow_env * end_ratio + epsilon);

    // Adaptive threshold: proportional to med_env when armed, high during sustain
    armed_thresh = max(armed_floor, med_env * armed_scale);
    threshold = ba.if(note_ended, armed_thresh, active_thresh);

    // Raw detection (derivative-based)
    raw_detect = fast_deriv > threshold;

    // Retrigger detection (absolute level-based)
    retrigger_detect = fast_env > (med_env * retrigger_ratio);

    // State machine: (inhibit_count, did_retrigger)
    inhibit_samples = int(inhibit_time * ma.SR);

    sm(p_inhib, p_retrig) = n_inhib, n_retrig, trig
    with {
        can_fire = p_inhib <= 0;

        // Normal trigger: derivative exceeds threshold while not inhibited
        normal_fire = raw_detect & can_fire;

        // Retrigger: during inhibition, fast_env jumped above med_env
        // Only one retrigger per inhibition window
        can_retrigger = (p_inhib > 0) & (p_retrig < 0.5) & retrigger_detect;

        trig = normal_fire | can_retrigger;

        // Track retrigger: set on retrigger, clear on normal fire
        n_retrig = ba.if(normal_fire, 0.0,
                    ba.if(can_retrigger, 1.0, p_retrig));

        // Reset inhibition on any trigger
        n_inhib = ba.if(trig, inhibit_samples, max(0, p_inhib - 1));
    };

    feedback = sm ~ (_, _);
    trigger = feedback : !, !, _;
};
