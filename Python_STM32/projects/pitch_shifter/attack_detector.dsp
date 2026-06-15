/* @block
(define-block attack_detector
 (inputs in)
 (outputs trigger threshold fast_env slow_env hold_env dive_strength k_effective active_gain ref_env))
*/

// Attack Detector — bass guitar transient detection
//
// Ported from the Python lab (attack_detector_lab.py). Two independent
// subsystems share this block:
//
//   1. TRIGGER  (fast / ref edge detector — the live, simple path)
//   2. DIVE     (slow / hold note-end detector — feeds active_gain muting in
//               loop_controller; preserved verbatim, lower-priority to simplify)
//
// ---- Trigger (level-invariant edge detector) -------------------------------
//
//   fast_env = peak-track of |audio|, 25 ms hold, accelerating release.
//   ref_env  = two-stage-attack / two-stage-release follower OF fast_env.
//   trigger  = rising edge of (fast_env / ref_env) across a LIVE threshold k(t)
//              that rests at k_nom, snaps to k_boost on each fire, then decays
//              back toward k_nom (the boosted-threshold holdoff — see below).
//
// ref_env is the reference ceiling that fast_env is measured against. Its
// attack is deliberately lagged so a fresh transient opens a fast/ref gap:
//
//   - Two-stage ATTACK: for a brief window (ref_att_slow_dur_s) after ref
//     re-enters attack mode it rises SLOWLY (ref_att_slow_s), so fast pulls
//     further ahead and the fast/ref ratio spikes higher at the transient
//     (stronger detection). Then it switches to a FAST attack (ref_att_fast_s)
//     so ref catches back up to fast between sub-peaks.
//   - Two-stage RELEASE: holds (ref_hold_rel_s ≈ ∞) for ref_hold_s after a
//     peak, then drops fast (ref_drop_s) so ref dives along with fast between
//     notes. A new attack therefore always sees a low ref → clean ratio spike
//     regardless of how loud the previous note was (works on legato, where a
//     within-cycle RMS reference rode up with the signal and showed no gap).
//
// No absolute level threshold: noise-floor false fires are accepted (signal so
// low it cannot produce an audible artifact, and active_gain mutes downstream).
//
// ---- Dive (note-end detector — preserved for loop_controller muting) -------
//
// hold_env (fast 5/24h/10 ms RMS peak) vs slow_env (200 ms / 1 s RMS, natural
// ring-down reference). When the player damps/articulates a note end, hold
// falls fast while slow lags — that gap is the dive:
//
//   dive_strength = clip((slow - hold) / slow, 0, 1)
//   active_gain   = 1 - dive_strength      // 1 = note sounding, 0 = ended/damped
//
// loop_controller multiplies the pitch-shifted loop taps by active_gain, so
// the output is muted during silence and armed-regime false fires land silent.
//
// Output 1: trigger impulse (0 or 1)
// Output 2: threshold (= ref_env * k_live) — probe, plots against fast_env
// Output 3: fast_env — probe
// Output 4: slow_env — probe (dive)
// Output 5: hold_env — probe (dive)
// Output 6: dive_strength 0..1 — probe / mute source
// Output 7: k_effective (= k_live, the live boosted threshold) — probe
// Output 8: active_gain (= 1 - dive_strength) — probe / mute
// Output 9: ref_env — trigger reference ceiling — probe

import("stdfaust.lib");

// ============================================================
// Parameters
// ============================================================

// --- Trigger path ---

// fast: instantaneous peak track of |audio| with hold + accelerating release.
// Hold > one low-E period (~24.4 ms) eliminates per-cycle wobble without RMS
// lag; past hold the release TC shrinks continuously.
fast_hold_s = 0.025;
fast_rel_s  = 0.050;

// ref: two-stage-attack / two-stage-release follower of fast_env.
// Attack: slow for ref_att_slow_dur_s after entering attack (widens the gap),
// then fast (catch-up = holdoff). Release: hold then drop (dives with fast).
ref_att_slow_s     = 0.050;   // slow initial attack — widens fast/ref at onset
ref_att_fast_s     = 0.015;   // quick catch-up after the slow window (holdoff)
ref_att_slow_dur_s = 0.012;   // how long ref stays in slow attack after onset
ref_hold_s         = 0.025;   // release plateau ≈ one low-E period
ref_hold_rel_s     = 1.000;   // hold-rate TC during the plateau (≈ perfect hold)
ref_drop_s         = 0.050;   // fall rate past the plateau

// Trigger: boosted-threshold holdoff (replaces the absolute debounce). The
// live threshold k(t) rests at k_nom, snaps to k_boost on each fire, then
// decays back toward k_nom with TC k_decay_s. The fire test is a rising edge
// of the ratio across the LIVE k, so a sustained-high ratio yields no new edge
// as k decays (no re-fire); a genuinely larger attack (ratio above the still-
// elevated k) overrides. Level-independent — k rests at a fixed nominal value.
k_nom     = 2.0;     // resting threshold
k_boost   = 20.0;    // threshold snaps here on each fire
k_decay_s = 0.020;   // boost decay time constant (s)

// --- Dive path (preserved for active_gain / loop_controller muting) ---

rms_window = 0.008;  // 8 ms RMS window (~1/3 lowest-bass period); hold + slow

// hold: recent peak (5 ms attack, 24 ms hold window, 10 ms fast release)
hold_attack       = 0.005;
hold_time         = 0.024;   // ≈ 1 / E1 = 1/41 Hz
hold_fast_release = 0.010;

// slow: natural-decay reference. 1 s release ≈ bass-string ring-down.
slow_attack  = 0.200;
slow_release = 1.000;

