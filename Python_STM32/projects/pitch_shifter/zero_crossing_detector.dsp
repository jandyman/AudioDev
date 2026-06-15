/* @block
(define-block zero_crossing_detector
 (inputs in)
 (outputs zc_out amp_env raw_zc zc_deriv))
*/

// Zero-crossing detector — qualified positive-going crossings (amplitude-gated,
// min-spacing) for bass guitar. Doc: zero_crossing_detector.md.

import("stdfaust.lib");

// ============================================================
// Parameters
// ============================================================

// Short-term amplitude envelope tracks signal level near each crossing
amp_attack  = 0.001;   // 1ms  - fast response to level changes
amp_release = 0.010;   // 10ms - holds level briefly after crossing

// Minimum amplitude to qualify a zero crossing.
// Set above noise floor, below softest expected bass note.
min_amplitude = 0.01;

// Minimum spacing between qualified crossings.
// Must be below the shortest expected period (3.2ms at 311Hz) to pass all
// fundamentals, while blocking most harmonic crossings at higher frequencies.
min_spacing = 0.0025;  // 2.5ms -> passes fundamentals up to 400Hz

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

process(x) = zc_out, amp_env, raw_zc, zc_deriv
with {
    // Short-term amplitude envelope on absolute value
    amp_env = env_ar(amp_attack, amp_release, abs(x));

    // Raw positive-going zero crossing: previous sample negative, current non-negative
    raw_zc = (x >= 0) & (x' < 0);

    // Amplitude gate: reject crossings where signal level is too low
    amp_gated = raw_zc & (amp_env > min_amplitude);

    // Inhibit timer: enforces minimum spacing between qualified crossings
    inhibit_samples = int(min_spacing * ma.SR);

    sm(p_inhib) = n_inhib, fire
    with {
        can_fire = p_inhib <= 0;
        fire = amp_gated & can_fire;
        n_inhib = ba.if(fire, inhibit_samples, max(0, p_inhib - 1));
    };

    feedback = sm ~ _;
    zc_out = feedback : !, _;

    // Derivative magnitude at each qualified crossing (x - x' is the instantaneous
    // slope; positive for a positive-going crossing). Zero between crossings.
    zc_deriv = ba.if(zc_out > 0.5, x - x', 0.0);
};
