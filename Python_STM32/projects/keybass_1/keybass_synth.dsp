// keybass_1 synth voice — driven by external control signals (the numpy estimators).
//
// Inputs (channel order): pulse (the synced bandlimited pulse), gate (note gate
// 0/1 from the attack trigger), amp (amplitude follow = fast_env). The voice does
// the actual DSP: ADSR -> exponential cutoff -> moog_vcf_2b -> VCA. Same chain as
// filter_sweep.dsp, but pulse/gate/amp arrive as inputs instead of being generated
// internally. Outputs: voice (audition), env, cutoff (probes).

import("stdfaust.lib");

att = nentry("attack",  0.1,  0.0, 2.0, 0.0001);
dec = nentry("decay",   1.5,  0.0, 5.0, 0.0001);
sus = nentry("sustain", 0.25, 0.0, 1.0, 0.001);
rel = nentry("release", 0.4,  0.0, 5.0, 0.0001);

offset  = nentry("cutoff_offset", 120.0, 20.0, 4000.0, 0.1);
env_oct = nentry("env_octaves", 4.0, 0.0, 8.0, 0.01);
res     = nentry("resonance", 0.3, 0.0, 0.999, 0.001);

process(pulse, gate, amp) = (pulse : ve.moog_vcf_2b(res, cutoff) : *(amp)), env, cutoff
with {
  env    = en.adsre(att, dec, sus, rel, gate);
  cutoff = min(ma.SR / 6.5, offset * pow(2.0, env_oct * env))
           : si.smooth(ba.tau2pole(0.002));
};
