// keybass_1 ADSR test voice.
//
// Exponential-segment ADSR (en.adsre — analog-style; decay/release args are
// T60, time to fall 60 dB). Swap to en.adsr for linear segments / literal times.
//
// The gate is generated internally as a periodic note (lf saw < duty) so a
// single constant-param render shows several attack/release cycles — run_faust
// holds parameters constant for the whole render. Outputs three channels:
//   0 voice = env * bandlimited saw  (audition)
//   1 env   = the raw envelope       (probe)
//   2 gate  = the note gate          (probe)

import("stdfaust.lib");

note_rate = nentry("note_rate", 2.0, 0.1, 10.0, 0.01);    // notes / second
gate_duty = nentry("gate_duty", 0.5, 0.05, 0.95, 0.01);   // fraction held on
carrier   = nentry("carrier", 110.0, 20.0, 1000.0, 0.1);  // test-tone Hz

att = nentry("attack",  0.005, 0.0, 1.0, 0.0001);
dec = nentry("decay",   0.20,  0.0, 2.0, 0.0001);
sus = nentry("sustain", 0.30,  0.0, 1.0, 0.001);
rel = nentry("release", 0.15,  0.0, 2.0, 0.0001);

gate  = os.lf_sawpos(note_rate) < gate_duty;
env   = en.adsre(att, dec, sus, rel, gate);
voice = env * os.sawtooth(carrier);

// One (ignored) input so the run_faust playback graph connects cleanly.
process(x) = voice, env, gate;
