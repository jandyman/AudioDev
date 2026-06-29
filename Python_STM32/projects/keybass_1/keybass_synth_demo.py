"""
keybass_1 — first end-to-end LISTEN: estimators -> synced pulse -> ADSR + filter.

Wires the Step-1 sensing front-end (input_lpf -> detection LP -> attack_detector ->
extremum detector) to a hard-synced pulse train, then the real Faust voice
(keybass_synth.dsp: ADSR -> exp cutoff -> moog_vcf_2b -> VCA). numpy generates the
three control/source signals (pulse, gate, amp=fast_env); Faust does the DSP.

Sample-resolution, no fractional placement and no real-attack splice yet (Step 2) —
this is purely "does the basic idea sound like anything." Saves a stereo WAV
(L = dry bass, R = synth) and can play it. Filter/ADSR defaults are the values
tuned in filter_sweep_demo.

Run from PyCharm (scipy env). No CLI args; config at the bottom. See keybass_1.md.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'python'))
from lib.diagnostic_plot import install_x_zoom, load_audio_mono, mark_events, event_indices, out_path
from lib.audio_buf_tools import run_faust, play

import numpy as np
import matplotlib.pyplot as plt
import scipy.io.wavfile as wav
from scipy.signal import butter, sosfilt
from pulse_generator import pulse_shape
from period_sense_demo import detect_extrema

DSP_FAUST = os.path.join(os.path.dirname(__file__), '..', '..', 'dsp_faust')

def anchor_notes(trig_idx, pos_idx, neg_idx, n):
  """Per note (between attack triggers), the anchor-polarity extrema: polarity is
  set by the first qualified extremum after the trigger (self-calibrating)."""
  allk = np.concatenate([pos_idx, neg_idx])
  pol = np.concatenate([np.ones(len(pos_idx)), -np.ones(len(neg_idx))])
  o = np.argsort(allk); allk, pol = allk[o], pol[o]
  bounds = list(trig_idx) + [n]
  notes = []
  for i, t0 in enumerate(trig_idx):
    seg = (allk >= t0) & (allk < bounds[i + 1])
    ks, ps = allk[seg], pol[seg]
    if len(ks):
      notes.append(ks[ps == ps[0]])
  return notes

def synced_pulse(notes, n, duty, transition):
  """Hard-synced pulse train: one raised-cosine cycle per consecutive anchor pair,
  phase 0 (rising edge) on each anchor extremum. Silent (0) outside notes."""
  out = np.zeros(n)
  for ks in notes:
    for a0, a1 in zip(ks[:-1], ks[1:]):
      P = a1 - a0
      if P <= 0: continue
      phase = (np.arange(a0, a1) - a0) / P
      out[a0:a1] = 2.0 * pulse_shape(phase, duty, transition / P) - 1.0   # -> [-1,1]
  return out

def note_gate(trig_idx, active_gain, n, active_thr):
  """1 from each attack trigger; note-off when the dive detector's active_gain
  drops below active_thr AFTER the note has established (active_gain first rose
  above it). Without that 'armed' step the gate would close instantly, since at the
  trigger instant active_gain is still recovering from the previous note's decay.
  A new trigger re-arms and re-attacks."""
  gate = np.zeros(n)
  trig = np.zeros(n, dtype=bool); trig[np.asarray(trig_idx, dtype=int)] = True
  on = armed = False
  for i in range(n):
    if trig[i]:
      on, armed = True, False
    if on:
      if active_gain[i] >= active_thr: armed = True
      elif armed:                      on = False
    gate[i] = 1.0 if on else 0.0
  return gate

def run(in_file, fc, det_fc, det_order, k_qual, deriv_lp_ms, refractory_ms,
        duty, transition, active_thr, voice, play_it):
  sr, audio = load_audio_mono(in_file)
  n = len(audio); t = np.arange(n) / sr

  lpf = run_faust(audio.astype(np.float32), os.path.join(DSP_FAUST, 'input_lpf.dsp'),
                  params={'fc': fc}, sr=sr)
  det = sosfilt(butter(det_order, det_fc, btype='low', fs=sr, output='sos'),
                lpf).astype(np.float32)
  atk = run_faust(det, os.path.join(DSP_FAUST, 'attack_detector.dsp'), sr=sr, all_outputs=True)
  trigger, fast_env, active_gain = atk[0], atk[2], atk[7]

  pos_idx, neg_idx, _ = detect_extrema(det, fast_env, sr, k_qual, deriv_lp_ms, refractory_ms)
  trig_idx = event_indices(trigger)
  notes = anchor_notes(trig_idx, pos_idx, neg_idx, n)

  pulse = synced_pulse(notes, n, duty, transition)
  gate = note_gate(trig_idx, active_gain, n, active_thr)
  amp = fast_env

  synth, env, cutoff = run_faust(np.stack([pulse, gate, amp]).astype(np.float32),
                                 os.path.join(os.path.dirname(__file__), 'keybass_synth.dsp'),
                                 params=voice, sr=sr, all_outputs=True)

  # Stereo A/B: L = dry bass, R = synth. Joint-normalize so the relative levels read.
  stereo = np.stack([audio, synth], axis=1)
  peak = np.abs(stereo).max()
  if peak > 0: stereo = stereo / (peak * 1.05)
  wav.write(out_path(f"{os.path.splitext(in_file)[0]}_keybass.wav"), sr,
            np.clip(stereo * 32767, -32768, 32767).astype(np.int16))
  if play_it:
    play(synth / max(1e-9, np.abs(synth).max()) * 0.3, sr)

  fig, ax = plt.subplots(4, 1, figsize=(15, 10), sharex=True)
  ax[0].plot(t, audio, lw=0.5, color='0.6'); ax[0].set_ylabel('dry bass')
  ax[1].plot(t, pulse, lw=0.5, color='C0'); ax[1].set_ylabel('synced pulse')
  ax[2].plot(t, synth, lw=0.5, color='C3'); ax[2].set_ylabel('synth out')
  ax[3].plot(t, env, lw=1.0, color='C2', label='VCF env'); ax[3].plot(t, gate, lw=0.7, color='0.7', label='gate')
  ax[3].set_ylabel('env / gate'); ax[3].set_ylim(-0.05, 1.05)
  axb = ax[3].twinx(); axb.plot(t, cutoff, lw=1.0, color='C1', label='cutoff'); axb.set_ylabel('cutoff (Hz)', color='C1')
  ax[3].legend(loc='upper right')
  mark_events(ax, t, trigger, color='orange', lw=0.9, label='attack')
  ax[0].set_xlim(0, t[-1])
  for a in ax: a.grid(True, alpha=0.3)
  fig.tight_layout()
  install_x_zoom(fig, x_min=0.0, x_max=t[-1])
  plt.show()

if __name__ == '__main__':
  in_file       = "Bass Notes Bad Trigger 2.wav"
  fc            = 10000.0
  det_fc        = 1000.0
  det_order     = 4
  k_qual        = 0.5
  deriv_lp_ms   = 0.2
  refractory_ms = 3.0
  duty          = 0.5      # pulse duty cycle
  transition    = 5        # raised-cosine edge width, samples
  active_thr    = 0.5      # note-off when the dive detector's active_gain drops below this
  voice = {                # filter/ADSR — the values tuned in filter_sweep_demo
    'attack': 0.01, 'decay': 1, 'sustain': 0.25, 'release': 0.4,
    'cutoff_offset': 120.0, 'env_octaves': 4.0, 'resonance': 0.3,
  }
  play_it = True
  run(in_file, fc, det_fc, det_order, k_qual, deriv_lp_ms, refractory_ms,
      duty, transition, active_thr, voice, play_it)
