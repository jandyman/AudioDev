"""
YIN detector demo / lab. Drives the generated pybind_yin module whole-file and
plots the probes (signal-node probing). Main figure is time-domain with shared-x
scroll-wheel zoom (scroll = horizontal zoom anchored at cursor; toolbar Home
resets): input + estimated f0, the decimated signal, and aperiodicity/confidence.
A second figure shows the latest d'(τ) curve (lag domain — own axis).

Build first (scipy conda env):  make -f yin.make
Run from PyCharm (scipy interpreter). Configure inputs at the bottom.
"""
import sys, os

# Must precede matplotlib.pyplot — diagnostic_plot sets MPLCONFIGDIR and backend.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'python'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from lib.diagnostic_plot import install_x_zoom, load_audio_mono

import numpy as np
import matplotlib.pyplot as plt
from build.pybind_yin import yin

DECIM = 16   # must match yin_detector.h

def make_detector(sr, fmin, fmax, threshold):
  yd = yin(); yd.init(sr)
  yd.set_param('yd.fmin', fmin)
  yd.set_param('yd.fmax', fmax)
  yd.set_param('yd.threshold', threshold)
  return yd

def run_file(fn, fmin, fmax, threshold):
  here = os.path.dirname(__file__)
  sr, audio = load_audio_mono(os.path.join(here, '..', '..', '..', 'test_audio', fn))
  N = len(audio)
  yd = make_detector(sr, fmin, fmax, threshold)
  yd.process_chunk(audio.astype(np.float32))

  f0   = np.array(yd.get_buffer('yd.f0', N))
  aper = np.array(yd.get_buffer('yd.aperiodicity', N))
  dec  = np.array(yd.get_buffer('yd.decimated', N))
  tau_max = int(np.ceil((sr / DECIM) / fmin))

  t = np.arange(N) / sr

  # The dprime probe holds only the LATEST update's curve, so a whole-file run
  # leaves it at end-of-file (decayed → flat). Re-run up to the highest-
  # confidence instant so the snapshot lands inside a sustained note, where the
  # dip is razor-sharp. (A click-to-redraw upgrade would make this per-moment.)
  conf = 1.0 - aper
  snap = int(np.argmax(np.where(f0 > 0, conf, -1.0)))   # only where an estimate exists
  yd2 = make_detector(sr, fmin, fmax, threshold)
  yd2.process_chunk(audio[:snap + 1].astype(np.float32))
  dprime = np.array(yd2.get_buffer('yd.dprime', tau_max + 1))

  # ---- main figure: time-domain, shared-x, scroll-wheel zoom ----
  fig, ax = plt.subplots(3, 1, figsize=(15, 9), sharex=True)
  fig.suptitle(f"YIN — {fn}  (sr={sr}, ÷{DECIM} → {sr//DECIM} Hz, thr={threshold})")

  ax[0].plot(t, audio, lw=0.5, color='0.6', label='input')
  a0 = ax[0].twinx()
  a0.plot(t, f0, lw=1.2, color='C0', label='f0 (Hz)')
  a0.set_ylabel('f0 (Hz)', color='C0'); a0.set_ylim(0, fmax * 1.1)
  ax[0].set_ylabel('input'); ax[0].set_title('input + estimated f0')

  ax[1].plot(t, dec, lw=0.6, color='C2')
  ax[1].set_ylabel('decimated'); ax[1].set_title('decimated signal (ZOH probe)')

  ax[2].plot(t, conf, lw=1.0, color='C3')
  ax[2].axhline(1.0 - threshold, color='k', ls='--', lw=0.8, label=f'1-thr')
  ax[2].axvline(snap / sr, color='C1', lw=1.0, alpha=0.8)   # d'(τ) snapshot time
  ax[2].set_ylim(-0.05, 1.05)
  ax[2].set_ylabel('confidence'); ax[2].set_xlabel('time (s)')
  ax[2].set_title("confidence = 1 - aperiodicity (1 = strongly periodic)")
  for a in ax: a.grid(True, alpha=0.3)
  ax[0].set_xlim(0, t[-1])
  fig.tight_layout()
  install_x_zoom(fig, x_min=0.0, x_max=t[-1])

  # ---- d'(τ) snapshot (lag domain — separate, own x-axis) ----
  fig2, bx = plt.subplots(figsize=(11, 4))
  tau = np.arange(len(dprime))
  bx.plot(tau, dprime, lw=1.0, color='C4')
  bx.axhline(threshold, color='k', ls='--', lw=0.8)
  star = int(np.argmin(np.where(tau >= 2, dprime, np.inf)))
  bx.plot(star, dprime[star], 'o', color='C1', ms=8)
  bx.set_xlabel('lag τ (decimated samples)'); bx.set_ylabel("d'(τ)")
  bx.set_title(f"d'(τ) at t={snap/sr:.3f}s (peak confidence) — dip τ={star} → "
               f"{sr / (star * DECIM):.1f} Hz" if star else "d'(τ)")
  bx.grid(True, alpha=0.3)
  fig2.tight_layout()

if __name__ == '__main__':
  in_file   = "Fourth Test.wav"
  fmin      = 40.0
  fmax      = 330.0
  threshold = 0.12

  run_file(in_file, fmin, fmax, threshold)
  plt.show()
