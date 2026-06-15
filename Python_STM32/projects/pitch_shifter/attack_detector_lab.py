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
def env_ar_2attack_hold(x, att_c_slow, att_c_fast, att_slow_samples,
                        rel_c_hold, rel_c_drop, rel_hold_samples):
  """AR follower with a two-stage attack AND a two-stage release.

     Attack: for the first att_slow_samples after entering attack mode, rise
     with att_c_slow (slow — lets x pull ahead so x/y opens a wider gap at the
     transient); then switch to att_c_fast so y catches up to x (closing the
     ratio back down — this is the trigger holdoff). The attack timer resets
     each time y re-enters attack mode (x rises above y after a fall).

     Release: hold-rate (rel_c_hold) for the first rel_hold_samples after a
     peak, then drop-rate (rel_c_drop) — same as env_ar_hold."""
  y = np.empty_like(x)
  prev = 0.0
  atk_timer = 0.0
  rel_timer = 0.0
  rising = False
  for i in range(len(x)):
    if x[i] > prev:
      if not rising:
        atk_timer = 0.0          # just entered attack mode — restart slow window
        rising = True
      c = att_c_slow if atk_timer < att_slow_samples else att_c_fast
      prev = c * prev + (1.0 - c) * x[i]
      atk_timer += 1.0
      rel_timer = 0.0
    else:
      rising = False
      c = rel_c_hold if rel_timer < rel_hold_samples else rel_c_drop
      prev = c * prev
      rel_timer += 1.0
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
# Peak-tracking fast env vs two-stage-attack ref env. Fire on a rising edge of
# fast/ref across a threshold that boosts on each fire and decays back (see the
# trigger block in compute). Keep the (audio, sr) -> dict contract.

def compute(audio, sr):
  x = audio.astype(np.float64)

  # fast: instant-attack peak track on |audio| with hold + accel release.
  # Hold ≥ one low-E period (24 ms) eliminates per-cycle wobble.
  fast_hold_s = 0.025
  fast_rel_s  = 0.050
  fast = env_peak_hold_accel(np.abs(x),
                             hold_samples=fast_hold_s * sr,
                             log_rel_c=np.log(tau_to_c(fast_rel_s, sr)))

  # ref: edge-detector reference.  Two-stage attack — slow for a brief window
  # after entering attack mode so fast pulls ahead and fast/ref opens a WIDER
  # gap at the transient (stronger detection), then fast so ref catches up to
  # fast (closing the ratio back down = trigger holdoff).  Release holds
  # briefly then drops fast so ref dives along with fast between notes — a new
  # attack always sees a low ref and gets a clean ratio spike, regardless of
  # how loud the previous note was.
  ref_att_slow_s  = 0.050          # slow initial attack — widens the gap at onset
  ref_att_fast_s  = 0.015          # quick catch-up after the slow window (holdoff)
  ref_att_slow_dur_s = 0.012       # how long ref stays in slow attack after onset
  ref_hold_s      = 0.025          # plateau matches one low-E period
  ref_hold_rel_s  = 1.000          # essentially "hold" — long TC during plateau
  ref_drop_s      = 0.050          # fall rate past the plateau
  ref = env_ar_2attack_hold(fast,
                    att_c_slow      = tau_to_c(ref_att_slow_s,  sr),
                    att_c_fast      = tau_to_c(ref_att_fast_s,  sr),
                    att_slow_samples= ref_att_slow_dur_s * sr,
                    rel_c_hold      = tau_to_c(ref_hold_rel_s,  sr),
                    rel_c_drop      = tau_to_c(ref_drop_s,      sr),
                    rel_hold_samples= ref_hold_s * sr)

  # Trigger: rising edge of the ratio across a LIVE threshold k(t). k rests at
  # k_nom; each fire snaps it up to k_boost, then it decays back toward k_nom
  # (k_decay_s TC). Testing the edge against the moving threshold means a
  # sustained-high ratio produces no new edge as k decays — the boost IS the
  # holdoff, no debounce needed. Level-independent: k rests at a fixed nominal
  # value, only the post-fire holdoff is time-varying.
  k_nom     = 2.0          # resting threshold
  k_boost   = 20.0         # threshold snaps here on each fire
  k_decay_s = 0.020        # boost decay time constant (s)
  ratio     = fast / np.maximum(ref, 1e-12)

  # Plain Python loop is fine here — the heavy lifting is in the envelopes.
  decay_c    = tau_to_c(k_decay_s, sr)
  k          = np.empty(len(ratio))
  fires      = []
  cur_k      = k_nom
  prev_ratio = 0.0
  for i in range(len(ratio)):
    if ratio[i] > cur_k and prev_ratio <= cur_k:    # rising edge across live threshold
      fires.append(i)
      cur_k = k_boost
    else:
      cur_k = (cur_k - k_nom) * decay_c + k_nom     # decay back toward k_nom
    prev_ratio = ratio[i]
    k[i] = cur_k

  return {
    'fast':      fast,
    'ref':       ref,
    'ratio':     ratio,
    'k':         k,                 # live threshold (in ratio units)
    'threshold': ref * k,           # threshold in level units (plot against fast)
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
  ax.plot(t, sigs['fast'], 'r-',  lw=0.8, label='fast')
  ax.plot(t, sigs['ref'], 'c-',  lw=1.0, label='ref')
  ax.plot(t, sigs['threshold'], 'r--', lw=0.6, alpha=0.7, label='ref × k')
  ax.set_ylabel('level'); ax.set_title('Envelopes')
  ax.legend(loc='upper right', fontsize=8)

  ax = axes[2]
  ax.plot(t, np.clip(sigs['ratio'], 0, 20), 'm-', lw=0.5, alpha=0.7, label='fast/ref ratio')
  ax.plot(t, sigs['k'], 'r--', lw=1, label='k (live threshold)')
  ax.set_ylim(0, 20); ax.set_ylabel('fast / ref')
  ax.set_title('Ratio vs live threshold — fire when ratio crosses k (k boosts on each fire, then decays)')
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
