/* @block
(define-block attack_detector
 (inputs in)
 (outputs trigger threshold fast_env slow_env hold_env dive_strength k_effective active_gain))
*/

// Attack Detector — bass guitar transient detection
//
// Continuous, level-invariant, three-envelope design. No absolute thresholds.
//
// Envelopes:
//   fast (peak-track / 25 ms hold / 50 ms accel-release on |audio|) — was
//                                    RMS+AR; now bypasses RMS entirely. Hold
//                                    preserves the per-cycle peak through one
//                                    low-E period (24 ms), eliminating wobble
//                                    without the 8 ms RMS lag. Past hold the
//                                    release coefficient accelerates
//                                    (rel_c^shrink_factor where shrink_factor
//                                    grows linearly past hold) so the decay
//                                    time constant continuously shrinks. Rise
//                                    time is now ~0 ms; previous ~9 ms.
//   hold (5ms / 24ms hold / 10ms)  — recent-peak reference. RMS-based, kept
//                                    on the original chain. fast must exceed
//                                    hold * k_effective to count as an attack.
//   slow (200ms / 1s)              — natural-decay reference. Only used to
//                                    compute dive_strength; the 1 s release
//                                    matches a freely-ringing bass string.
//
// Dive: how much hold has dropped relative to slow. When the player damps the
// string or articulates a note end, hold falls fast while slow lags — that
// gap IS the dive. Continuous 0..1, not a binary branch.
//
//     dive_strength = clip((slow - hold) / slow, 0, 1)
//
// Trigger rule (level-invariant, ratio-based):
//
//     k_effective = K_FULL - dive_strength * (K_FULL - K_FLOOR)
//     attack      = fast > hold * k_effective
//
// At no dive (sustaining note), k_effective = K_FULL (strict). At full dive
// (note clearly ended), k_effective = K_FLOOR (permissive). Smooth in between.
//
// State machine:
//   - Rising-edge detection on `attack_detected` ensures one fire per attack.
//   - 50 ms inhibit absorbs brief within-period drops/rises of attack_detected
//     so a single physical attack doesn't double-fire on intra-cycle ripple.
//   - No retrigger machinery — the dive-modulated K_effective already handles
//     same-level new attacks naturally (dive rises → K drops → next attack
//     crosses threshold on its own).
//
// Output 1: trigger impulse (0 or 1)
// Output 2: live threshold (= hold * k_effective) — probe
// Output 3: fast envelope — probe
// Output 4: slow envelope — probe
// Output 5: hold envelope — probe
// Output 6: dive_strength 0..1 — probe
// Output 7: k_effective — probe (live decision K)

import("stdfaust.lib");

// ============================================================
// Parameters
// ============================================================

rms_window = 0.008;  // 8 ms RMS window (~1/3 lowest-bass period); used by hold + slow only

// fast: instantaneous peak tracker with hold + accelerating release on |audio|.
// Hold > one low-E period eliminates per-cycle wobble without RMS smoothing
// (the 8 ms RMS lag is gone). With pure peak hold, square+sqrt around the
// level cancel — no RMS needed.
fast_hold_s = 0.025;  // 25 ms — just past one low-E period (~24.4 ms)
fast_rel_s  = 0.050;  // nominal release TC; accelerates continuously past hold

// hold: recent peak (5ms attack, 24ms hold window, 10ms fast release)
hold_attack       = 0.005;
hold_time         = 0.024;   // ≈ 1 / E1 = 1/41 Hz
hold_fast_release = 0.010;

// slow: natural-decay reference. 1s release ≈ bass-string ring-down.
slow_attack  = 0.200;
slow_release = 1.000;

// K bounds. k_effective ranges between these based on dive_strength.
// Bumped ~3× from prior 2.025 / 1.35 (which were tuned against the old
// RMS+AR fast_env that tracked body level). fast_env is now peak-tracking on
// |audio|, so the fast/hold ratio on transients spikes much higher (peak is
// 3–5× body on bass attacks). Starting guess — refine by reading the
// normalized fire-strength plot against bass test files.
K_FULL  = 6.0;   // no dive: strict, sustain-mode trigger
K_FLOOR = 4.0;   // full dive: minimum rise above hold to count as attack

// Inhibit window: just long enough to suppress within-period ripple from
// causing same-attack double-fires. Well under typical inter-note spacing.
inhibit_time = 0.050;

// Avoid divide-by-zero in dive_strength when slow ≈ 0
slow_eps = 1.0e-9;

// ============================================================
// Envelope followers
// ============================================================

rms_env(window_s, x) = x * x : onepole : sqrt
with {
    coeff = exp(-1.0 / (window_s * ma.SR));
    onepole(y) = y * (1.0 - coeff) : (+ ~ *(coeff));
};

env_ar(att_s, rel_s, x) = loop ~ _
with {
    att_c = exp(-1.0 / (att_s * ma.SR));
    rel_c = exp(-1.0 / (rel_s * ma.SR));
    loop(prev) = ba.if(x > prev,
                       att_c * prev + (1.0 - att_c) * x,
                       rel_c * prev);
};

