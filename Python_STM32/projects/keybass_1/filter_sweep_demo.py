"""
Demo for keybass_1's resonant 24 dB LP with envelope-swept cutoff (filter_sweep.dsp).

The "whole shebang" so far: a steady numpy pulse (NO amplitude envelope) is fed
through a moog_vcf_2b whose cutoff = offset * 2^(env_octaves * env), with the ADSR
gated by one long note. You hear the filter open on the attack and decay to the
sustain cutoff, then release.

Run from PyCharm (scipy env). No CLI args; config vars at the bottom. `run()`
returns the filtered buffer so you can `play(out, sr, device=...)` at a breakpoint.
Uses the diagnostic_plot toolset (shared-x panels, install_x_zoom, mark_events).
See docs/python_experimentation.md.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'python'))
from lib.diagnostic_plot import install_x_zoom, mark_events   # BEFORE pyplot
from lib.audio_buf_tools import run_faust, play               # play: breakpoint use

import numpy as np
import matplotlib.pyplot as plt
from pulse_generator import pulse

def run(pulse_cfg, params, sr, dur):
  n = int(dur * sr)
  t = np.arange(n) / sr
  x = pulse(pulse_cfg['freq'], n, sr=sr, duty=pulse_cfg['duty'],
            transition=pulse_cfg['transition']).astype('float32')
  dsp = os.path.join(os.path.dirname(__file__), 'filter_sweep.dsp')
  out, env, cutoff, gate, amp = run_faust(x, dsp, params=params, sr=sr, bs=128, all_outputs=True)

  fig, ax = plt.subplots(4, 1, figsize=(14, 10), sharex=True)
  ax[0].plot(t, x, lw=0.5, color='0.6'); ax[0].set_ylabel('pulse in')
  ax[0].set_title(f"pulse {pulse_cfg['freq']:g} Hz -> moog_vcf_2b, env-swept cutoff")
  ax[1].plot(t, out, lw=0.5, color='C0'); ax[1].set_ylabel('filtered out')
  ax[2].plot(t, env, lw=1.2, color='C2', label='filter env')
  ax[2].plot(t, amp, lw=1.2, color='C4', label='amp env (VCA)')
  ax[2].plot(t, gate, lw=0.8, color='0.7', label='gate')
  ax[2].set_ylabel('envs / gate'); ax[2].set_ylim(-0.05, 1.05); ax[2].legend(loc='upper right')
  ax[3].plot(t, cutoff, lw=1.2, color='C1'); ax[3].set_ylabel('cutoff (Hz)')
  ax[3].set_yscale('log')   # exponential mapping -> log axis reads as the env shape
  ax[3].axhline(params['cutoff_offset'], color='0.5', ls=':', lw=0.8)

  mark_events(ax, t, (gate > 0.5).astype(float), color='orange', lw=0.8, label='note on')
  ax[0].set_xlim(0, t[-1])
  for a in ax: a.grid(True, alpha=0.3)
  fig.tight_layout()
  install_x_zoom(fig, x_min=0.0, x_max=t[-1])
  plt.show()
  return out, sr

if __name__ == '__main__':
  sr  = 48000
  dur = 7.0   # one ~5 s note + release tail
  pulse_cfg = {'freq': 60.0, 'duty': 0.5, 'transition': 5}
  params = {
    'gate_on':       0.2,    # s, note start
    'note_len':      5.0,    # s, gate held high
    # filter (VCF) envelope THis— shapes timbre / the cutoff sweep
    'attack':        0.1 ,   # s
    'decay':         1.5,    # T60, s
    'sustain':       0.25,   # level 0..1
    'release':       0.4,    # T60, s
    'cutoff_offset': 120.0,  # Hz, resting/base cutoff (the offset)
    'env_octaves':   4.0,    # sweep depth in octaves
    'resonance':     0.3,    # 0..1 (moog_vcf_2b; quite resonant)
    # amplitude (VCA) envelope — starts/stops the note
    'amp_attack':    0.005,  # s
    'amp_decay':     0.30,   # T60, s
    'amp_sustain':   0.80,   # level 0..1
    'amp_release':   0.15,   # T60, s
  }
  out, sr = run(pulse_cfg, params, sr, dur)
  play(out / max(1e-9, np.abs(out).max()) * 0.3, sr)   # normalized audition
