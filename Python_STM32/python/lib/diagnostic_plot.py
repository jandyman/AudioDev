"""
diagnostic_plot — shared helpers for offline probe/diagnostic plots.

Use with sharex=True multi-panel figures so scroll-wheel zoom and the
toolbar Home button propagate across all panels.

Importing this module ALSO bootstraps matplotlib for all diagnostic scripts:
  - sets MPLCONFIGDIR to ~/.cache/matplotlib so matplotlib can write its font
    cache without granting write access to ~/.matplotlib
  - selects the TkAgg backend (cooperative window geometry; the macosx backend
    forces figures back to a fixed position/size on every redraw)

For this to take effect, scripts must `from lib.diagnostic_plot import ...`
BEFORE doing `import matplotlib.pyplot as plt`.
"""
import os

# Matplotlib config dir — must be set before matplotlib is imported anywhere.
_MPL_CACHE = os.path.expanduser('~/.cache/matplotlib')
os.makedirs(_MPL_CACHE, exist_ok=True)
os.environ.setdefault('MPLCONFIGDIR', _MPL_CACHE)

import matplotlib
matplotlib.use('TkAgg')

import numpy as np
import scipy.io.wavfile as wav


def install_x_zoom(fig, x_min, x_max, base_scale=1.3):
  """Scroll wheel -> horizontal-only zoom anchored at cursor x.

  With sharex=True on the figure's axes, changing one xlim propagates.
  Toolbar Home button resets to the original full range (we seed the
  toolbar's navigation stack on first draw so Home has a view to return to;
  scroll-wheel zoom otherwise leaves the stack empty).
  """
  def on_scroll(event):
    ax = event.inaxes
    if ax is None or event.xdata is None: return
    factor = (1.0 / base_scale) if event.step > 0 else base_scale
    x = event.xdata
    x0, x1 = ax.get_xlim()
    new_left  = max(x - (x - x0) * factor, x_min)
    new_right = min(x + (x1 - x) * factor, x_max)
    if new_right - new_left < 1e-6: return
    ax.set_xlim(new_left, new_right)
    fig.canvas.draw_idle()
  fig.canvas.mpl_connect('scroll_event', on_scroll)

  seeded = [False]
  def _seed_home(_evt):
    if seeded[0]: return
    tb = getattr(fig.canvas, 'toolbar', None)
    if tb is not None and hasattr(tb, 'push_current'):
      tb.push_current()
      seeded[0] = True
  fig.canvas.mpl_connect('draw_event', _seed_home)


def load_audio_mono(path):
  """Load a WAV file, return (sample_rate, float64 mono samples in [-1, 1])."""
  sr, raw = wav.read(path)
  if raw.dtype == np.int16:
    x = raw.astype(np.float64) / 32768.0
  elif raw.dtype == np.int32:
    x = raw.astype(np.float64) / 2147483648.0
  else:
    x = raw.astype(np.float64)
  if x.ndim > 1: x = x[:, 0]
  return sr, x
