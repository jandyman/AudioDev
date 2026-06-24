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

# Repo-root audio folders, resolved relative to THIS file so callers pass a bare
# filename ("Fourth Test.wav") instead of reconstructing "../../../test_audio"
# from wherever the script happens to live. lib/ is python/lib/, three levels
# under the repo root.
_REPO_ROOT         = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
TEST_AUDIO_DIR     = os.path.join(_REPO_ROOT, 'test_audio')
TEST_AUDIO_OUT_DIR = os.path.join(_REPO_ROOT, 'test_audio_out')


def _resolve(name, folder):
  """A bare filename (no directory part) resolves under `folder`; anything with
  a path component or an absolute path is used exactly as given."""
  return name if os.path.dirname(name) else os.path.join(folder, name)


def install_x_zoom(fig, x_min, x_max, base_scale=1.3, pan_frac=0.20):
  """Mouse-wheel navigation on the x axis, no toolbar mode-switching:

    scroll            zoom x, anchored at the cursor (up = in, down = out)
    shift + scroll    pan x left / right (down = back, up = forward)

  With sharex=True on the figure's axes, changing one xlim propagates to all.
  Toolbar Home still resets to the original full range (we seed the toolbar's
  navigation stack on first draw so Home has a view to return to; wheel
  zoom/pan otherwise leaves the stack empty). pan_frac is the fraction of the
  visible width moved per scroll notch.
  """
  def on_scroll(event):
    ax = event.inaxes
    if ax is None or event.xdata is None: return
    x0, x1 = ax.get_xlim()
    width = x1 - x0

    if event.key == 'shift':
      # Horizontal pan: shift the window, preserving width, clamped to range.
      shift = event.step * pan_frac * width   # up/away -> forward (right)
      new_left, new_right = x0 + shift, x1 + shift
      if new_left  < x_min: new_left,  new_right = x_min, x_min + width
      if new_right > x_max: new_left,  new_right = x_max - width, x_max
    else:
      # Zoom anchored at the cursor (clamped to the full data range).
      factor = (1.0 / base_scale) if event.step > 0 else base_scale
      x = event.xdata
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


def event_indices(signal, thresh=0.5):
  """Rising-edge indices of a 0/1 impulse-or-flag signal — where it crosses up
  through `thresh`. Works the same for single-sample impulse trains (each spike
  is one event) and for held flags (one event at each activation, not per sample).
  """
  s = np.asarray(signal) > thresh
  rising = s & ~np.concatenate(([False], s[:-1]))
  return np.flatnonzero(rising)


def mark_events(axes, x, events, thresh=0.5, color='C3', lw=1.0, alpha=0.6, label=None):
  """Draw vertical markers at discrete events across one or more shared-x axes.

  axes:   a single Axes OR an iterable/array of them — mark every panel in one
          call so markers line up across the whole figure.
  x:      the x-coordinate array (e.g. time); events index into it.
  events: a per-sample 0/1 impulse/flag signal (rising edges are used), OR an
          array of integer sample indices already extracted.
  label:  legend label; attached to the first line only so the legend shows once.

  Returns the event index array (handy for counting / reuse).
  """
  ev = np.asarray(events)
  is_signal = ev.dtype == bool or np.issubdtype(ev.dtype, np.floating) or ev.size == len(x)
  idx = event_indices(ev, thresh) if is_signal else ev.astype(int)

  ax_list = np.asarray(axes, dtype=object).ravel() if hasattr(axes, '__iter__') else [axes]
  for ax in ax_list:
    for k, i in enumerate(idx):
      ax.axvline(x[i], color=color, lw=lw, alpha=alpha, label=(label if k == 0 else None))
  return idx


def load_audio_mono(name, folder=TEST_AUDIO_DIR):
  """Load a WAV, return (sample_rate, float64 mono samples in [-1, 1]).

  `name` may be a bare filename — resolved under `folder` (default the repo-root
  test_audio/) — or a full/relative path with a directory part, used as given.
  """
  sr, raw = wav.read(_resolve(name, folder))
  if raw.dtype == np.int16:
    x = raw.astype(np.float64) / 32768.0
  elif raw.dtype == np.int32:
    x = raw.astype(np.float64) / 2147483648.0
  else:
    x = raw.astype(np.float64)
  if x.ndim > 1: x = x[:, 0]
  return sr, x


def out_path(name, folder=TEST_AUDIO_OUT_DIR):
  """Resolve an output WAV path: a bare filename lands in `folder` (default the
  repo-root test_audio_out/); a path with a directory part passes through. The
  target directory is created. Build the name with the usual <stem>_<tag>.wav
  convention, e.g. out_path(f'{stem}_pitch_shifted_{st:+d}st.wav')."""
  path = _resolve(name, folder)
  os.makedirs(os.path.dirname(path), exist_ok=True)
  return path
