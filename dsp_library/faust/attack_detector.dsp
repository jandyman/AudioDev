// Attack Detector - Bass Guitar Transient Detection
// Note-end detection arms a sensitive trigger for the next attack
//
// Designed for bass guitar (E1=41Hz to D4=294Hz)
//
// Strategy: Rather than trying to detect attacks directly (which is hard
// because bass cycle rising edges look like attacks), we detect note *endings*
// by comparing a fast RMS envelope against a slow one. When the fast envelope
// drops significantly below the slow envelope, we know a note has ended and
// arm a sensitive trigger. The next energy rise fires immediately.
//
// This works because:
//   - Note endings produce a clear drop in the fast/slow envelope ratio
//   - Once we're confident a note has ended, false triggers are benign
//   - The slow envelope provides context for "where energy is dropping from"
//
// Input 1:  audio signal
// Output 1: attack impulse (0 or 1)
// Output 2: adaptive threshold (debug probe)

import("stdfaust.lib");

// ============================================================
// Parameters
// ============================================================

// RMS front-end: smooths per-cycle peaks
rms_window = 0.008;  // 8ms - ~1/3 of lowest bass period

// Fast envelope on RMS signal
fast_attack  = 0.001;   // 1ms
fast_release = 0.010;   // 10ms

// Slow envelope on RMS signal
slow_attack  = 0.050;   // 50ms
slow_release = 0.200;   // 200ms

// Note-end detection: when fast/slow ratio drops below this, arm the trigger
end_ratio = 0.5;  // fast has dropped to 50% of slow -> note has ended

// Attack sensitivity once armed
armed_thresh  = 0.0002;  // Very low - any energy rise triggers when armed
active_thresh = 0.02;    // High - only big transients trigger during sustain

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

process(audio) = trigger, threshold
with {
    // RMS front-end
    rms = rms_env(rms_window, audio);

    // Envelope followers on RMS
    fast_env = env_ar(fast_attack, fast_release, rms);
    slow_env = env_ar(slow_attack, slow_release, rms);

    // Derivative of fast envelope
    fast_deriv = fast_env - fast_env';

    // Note-end detection: fast has dropped well below slow
    epsilon = 0.0001;
    note_ended = fast_env < (slow_env * end_ratio + epsilon);

    // Adaptive threshold: very sensitive when note has ended, high during sustain
    threshold = ba.if(note_ended, armed_thresh, active_thresh);

    // Raw detection
    raw_detect = fast_deriv > threshold;

    // Inhibition timer
    inhibit_samples = int(inhibit_time * ma.SR);

    step(prev_count) = new_count, trig
    with {
        can_fire = prev_count <= 0;
        trig = raw_detect & can_fire;
        new_count = ba.if(trig, inhibit_samples, max(0, prev_count - 1));
    };

    trigger = step ~ _ : !, _;
};
