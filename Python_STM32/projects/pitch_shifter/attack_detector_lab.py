"""
attack_detector_lab.py — Python-only experimentation space for the bass
attack detector.  No Faust, no chunking, no build step — edit, hit run,
plots refresh.

Two-function contract:
  compute(audio, sr)            — returns dict with 'fires' (int sample
                                   indices) + any named signals you want
                                   to plot.  Edit freely.
  plot_panels(axes, sigs, t)    — draws each panel using sigs[<name>].
                                   Set NUM_PANELS to match.

The driver at the bottom loads each test file, calls compute, builds a
sharex'd figure with NUM_PANELS subplots, calls plot_panels, overlays
fire markers on every panel + big dots on the audio panel, and installs
scroll-wheel x-zoom (toolbar Home resets).

Run from PyCharm with the scipy env (numba optional but recommended —
falls back to pure-Python loops otherwise, ~10x slower).
"""
import os
import sys

# diagnostic_plot lives at Python_STM32/python/lib/diagnostic_plot.py.
# PyCharm has python/ on its content root; add it explicitly for CLI runs.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'python'))
from lib.diagnostic_plot import install_x_zoom, load_audio_mono

import numpy as np
import matplotlib.pyplot as plt

# Numba accelerates the per-sample feedback loops ~50x. Optional.
try:
  from numba import njit
except ImportError:
  def njit(f): return f


# ============================================================
# Envelope primitives  (edit / extend freely)
# ============================================================

def tau_to_c(tau_s, sr):
  """Time constant in seconds → one-pole per-sample coefficient."""
  return np.exp(-1.0 / (tau_s * sr))

@njit
def env_ar(x, att_c, rel_c):
  """Asymmetric attack/release one-pole follower.
     Rises toward x with att_c; decays geometrically with rel_c."""
  y = np.empty_like(x)
  prev = 0.0
  for i in range(len(x)):
    if x[i] > prev:
      prev = att_c * prev + (1.0 - att_c) * x[i]
    else:
      prev = rel_c * prev
    y[i] = prev
  return y

@njit
def env_ar_hold(x, att_c, rel_c_hold, rel_c_drop, hold_samples):
  """AR follower with a two-stage release: hold-rate (rel_c_hold) for the
     first hold_samples after a peak, then drop-rate (rel_c_drop) thereafter.
     Set rel_c_hold ≈ 1.0 (very long TC) for a true plateau; set rel_c_drop
     to whatever fall TC you want past the hold."""
  y = np.empty_like(x)
  timer = 0.0
  prev = 0.0
  for i in range(len(x)):
    if x[i] > prev:
      timer = 0.0
      prev = att_c * prev + (1.0 - att_c) * x[i]
    else:
      c = rel_c_hold if timer < hold_samples else rel_c_drop
      prev = c * prev
      timer += 1.0
    y[i] = prev
  return y

@njit
def env_peak_hold_accel(x_abs, hold_samples, log_rel_c):
  """Peak-track on |x| with continuously-accelerating release.
     Effective release TC shrinks as (t/hold)^2, so behavior is perfect
     hold near a peak and faster-than-exponential decay past it.  Mirror
     of the Faust env_hold_accel block."""
  y = np.empty_like(x_abs)
  prev = 0.0
  timer = 0.0
  for i in range(len(x_abs)):
    if x_abs[i] > prev:
      prev = x_abs[i]
      timer = 0.0
    else:
      sf = timer / hold_samples
      prev = prev * np.exp(sf * sf * log_rel_c)
    timer += 1.0
    y[i] = prev
  return y


# ============================================================
# Detector  — EDIT THIS
# ============================================================
# Simple example: peak-tracking fast env vs slow-attack ref env, fire
# when the ratio crosses k while above a noise floor.  Debounced.
# Replace with whatever you want; just keep the (audio, sr) -> dict
# contract.

def compute(audio, sr):
  x = audio.astype(np.float64)

  # fast: instant-attack peak track on |audio| with hold + accel release.
  # Hold ≥ one low-E period (24 ms) eliminates per-cycle wobble.
  fast_hold_s = 0.025
  fast_rel_s  = 0.050
  fast = env_peak_hold_accel(np.abs(x),
                             hold_samples=fast_hold_s * sr,
                             log_rel_c=np.log(tau_to_c(fast_rel_s, sr)))

  # ref: edge-detector reference.  Attack slower than fast (25 ms) so the
  # ratio fast/ref opens a gap on a rising edge.  Release holds briefly
  # then drops fast so ref dives along with fast between notes — a new
  # attack always sees a low ref and gets a clean ratio spike, regardless
  # of how loud the previous note was.
  ref_att_s       = 0.025
  ref_hold_s      = 0.025          # plateau matches one low-E period
  ref_hold_rel_s  = 1.000          # essentially "hold" — long TC during plateau
  ref_drop_s      = 0.050          # fall rate past the plateau
  ref = env_ar_hold(fast,
                    att_c       = tau_to_c(ref_att_s,      sr),
                    rel_c_hold  = tau_to_c(ref_hold_rel_s, sr),
                    rel_c_drop  = tau_to_c(ref_drop_s,     sr),
                    hold_samples= ref_hold_s * sr)

  # Trigger: ratio crosses threshold (rising edge), with debounce.
  k        = 1.4
  debounce = int(0.025 * sr)
  ratio    = fast / np.maximum(ref, 1e-12)
  detected = ratio > k

  # Rising-edge fire with debounce.  Plain Python loop is fine here —
  # the heavy lifting is in the envelopes above.
  fires = []
  last_fire = -debounce - 1
  prev_det = False
  for i in range(len(audio)):
    if detected[i] and not prev_det and (i - last_fire) > debounce:
      fires.append(i)
      last_fire = i
    prev_det = bool(detected[i])

  return {
    'fast':      fast,
    'ref':       ref,
    'threshold': ref * k,        # plot directly against fast
    'ratio':     ratio,
    'fires':     np.array(fires, dtype=np.int64),
  }


