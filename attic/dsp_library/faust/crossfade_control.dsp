// Crossfade Control - Ping-pong delay tap management for pitch shifting
//
// Manages two delay taps that alternate (ping-pong) with crossfading.
// On each attack trigger, the inactive tap resets to minimum delay and
// a crossfade transitions from the active tap to the freshly reset one.
// Both taps ramp their delay continuously at a rate determined by pitch_ratio.
//
// Input 1:  attack_trigger (0 or 1 impulse)
// Input 2:  pitch_ratio (e.g. 0.5 for octave down, 0.75 for fourth down)
//
// Output 1: delay1_ms (delay time for tap 1)
// Output 2: delay2_ms (delay time for tap 2)
// Output 3: gain1 (crossfade gain for tap 1, 0.0–1.0)
// Output 4: gain2 (crossfade gain for tap 2, 0.0–1.0)
// Output 5: active_tap (probe: 0 or 1)

import("stdfaust.lib");

// ============================================================
// Parameters
// ============================================================

min_delay_samples = 4;
min_delay_ms = min_delay_samples / ma.SR * 1000.0;

xfade_time = 0.0015;  // 1.5ms
xfade_step = 1.0 / (xfade_time * ma.SR);

// ============================================================
// State machine: 6 feedback signals → 6 outputs
// ============================================================

sm(trig, ratio, pd1, pd2, pxf, pact, pxfing, ptgt) =
    nd1, nd2, nxf, nact, nxfing, ntgt
with {
    inc = (1.0 - ratio) / ma.SR * 1000.0;

    fire = (trig > 0.5) & (pxfing < 0.5);

    r1 = fire & (pact > 0.5);
    r2 = fire & (pact < 0.5);

    nd1 = ba.if(r1, min_delay_ms, pd1 + inc) : max(min_delay_ms);
    nd2 = ba.if(r2, min_delay_ms, pd2 + inc) : max(min_delay_ms);

    ntgt = ba.if(fire, ba.if(pact < 0.5, 1.0, 0.0), ptgt);

    xm = ba.if(pxfing > 0.5,
        ba.if(ptgt > 0.5, pxf + xfade_step, pxf - xfade_step),
        pxf);
    nxf_raw = ba.if(fire, pxf, xm);
    nxf = nxf_raw : max(0.0) : min(1.0);

    done = (pxfing > 0.5) &
           (((ptgt > 0.5) & (nxf >= 1.0)) |
            ((ptgt < 0.5) & (nxf <= 0.0)));

    nxfing = ba.if(fire, 1.0, ba.if(done, 0.0, pxfing));
    nact = ba.if(done, 1.0 - pact, pact);
};

// ============================================================
// Wire feedback using Faust's multi-channel ~ operator
// ============================================================

process(attack_trigger, pitch_ratio) = d1, d2, g1, g2, act
with {
    // sm takes 8 inputs: trig, ratio, then 6 feedback signals
    // sm produces 6 outputs which feed back
    // We use the pattern: (sm(trig, ratio) ~ (_, _, _, _, _, _))
    // But we need to pass trig and ratio as "external" inputs

    core = sm(attack_trigger, pitch_ratio);
    feedback = core ~ (_, _, _, _, _, _);

    d1  = feedback : _, !, !, !, !, !;
    d2  = feedback : !, _, !, !, !, !;
    xf  = feedback : !, !, _, !, !, !;
    act = feedback : !, !, !, _, !, !;

    g1 = 1.0 - xf;
    g2 = xf;
};
