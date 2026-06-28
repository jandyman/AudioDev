// keybass_1 — resonant 24 dB LP with envelope-swept cutoff.
//
// The pulse wave is the INPUT (x), generated in numpy by pulse_generator and fed
// in by run_faust. There is NO amplitude envelope: the pulse plays steadily and
// the ADSR modulates only the filter cutoff, so you hear the filter open and
// close on a sustained tone.
//
// Time-varying control must live inside the block — run_faust holds parameters
// constant for the whole render. So the gate, envelope and cutoff are all
// computed here and exposed as probe outputs for plotting:
//   0 filtered = ve.moog_vcf(res, cutoff) applied to x   (audition)
//   1 env      = ADSR envelope 0..1                       (probe)
//   2 cutoff   = filter cutoff in Hz                       (probe)
//   3 gate     = note gate 0/1                             (probe)
import("stdfaust.lib");

// One-shot note from the sample clock: a single long note shows attack/decay,
// sustain across the hold, then release.
gate_on  = nentry("gate_on", 0.2, 0.0, 20.0, 0.001);    // s, note start
note_len = nentry("note_len", 5.0, 0.1, 20.0, 0.001);   // s, gate held high
tsec = ba.time / ma.SR;
gate = (tsec >= gate_on) & (tsec < gate_on + note_len);

// ADSR (exponential segments; decay/release are T60 times).
att = nentry("attack",  0.005, 0.0, 2.0, 0.0001);
dec = nentry("decay",   0.8,   0.0, 5.0, 0.0001);
sus = nentry("sustain", 0.25,  0.0, 1.0, 0.001);
rel = nentry("release", 0.4,   0.0, 5.0, 0.0001);
env = en.adsre(att, dec, sus, rel, gate);

// Env -> cutoff, EXPONENTIAL (V/oct): `offset` is the resting/base cutoff in Hz,
// the envelope adds `env_oct` octaves on top. Clamped to the filter's stable
// range, then smoothed (~2 ms) to de-zipper fast modulation.
offset  = nentry("cutoff_offset", 120.0, 20.0, 4000.0, 0.1);  // Hz, base/offset
env_oct = nentry("env_octaves", 4.0, 0.0, 8.0, 0.01);         // sweep depth, oct
cutoff  = min(ma.SR / 6.5, offset * pow(2.0, env_oct * env))
          : si.smooth(ba.tau2pole(0.002));

// moog_vcf_2b: biquad-factored Moog, 24 dB/oct, resonant. Chosen over moog_vcf
// because it modulates cleanly (moog_vcf's instantaneous unity-gain rescaling
// spikes badly on a fast cutoff sweep). NB: its `res` is the 4th root of
// moog_vcf's, i.e. more resonant for the same number.
res = nentry("resonance", 0.7, 0.0, 0.999, 0.001);

// VCA amplitude envelope — this is what starts/stops the note. A lowpass alone
// can't: it always passes the fundamental (a 24 dB slope only attenuates it), so
// without a VCA the steady pulse drones from t=0 and the note has no clean onset.
// Separate ADSR from the filter sweep (VCF env shapes timbre, VCA env articulates).
amp_a = nentry("amp_attack",  0.005, 0.0, 2.0, 0.0001);
amp_d = nentry("amp_decay",   0.30,  0.0, 5.0, 0.0001);
amp_s = nentry("amp_sustain", 0.80,  0.0, 1.0, 0.001);
amp_r = nentry("amp_release", 0.15,  0.0, 5.0, 0.0001);
amp = en.adsre(amp_a, amp_d, amp_s, amp_r, gate);

process(x) = (x : ve.moog_vcf_2b(res, cutoff) : *(amp)), env, cutoff, gate, amp;