# ============================================================
# Plot panels  — EDIT THIS to match the signals you return
# ============================================================
# axes is a list of NUM_PANELS already-sharex'd matplotlib Axes.
# sigs[<name>] is whatever you put in compute()'s return dict, plus
# sigs['audio'] which the driver adds for convenience.
# Fire markers and the scroll-wheel zoom are added by the driver.

NUM_PANELS = 3

def plot_panels(axes, sigs, t):
  ax = axes[0]
  ax.plot(t, sigs['audio'], 'b-', lw=0.3, alpha=0.5)
  ax.set_ylabel('amplitude'); ax.set_title('Input waveform')

  ax = axes[1]
  ax.plot(t, sigs['fast'],      'r-',  lw=0.8, label='fast')
  ax.plot(t, sigs['ref'],       'c-',  lw=1.0, label='ref')
  ax.plot(t, sigs['threshold'], 'r--', lw=0.6, alpha=0.7, label='ref × k')
  ax.set_ylabel('level'); ax.set_title('Envelopes')
  ax.legend(loc='upper right', fontsize=8)

  ax = axes[2]
  ax.plot(t, np.clip(sigs['ratio'], 0, 5), 'm-', lw=0.5, alpha=0.7)
  ax.axhline(1.4, color='r',    ls='--', lw=1,   label='k')
  ax.axhline(1.0, color='gray', ls=':',  lw=0.5)
  ax.set_ylim(0, 5); ax.set_ylabel('fast / ref')
  ax.set_title('Ratio (fires when crossing red while above floor)')
  ax.legend(loc='upper right', fontsize=8)


# ============================================================
# Driver  — usually no edits needed
# ============================================================

TEST_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'test_audio')
TEST_FILES = [
  'Longer Bass Notes.wav',
  'bass notes bad trigger 2.wav',
  'Bass Notes Bad Trigger.wav',
]

# Figure sizing — inches.  Each new panel adds PANEL_HEIGHT; the FIG_BASE
# leaves room for the suptitle and bottom xlabel/margins.
FIG_WIDTH    = 13.0
FIG_BASE     = 2.0
PANEL_HEIGHT = 2.0


def make_figure(num_panels, title):
  """Sharex'd vertical stack of subplots.  Sharex is what makes scroll-zoom
  and toolbar Home propagate across panels."""
  height = FIG_BASE + PANEL_HEIGHT * num_panels
  fig, axes = plt.subplots(num_panels, 1, sharex=True,
                           figsize=(FIG_WIDTH, height))
  if num_panels == 1: axes = [axes]
  fig.suptitle(title, fontsize=12)
  return fig, axes


def overlay_fire_markers(axes, audio, fires, t):
  """Thin red verticals across every panel + big red dots on the audio panel."""
  for ax in axes:
    for f in fires:
      ax.axvline(t[f], color='red', lw=0.5, alpha=0.35)
  if len(fires) > 0:
    axes[0].plot(t[fires], audio[fires], 'ro', ms=8, alpha=0.8,
                 label=f'fires ({len(fires)})')
    axes[0].legend(loc='upper right', fontsize=8)


def finish_figure(fig, axes, t):
  """Grid on every panel, xlabel on the bottom one, full x-range, zoom handler."""
  for ax in axes: ax.grid(True, alpha=0.3)
  axes[-1].set_xlabel('time (s)')
  axes[0].set_xlim(0, t[-1])
  plt.tight_layout(rect=[0, 0.02, 1, 0.97])
  plt.subplots_adjust(hspace=0.3)
  install_x_zoom(fig, 0, t[-1])


def run(input_path):
  # --- data ---
  name = os.path.basename(input_path)
  sr, audio = load_audio_mono(input_path)
  t = np.arange(len(audio)) / sr
  sigs = compute(audio, sr)
  sigs['audio'] = audio
  fires = sigs['fires']
  print(f"{name}: {len(fires)} fires, sr={sr}, dur={t[-1]:.2f}s")

  # --- figure ---
  fig, axes = make_figure(NUM_PANELS, name)
  plot_panels(axes, sigs, t)              # your content
  overlay_fire_markers(axes, audio, fires, t)
  finish_figure(fig, axes, t)


# ----- Parameters live here for PyCharm runs -----
files_to_run = TEST_FILES

if __name__ == '__main__':
  for filename in files_to_run:
    run(os.path.join(TEST_DIR, filename))
  plt.show()