// Hold-then-release follower: attack like env_ar; on release the coefficient
// blends from 1.0 (perfect hold) to rel_c over hold_samples.
env_hold(att_s, hold_s, rel_fast_s, x) = feedback : _, !
with {
    att_c        = exp(-1.0 / (att_s * ma.SR));
    rel_c        = exp(-1.0 / (rel_fast_s * ma.SR));
    hold_samples = max(1.0, hold_s * ma.SR);

    // Output order must match input order for `~ (_, _)` feedback wiring.
    sm(prev, timer) = next_prev, next_timer
    with {
        in_attack    = x > prev;
        attacked     = att_c * prev + (1.0 - att_c) * x;
        next_timer   = ba.if(in_attack, 0.0, timer + 1.0);
        hold_factor  = min(1.0, next_timer / hold_samples);
        eff_rel      = 1.0 - hold_factor * (1.0 - rel_c);
        released     = eff_rel * prev;
        next_prev    = ba.if(in_attack, attacked, released);
    };

    feedback = sm ~ (_, _);
};

// Continuous-time-varying-release peak follower. Instantaneous attack (peak
// track). The effective release time constant TC(t) starts at infinity right
// after a peak and shrinks continuously: TC(t) = rel_s * (hold_samples/t)^2.
// At t = hold_samples, TC = rel_s (nominal). At t = 2*hold_samples, TC = rel_s/4.
// At t = 3*hold_samples, TC = rel_s/9. No piecewise hold-then-release split —
// the "hold-ish" behavior near a peak emerges from TC being very large there.
//
// Math: eff_rel(t) = exp(-1/(TC(t)*SR)) = exp(-(t/hold_samples)^2 / (rel_s*SR))
//                  = exp((t/hold_samples)^2 * log(rel_c)).
// Cumulative envelope ratio over n samples: exp(log_rel_c * n^3 / (3*hold_samples^2)).
env_hold_accel(hold_s, rel_s, x) = feedback : _, !
with {
    rel_c        = exp(-1.0 / (rel_s * ma.SR));
    log_rel_c    = log(rel_c);                            // negative; init-time constant
    hold_samples = max(1.0, hold_s * ma.SR);

    sm(prev, timer) = next_prev, next_timer
    with {
        in_attack    = x > prev;
        next_timer   = ba.if(in_attack, 0.0, timer + 1.0);
        sf           = next_timer / hold_samples;          // dimensionless time
        // eff_rel = exp(sf^2 * log_rel_c). Smoothly approaches 1 as sf -> 0
        // (perfect hold near the peak) and shrinks faster than exponential past
        // sf = 1. Single continuous formula, no branches.
        eff_rel      = exp(sf * sf * log_rel_c);
        released     = eff_rel * prev;
        next_prev    = ba.if(in_attack, x, released);      // instantaneous peak track
    };

    feedback = sm ~ (_, _);
};

// ============================================================
// Main process
// ============================================================

process(audio) = trigger, threshold, fast_env, slow_env, hold_env, dive_strength, k_effective, active_gain
with {
    rms = rms_env(rms_window, audio);

    // fast_env now bypasses RMS: peak track of |audio| with hold + accel release.
    fast_env = env_hold_accel(fast_hold_s, fast_rel_s, abs(audio));
    slow_env = env_ar(slow_attack, slow_release, rms);
    hold_env = env_hold(hold_attack, hold_time, hold_fast_release, rms);

    // Dive: hold dropped relative to slow. Clipped to [0, 1].
    dive_raw      = (slow_env - hold_env) / (slow_env + slow_eps);
    dive_strength = max(0.0, min(1.0, dive_raw));

    // Effective K: continuous between K_FULL (no dive) and K_FLOOR (full dive).
    k_effective = K_FULL - dive_strength * (K_FULL - K_FLOOR);

    // active_gain: 1 when note sounding, 0 when ended/damped. Mutes pitch-shifter
    // output during silence and suppresses old-buffer bleed during attack crossfade.
    active_gain = 1.0 - dive_strength;

    // Live threshold (exposed as probe). Trigger fires when fast > threshold.
    threshold = hold_env * k_effective;

    attack_detected = fast_env > threshold;

    // State machine: inhibit counter + previous attack_detected state.
    // Fire on the rising edge of attack_detected (false → true), gated by
    // can_fire (inhibit window). No retrigger logic — dive-modulated K
    // handles same-level new attacks via the ratio test itself.
    inhibit_samples = int(inhibit_time * ma.SR);

    sm(p_inhib, p_prev_det) = n_inhib, n_prev_det, trig
    with {
        can_fire    = p_inhib <= 0;
        rising_edge = attack_detected & (p_prev_det < 0.5);
        trig        = rising_edge & can_fire;
        n_inhib     = ba.if(trig, inhibit_samples, max(0, p_inhib - 1));
        n_prev_det  = ba.if(attack_detected, 1.0, 0.0);
    };

    feedback = sm ~ (_, _);
    trigger  = feedback : !, !, _;
};
