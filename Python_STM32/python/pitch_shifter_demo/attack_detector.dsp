/* @block
(define-block attack_detector
 (inputs in)
 (outputs trigger threshold fast_env slow_env note_ended med_env hold_env))
*/

// Attack Detector - Bass Guitar Transient Detection
//
// Designed for bass guitar (E1=41Hz to D4=294Hz)
//
// Detection rule (simplest possible):
//
//     trigger = (fast_env > slow_env * SUSTAIN_ATTACK_RATIO) & can_fire
//
// can_fire = post-trigger inhibit window has elapsed. The previous derivative-
// based armed/active machinery and the retrigger path are gone — see the
// concept doc for the prior design. Probes for the old quantities (med_env,
// note_ended, threshold) are still emitted so the diagnostic plots are
// directly comparable.
//
// hold_env is a new fourth follower with a two-stage release: attack-toward-x
// like env_ar, but on release the coefficient starts at "hold" (effectively
// 1.0, i.e. no decay) for ~24 ms (lowest fundamental of interest, E1) then
// transitions to a normal release coefficient. The intent is to bridge
// intra-cycle envelope ripple at low notes without sacrificing note-end
// latency. It is emitted as a probe and not yet wired into the trigger — once
// the plots tell us whether fast/slow or fast/hold is the cleaner
// discriminator, the rule's denominator can be swapped.
//
// Input 1:  audio signal
// Output 1: attack impulse (0 or 1)
// Output 2: decision threshold (= slow_env * SUSTAIN_ATTACK_RATIO)
// Output 3: fast envelope (probe)
// Output 4: slow envelope (probe)
// Output 5: note-end flag (probe; legacy, not used in trigger logic)
// Output 6: medium envelope (probe; legacy)
// Output 7: hold envelope (probe; two-stage release follower)

import("stdfaust.lib");

// ============================================================
// Parameters
// ============================================================

// RMS front-end: smooths per-cycle peaks
rms_window = 0.008;  // 8 ms - ~1/3 of lowest bass period

// Fast envelope on RMS signal
fast_attack  = 0.001;   // 1 ms
fast_release = 0.010;   // 10 ms

// Medium envelope — slower attack so fast/med ratio is more discriminative
med_attack   = 0.020;   // 20 ms
med_release  = 0.050;

// Slow envelope — longer attack so fast/slow ratio at attacks is larger;
// slow barely budges during the attack peak while fast tracks the new level.
slow_attack  = 0.200;   // 200 ms
slow_release = 0.200;

// Hold envelope — two-stage release. Attack like env_ar; release starts at
// "hold" (perfect hold) for hold_time, then transitions linearly to a fast
// release. With hold_fast_release=10ms, hold snaps down to the actual current
// level after the hold window — making hold_env a clean "is a note currently
// vibrating?" indicator (decays to near zero ~30ms after damping stops).
hold_attack       = 0.005;   // 5 ms
hold_time         = 0.024;   // 24 ms (≈ 1 / E1 = 1/41 Hz)
hold_fast_release = 0.010;   // 10 ms — snap down after hold expires

// Sustain-attack rule: fire when fast exceeds slow by this factor.
SUSTAIN_ATTACK_RATIO = 1.5;

// Minimum fast_env level for a trigger to be considered real. Above noise
// (~0.02) and well below realistic attack peaks (0.13+ in the test files).
MIN_SIGNAL_FLOOR = 0.05;

// Dive-then-attack rule: if hold has decayed below this, the previous note
// has ended (no ripple refreshing hold), so any fast rising above the floor
// is a new note. Picked a small multiple of the floor.
HOLD_LOW_THRESHOLD = 0.02;

// Legacy probes (no longer used in trigger logic but emitted for diagnostics)
end_ratio = 0.75;
armed_floor = 0.00005;

// Inhibition: prevent re-triggering on first cycles of a new note.
// 250 ms — covers slow_env catching up to within × K of fast (with
// slow_attack=200ms and K=1.5, fast/slow drops below K at t ≈ 220 ms).
inhibit_time = 0.250;

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
// Hold-then-release envelope follower
//
// State: (prev_env, release_timer).
//   - On any sample where x > prev_env: attack as env_ar; reset timer.
//   - On any sample where x <= prev_env: increment timer; release coefficient
//     blends from 1.0 (perfect hold) to rel_c (fast release) over hold_samples.
//
// The blend is linear in timer/hold_samples (no zipper concern at audio
// rate since the coefficient only moves once per sample by 1/hold_samples).
// ============================================================

env_hold(att_s, hold_s, rel_fast_s, x) = feedback : _, !
with {
    att_c        = exp(-1.0 / (att_s * ma.SR));
    rel_c        = exp(-1.0 / (rel_fast_s * ma.SR));
    hold_samples = max(1.0, hold_s * ma.SR);

    // Output order must match input order for `~ (_, _)` feedback wiring:
    // first output → first input (prev), second output → second input (timer).
    sm(prev, timer) = next_prev, next_timer
    with {
        in_attack    = x > prev;
        attacked     = att_c * prev + (1.0 - att_c) * x;
        next_timer   = ba.if(in_attack, 0.0, timer + 1.0);
        hold_factor  = min(1.0, next_timer / hold_samples);
        // Effective release coefficient: 1.0 at hold start, rel_c at hold end.
        eff_rel      = 1.0 - hold_factor * (1.0 - rel_c);
        released     = eff_rel * prev;
        next_prev    = ba.if(in_attack, attacked, released);
    };

    feedback = sm ~ (_, _);
};

// ============================================================
// Main process
// ============================================================

process(audio) = trigger, threshold, fast_env, slow_env, note_ended, med_env, hold_env
with {
    // RMS front-end
    rms = rms_env(rms_window, audio);

    // Envelope followers
    fast_env = env_ar(fast_attack, fast_release, rms);
    med_env  = env_ar(med_attack,  med_release,  rms);
    slow_env = env_ar(slow_attack, slow_release, rms);
    hold_env = env_hold(hold_attack, hold_time, hold_fast_release, rms);

    // Legacy probe: note_ended (no longer used in trigger logic)
    epsilon    = 0.0001;
    note_ended = fast_env < (slow_env * end_ratio + epsilon);

    // Decision threshold (exposed as probe). Trigger fires when fast > threshold.
    threshold = slow_env * SUSTAIN_ATTACK_RATIO;

    // Two-branch attack rule, both gated by the noise floor:
    //   - sustain branch:    fast > slow * K   (attack on top of a sustained note)
    //   - dive-then-attack:  hold < hold_low   (previous note's ripple has stopped,
    //                                           so any signal above floor is new)
    above_floor      = fast_env > MIN_SIGNAL_FLOOR;
    sustain_attack   = fast_env > threshold;
    dive_then_attack = hold_env < HOLD_LOW_THRESHOLD;
    attack_detected  = above_floor & (sustain_attack | dive_then_attack);

    // State machine: single state — inhibit_count.
    inhibit_samples = int(inhibit_time * ma.SR);

    sm(p_inhib) = n_inhib, trig
    with {
        can_fire = p_inhib <= 0;
        trig     = attack_detected & can_fire;
        n_inhib  = ba.if(trig, inhibit_samples, max(0, p_inhib - 1));
    };

    feedback = sm ~ _;
    trigger  = feedback : !, _;
};