// Avoid divide-by-zero (dive_strength when slow ≈ 0; ratio when ref ≈ 0).
eps = 1.0e-9;

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
// track). The effective release TC starts at infinity right after a peak and
// shrinks continuously: TC(t) = rel_s * (hold_samples/t)^2. The "hold-ish"
// behavior near a peak emerges from TC being very large there.
//   eff_rel = exp(sf^2 * log_rel_c),  sf = t / hold_samples.
env_hold_accel(hold_s, rel_s, x) = feedback : _, !
with {
    rel_c        = exp(-1.0 / (rel_s * ma.SR));
    log_rel_c    = log(rel_c);                            // negative; init-time constant
    hold_samples = max(1.0, hold_s * ma.SR);

    sm(prev, timer) = next_prev, next_timer
    with {
        in_attack    = x > prev;
        next_timer   = ba.if(in_attack, 0.0, timer + 1.0);
        sf           = next_timer / hold_samples;
        eff_rel      = exp(sf * sf * log_rel_c);
        released     = eff_rel * prev;
        next_prev    = ba.if(in_attack, x, released);      // instantaneous peak track
    };

    feedback = sm ~ (_, _);
};

// Two-stage-attack / two-stage-release follower (mirror of the lab's
// env_ar_2attack_hold). Attack: slow (att_slow_s) for the first att_slow_dur_s
// after re-entering attack mode, then fast (att_fast_s). Release: hold-rate
// (rel_hold_s) for rel_hold_dur_s after a peak, then drop-rate (rel_drop_s).
// The attack timer resets each time the follower re-enters attack mode.
env_ar_2attack(att_slow_s, att_fast_s, att_slow_dur_s,
               rel_hold_s, rel_drop_s, rel_hold_dur_s, x) = feedback : _, !, !, !
with {
    att_c_slow       = exp(-1.0 / (att_slow_s * ma.SR));
    att_c_fast       = exp(-1.0 / (att_fast_s * ma.SR));
    rel_c_hold       = exp(-1.0 / (rel_hold_s * ma.SR));
    rel_c_drop       = exp(-1.0 / (rel_drop_s * ma.SR));
    att_slow_samples = att_slow_dur_s * ma.SR;
    rel_hold_samples = rel_hold_dur_s * ma.SR;

    // State (prev, atk_timer, rel_timer, rising). `rising` = was the previous
    // sample in attack mode — drives the attack-timer reset on re-entry.
    sm(prev, atk_timer, rel_timer, rising) = next_prev, next_atk_timer, next_rel_timer, next_rising
    with {
        in_attack  = x > prev;
        entering   = in_attack & (rising < 0.5);
        atk_use    = ba.if(entering, 0.0, atk_timer);      // timer used this sample
        att_c      = ba.if(atk_use < att_slow_samples, att_c_slow, att_c_fast);
        attacked   = att_c * prev + (1.0 - att_c) * x;
        rel_c      = ba.if(rel_timer < rel_hold_samples, rel_c_hold, rel_c_drop);
        released   = rel_c * prev;
        next_prev  = ba.if(in_attack, attacked, released);
        next_atk_timer = ba.if(in_attack, atk_use + 1.0, atk_timer);
        next_rel_timer = ba.if(in_attack, 0.0, rel_timer + 1.0);
        next_rising    = ba.if(in_attack, 1.0, 0.0);
    };

    feedback = sm ~ (_, _, _, _);
};

// ============================================================
// Main process
// ============================================================

process(audio) = trigger, threshold, fast_env, slow_env, hold_env, dive_strength, k_effective, active_gain, ref_env
with {
    rms = rms_env(rms_window, audio);

    // --- Trigger path ---
    fast_env = env_hold_accel(fast_hold_s, fast_rel_s, abs(audio));
    ref_env  = env_ar_2attack(ref_att_slow_s, ref_att_fast_s, ref_att_slow_dur_s,
                              ref_hold_rel_s, ref_drop_s, ref_hold_s, fast_env);

    // --- Dive path (preserved) ---
    slow_env      = env_ar(slow_attack, slow_release, rms);
    hold_env      = env_hold(hold_attack, hold_time, hold_fast_release, rms);
    dive_raw      = (slow_env - hold_env) / (slow_env + eps);
    dive_strength = max(0.0, min(1.0, dive_raw));
    active_gain   = 1.0 - dive_strength;

    // --- Trigger state machine: boosted-threshold holdoff (mirror of the lab) ---
    // State (p_b, p_prev_ratio): p_b is the boost ABOVE k_nom (starts at 0 so
    // the live threshold starts at k_nom, matching the lab), p_prev_ratio is the
    // previous-sample ratio. Fire on a rising edge of the ratio across the live
    // threshold (k_nom + p_b); on fire set the boost to (k_boost - k_nom), else
    // decay it toward 0. Live threshold k = k_nom + boost.
    current_ratio = fast_env / max(ref_env, 1.0e-12);
    k_decay_c     = exp(-1.0 / (k_decay_s * ma.SR));

    sm(p_b, p_prev_ratio) = n_b, n_prev_ratio, trig
    with {
        k_now        = k_nom + p_b;
        trig         = (current_ratio > k_now) & (p_prev_ratio <= k_now);
        n_b          = ba.if(trig, k_boost - k_nom, p_b * k_decay_c);
        n_prev_ratio = current_ratio;
    };

    feedback = sm ~ (_, _);
    trigger  = feedback : !, !, _;
    k_live   = k_nom + (feedback : _, !, !);   // live threshold, for probes

    // Probes.
    threshold   = ref_env * k_live;
    k_effective = k_live;
};
