"""
Demo for keybass_1's raised-cosine pulse generator.

Run from PyCharm (scipy env). No CLI args; config vars live at the bottom.
`run()` returns a buffer of the configured pulse so you can audition it at a
breakpoint: `play(audio, sr, device=...)` (or just `play(audio, sr)` if your
system default output is sane). See docs/python_experimentation.md.

Figures:
  1. time domain — waveform (a few cycles) + a single rising edge (zoom-enabled).
  2. spectrum — the naive 48 k pulse vs an oversampled-and-decimated, essentially
     alias-free reference of the SAME waveform. Where naive rises above the
     reference is aliasing; the worst such excess (dB below the fundamental) is
     printed. The true-harmonic comb (k*f0) is marked to guide the eye.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'python'))
from lib.diagnostic_plot import install_x_zoom   # BEFORE pyplot (sets backend)
from lib.audio_buf_tools import play             # noqa: F401  (for breakpoint use)

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import resample_poly
from pulse_generator import pulse

def alias_reference(freq, duty, transition, sr, n, os_factor):
  """Alias-free reference: same waveform oversampled (edge DURATION preserved),
  ideal-lowpassed and decimated back to sr. Returns an n-length buffer."""
  y_os = pulse(freq, n * os_factor, sr=sr * os_factor,
               duty=duty, transition=transition * os_factor)
  return resample_poly(y_os, 1, os_factor)[:n]

def run(freq, duty, transition, sr, dur, os_factor):
  n = int(dur * sr)
  t = np.arange(n) / sr
  audio = pulse(freq, n, sr=sr, duty=duty, transition=transition)

  # --- Figure 1: time domain --------------------------------------------------
  fig1, ax = plt.subplots(2, 1, figsize=(14, 7))
  span = min(n, int(5 * sr / freq))
  ax[0].plot(t[:span], audio[:span], lw=1.0, color='C0', marker='.', ms=3)
  ax[0].set_ylabel('pulse'); ax[0].set_title(
    f'{freq:g} Hz, duty {duty:g}, N={transition} samples')
  ax[0].set_xlim(0, t[span - 1]); ax[0].grid(True, alpha=0.3)
  edge = max(transition * 4, 12)
  ax[1].plot(t[:edge] * 1e3, audio[:edge], lw=1.0, color='C1', marker='o', ms=4)
  ax[1].set_ylabel('rising edge'); ax[1].set_xlabel('ms'); ax[1].grid(True, alpha=0.3)
  fig1.tight_layout()
  install_x_zoom(fig1, x_min=0.0, x_max=t[span - 1])

  # --- Figure 2: aliasing analysis -------------------------------------------
  win = np.hanning(n)
  freqs = np.fft.rfftfreq(n, 1.0 / sr)
  ref = alias_reference(freq, duty, transition, sr, n, os_factor)
  m_naive = np.abs(np.fft.rfft(audio * win))
  m_ref   = np.abs(np.fft.rfft(ref   * win))
  ref0 = m_naive[np.argmin(np.abs(freqs - freq))]   # fundamental magnitude
  naive_db = 20 * np.log10(m_naive / ref0 + 1e-12)
  ref_db   = 20 * np.log10(m_ref   / ref0 + 1e-12)

  # Aliasing = naive energy where the reference is negligible (off the comb),
  # above 20 Hz. Worst such peak, in dB below the fundamental.
  alias_zone = (ref_db < -80.0) & (freqs > 20.0)
  worst = naive_db[alias_zone].max() if alias_zone.any() else -np.inf
  print(f"N={transition} @ {freq:g} Hz, duty {duty:g}: "
        f"worst aliasing {worst:.1f} dB below fundamental")

  fig2, axs = plt.subplots(figsize=(14, 5))
  for k in range(1, int(sr / 2 / freq) + 1):              # true-harmonic comb
    axs.axvline(k * freq, color='0.85', lw=0.6, zorder=0)
  axs.plot(freqs, naive_db, lw=0.8, color='C3', label='naive 48 k')
  axs.plot(freqs, ref_db,   lw=1.0, color='C0', label=f'reference ({os_factor}x)')
  axs.axhline(worst, color='k', ls='--', lw=0.8, label=f'worst alias {worst:.1f} dB')
  axs.set_xlim(0, sr / 2); axs.set_ylim(-120, 5)
  axs.set_xlabel('Hz'); axs.set_ylabel('dB (re fundamental)')
  axs.set_title(f'aliasing: naive vs alias-free reference, N={transition}')
  axs.grid(True, alpha=0.3); axs.legend()
  fig2.tight_layout()

  plt.show()
  return audio, sr

if __name__ == '__main__':
  sr         = 48000
  freq       = 110.0   # A2 — a real bass register
  duty       = 0.125
  transition = 5       # N: raised-cosine edge width in samples
  dur        = 3.0     # seconds — the returned buffer is this long, for audition
  os_factor  = 16      # oversampling for the alias-free reference
  audio, sr  = run(freq, duty, transition, sr, dur, os_factor)
  play(audio, sr)    # uncomment, or call at a breakpoint
