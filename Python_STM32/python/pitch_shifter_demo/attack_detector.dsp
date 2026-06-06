/* @block
(define-block attack_detector
 (inputs in)
 (outputs trigger threshold fast_env slow_env hold_env dive_strength k_effective active_gain))
*/

// Attack Detector — bass guitar transient detection
//
// Continuous, level-invariant, three-envelope design. No absolute thresholds.
//
// Envelopes (all driven by an RMS front-end):
//   fast (1ms / 10ms)              — instantaneous level
//   hold (5ms / 24ms hold / 10ms)  — recent peak; the reference fast must
//                                    exceed by k_effective × to count as an
//                                    attack. The 24 ms hold window preserves a
//                                    transient's true peak briefly, preventing
//                                    nuisance re-fires on the same attack's
//                                    decay tail.
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

rms_window = 0.008;  // 8 ms RMS window (~1/3 lowest-bass period)

// fast: instantaneous level tracker
fast_attack  = 0.001;
fast_release = 0.010;

// hold: recent peak (5ms attack, 24ms hold window, 10ms fast release)
hold_attack       = 0.005;
hold_time         = 0.024;   // ≈ 1 / E1 = 1/41 Hz
hold_fast_release = 0.010;

// slow: natural-decay reference. 1s release ≈ bass-string ring-down.
slow_attack  = 0.200;
slow_release = 1.000;

// K bounds. k_effective ranges between these based on dive_strength.
// Scaled 1.35× from a prior 1.5/1.0 baseline based on bass-test-file analysis:
// real attacks (incl. damped ghost plucks) sat well above the 1.35 mark on the
// normalized fire-strength plot, while noise/spurious crossings sat under it.
K_FULL  = 2.025;  // no dive: strict, sustain-mode trigger
K_FLOOR = 1.35;   // full dive: minimum rise above hold to count as attack

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

// ============================================================
// Main process
// ============================================================

process(audio) = trigger, threshold, fast_env, slow_env, hold_env, dive_strength, k_effective, active_gain
with {
    rms = rms_env(rms_window, audio);

    fast_env = env_ar(fast_attack, fast_release, rms);
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
