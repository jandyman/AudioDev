"""
Demo for keybass_1's ADSR (adsr.dsp, en.adsre exponential segments).

Run from PyCharm (scipy env). No CLI args; config vars at the bottom. Renders the
Faust block via a one-shot run_faust round-trip (no build step) with an internal
periodic gate, so you see several attack/decay/sustain/release cycles in one go.
`run()` returns the voice buffer so you can `play(voice, sr, device=...)` at a
breakpoint. See docs/python_experimentation.md.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'python'))
from lib.diagnostic_plot import install_x_zoom, mark_events   # BEFORE pyplot
from lib.audio_buf_tools import run_faust, play               # play: breakpoint use

import numpy as np
import matplotlib.pyplot as plt

def run(params, sr, dur):
  n = int(dur * sr)
  t = np.arange(n) / sr
  x = np.zeros(n, dtype='float32')
  dsp = os.path.join(os.path.dirname(__file__), 'adsr.dsp')
  voice, env, gate = run_faust(x, dsp, params=params, sr=sr, bs=128, all_outputs=True)

  fig, ax = plt.subplots(2, 1, figsize=(14, 7), sharex=True)
  ax[0].plot(t, voice, lw=0.5, color='0.6'); ax[0].set_ylabel('voice')
  ax[0].set_title("ADSR (en.adsre) — env * saw")

  ax[1].plot(t, env, lw=1.2, color='C0', label='env')
  ax[1].plot(t, gate, lw=0.8, color='0.7', label='gate')
  ax[1].axhline(params['sustain'], color='C3', ls='--', lw=0.8, label='sustain')
  ax[1].set_ylabel('env / gate'); ax[1].set_ylim(-0.05, 1.05); ax[1].legend(loc='upper right')

  mark_events(ax, t, (gate > 0.5).astype(float), color='orange', lw=0.8, label='note on')
  ax[0].set_xlim(0, t[-1])
  for a in ax: a.grid(True, alpha=0.3)
  fig.tight_layout()
  install_x_zoom(fig, x_min=0.0, x_max=t[-1])
  plt.show()
  return voice, sr

if __name__ == '__main__':
  sr  = 48000
  dur = 3.0
  params = {
    'note_rate': 1.5,    # notes / second
    'gate_duty': 0.55,   # fraction of each note the gate is held on
    'carrier':   110.0,  # test-tone Hz (A2)
    'attack':    0.005,  # s
    'decay':     0.25,   # T60, s
    'sustain':   0.30,   # level 0..1
    'release':   0.20,   # T60, s
  }
  voice, sr = run(params, sr, dur)
  # play(voice, sr)   # uncomment, or call at a breakpoint
