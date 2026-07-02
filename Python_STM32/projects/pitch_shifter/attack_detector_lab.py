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

@njit
def tau_to_c(tau_s, sr):
  """Time constant in seconds → one-pole per-sample coefficient.
     tau=0 → 0.0 (instant: prev←x); tau→∞ → 1.0 (frozen / perfect hold)."""
  den = tau_s * sr
  return 0.0 if den == 0 else np.exp(-1.0 / den)

# Every follower below takes its time constants in SECONDS plus sr (default
# 48 kHz) and calls tau_to_c internally — callers pass times, never coefficients.
# An attack time of 0 s is an instantaneous peak track (prev←x); a hold/release
# time of np.inf is a perfect plateau (coefficient 1.0). That subsumes what used
# to be separate peak-hold followers: a flat-hold peak env is just env_ar_hold
# with att_s=0 and rel_hold_s=inf.

@njit
def env_ar(x, att_s, rel_s, sr=48000.0):
  """Asymmetric attack/release one-pole follower.
     Rises toward x with att_s; decays geometrically with rel_s."""
  att_c = tau_to_c(att_s, sr)
  rel_c = tau_to_c(rel_s, sr)
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
def env_ar_hold(x, att_s, rel_hold_s, rel_drop_s, hold_s, sr=48000.0):
  """AR follower with a two-stage release: hold-rate (rel_hold_s) for the first
     hold_s after a peak, then drop-rate (rel_drop_s) thereafter.  rel_hold_s=inf
     is a true plateau; att_s=0 makes it an instant peak track (the old
     env_peak_hold_drop = env_ar_hold(att_s=0, rel_hold_s=inf))."""
  att_c        = tau_to_c(att_s, sr)
  rel_c_hold   = tau_to_c(rel_hold_s, sr)
  rel_c_drop   = tau_to_c(rel_drop_s, sr)
  hold_samples = hold_s * sr
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
def env_ar_2attack_hold(x, att_slow_s, att_fast_s, att_slow_dur_s,
                        rel_hold_s, rel_drop_s, rel_hold_dur_s, sr=48000.0):
  """AR follower with a two-stage attack AND a two-stage release.

     Attack: for the first att_slow_dur_s after entering attack mode, rise with
     att_slow_s (slow — lets x pull ahead so x/y opens a wider gap at the
     transient); then switch to att_fast_s so y catches up to x (closing the
     ratio back down — this is the trigger holdoff). The attack timer resets
     each time y re-enters attack mode (x rises above y after a fall).

     Release: hold-rate (rel_hold_s) for the first rel_hold_dur_s after a peak,
     then drop-rate (rel_drop_s) — same as env_ar_hold."""
  att_c_slow       = tau_to_c(att_slow_s, sr)
  att_c_fast       = tau_to_c(att_fast_s, sr)
  att_slow_samples = att_slow_dur_s * sr
  rel_c_hold       = tau_to_c(rel_hold_s, sr)
  rel_c_drop       = tau_to_c(rel_drop_s, sr)
  rel_hold_samples = rel_hold_dur_s * sr
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
def rms_env(x, window_s, sr=48000.0):
  """One-pole RMS: leaky integrator on x² then sqrt.  Mirror of the Faust
     rms_env (x*x : onepole : sqrt).  window_s is the averaging time constant."""
  coeff = tau_to_c(window_s, sr)
  y = np.empty_like(x)
  prev = 0.0
  for i in range(len(x)):
    prev = (1.0 - coeff) * (x[i] * x[i]) + coeff * prev
    y[i] = np.sqrt(prev)
  return y

@njit
def env_hold_blend(x, att_s, rel_s, hold_s, sr=48000.0):
  """Attack/hold/release follower — mirror of the Faust env_hold.  Attack like
     env_ar; on release the coefficient ramps from 1.0 (perfect hold) at the
     peak to rel_s after hold_s, so recent peaks plateau then fall."""
  att_c        = tau_to_c(att_s, sr)
  rel_c        = tau_to_c(rel_s, sr)
  hold_samples = hold_s * sr
  y = np.empty_like(x)
  prev = 0.0
  timer = 0.0
  for i in range(len(x)):
    if x[i] > prev:
      prev = att_c * prev + (1.0 - att_c) * x[i]
      timer = 0.0
    else:
      timer += 1.0
      hold_factor = min(1.0, timer / hold_samples)
      eff_rel = 1.0 - hold_factor * (1.0 - rel_c)
      prev = eff_rel * prev
    y[i] = prev
  return y

@njit
def env_ar_accel(x, att_s, rel_s, hold_s, sr=48000.0):
  """AR follower with a continuously-accelerating release.  Rises toward x with
     att_s (att_s=0 = instant peak track); on release the effective TC shrinks as
     (t/hold_s)^2 — perfect hold near a peak, then faster-than-exponential decay
     past hold_s.  Mirror of the Faust env_hold_accel.  The release is not a fixed
     coefficient, so it can't reduce to env_ar_hold — but the interface matches."""
  att_c        = tau_to_c(att_s, sr)
  hold_samples = hold_s * sr
  log_rel_c    = np.log(tau_to_c(rel_s, sr))
  y = np.empty_like(x)
  prev = 0.0
  timer = 0.0
  for i in range(len(x)):
    if x[i] > prev:
      prev = att_c * prev + (1.0 - att_c) * x[i]
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
  fast = env_ar_accel(np.abs(x), 0.0, fast_rel_s, fast_hold_s, sr)

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
  ref = env_ar_2attack_hold(fast, ref_att_slow_s, ref_att_fast_s, ref_att_slow_dur_s,
                            ref_hold_rel_s, ref_drop_s, ref_hold_s, sr)

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

  # Dive path (note-end detector → active_gain muting in loop_controller). A
  # slow natural-decay reference vs a recent-peak hold envelope, both on RMS;
  # when hold falls below slow the note is ending → dive_strength rises →
  # active_gain (= 1 − dive_strength) dips. Mirror of the Faust dive path.
  rms_window        = 0.025        # short-term energy window (~one low-E period)
  hold_attack       = 0.005
  hold_fast_release = 0.050
  slow_release      = 1.000        # ≈ bass-string ring-down
  eps               = 1.0e-9

  rms      = rms_env(x, rms_window, sr)
  hold_env = env_ar_hold(rms, hold_attack, slow_release/2, hold_fast_release, 28e-3, sr)
  slow_env = env_ar(rms, hold_attack, slow_release, sr)

  # active_gain = short-term / slow envelope ratio — the detector side of a
  # program-adaptive gate. Algebraically 1 − (slow−hold)/slow, i.e. the same
  # quantity as the old dive_strength, in its natural (clean-looking) form.
  active_gain   = np.clip(hold_env / (slow_env + eps), 0.0, 1.0)
  dive_strength = 1.0 - active_gain

  return {
    'fast':               fast,
    'ref':                ref,
    'ratio':              ratio,
    'k':                  k,             # live threshold (in ratio units)
    'threshold':          ref * k,       # threshold in level units (plot against fast)
    'rms':                rms,
    'slow_env':           slow_env,
    'hold_env':           hold_env,
    'dive_strength':      dive_strength,
    'active_gain':        active_gain,
    'fires':              np.array(fires, dtype=np.int64),
  }


# ============================================================
# Plot panels  — EDIT THIS to match the signals you return
# ============================================================
# axes is a list of NUM_PANELS already-sharex'd matplotlib Axes.
# sigs[<name>] is whatever you put in compute()'s return dict, plus
# sigs['audio'] which the driver adds for convenience.
# Fire markers and the scroll-wheel zoom are added by the driver.

NUM_PANELS = 5

def plot_panels(axes, sigs, t):
  ax = axes[0]
  ax.plot(t, sigs['audio'], 'b-', lw=0.3, alpha=0.5)
  ax.set_ylabel('amplitude'); ax.set_title('Input waveform')

  ax = axes[1]
  # ref × k spikes to k_boost× ref on every fire; clip it and pin the y-range to
  # the envelope level so fast/ref stay readable (the boost dynamics live in the
  # ratio panel below).
  ymax = float(np.max(sigs['fast'])) * 1.1 + 1e-9
  ax.plot(t, sigs['fast'], 'r-',  lw=0.8, label='fast')
  ax.plot(t, sigs['ref'], 'c-',  lw=1.0, label='ref')
  ax.plot(t, np.clip(sigs['threshold'], 0, ymax), 'r--', lw=0.6, alpha=0.7, label='ref × k (clipped)')
  ax.set_ylim(0, ymax)
  ax.set_ylabel('level'); ax.set_title('Envelopes')
  ax.legend(loc='upper right', fontsize=8)

  ax = axes[2]
  ax.plot(t, np.clip(sigs['ratio'], 0, 20), 'm-', lw=0.5, alpha=0.7, label='fast/ref ratio')
  ax.plot(t, sigs['k'], 'r--', lw=1, label='k (live threshold)')
  ax.set_ylim(0, 20); ax.set_ylabel('fast / ref')
  ax.set_title('Ratio vs live threshold — fire when ratio crosses k (k boosts on each fire, then decays)')
  ax.legend(loc='upper right', fontsize=8)

  ax = axes[3]
  ax.plot(t, sigs['rms'], color='0.7', lw=0.5, alpha=0.6, label='rms (25 ms)')
  ax.plot(t, sigs['hold_env'], 'r-', lw=0.9, label='hold_env (short-term)')
  ax.plot(t, sigs['slow_env'], 'b-', lw=1.0, label='slow_env (reference)')
  ax.set_ylabel('level'); ax.set_title('Dive envelopes — short-term RMS vs slow reference')
  ax.legend(loc='upper right', fontsize=8)

  ax = axes[4]
  ax.plot(t, sigs['active_gain'], 'g-', lw=1.2, label='active_gain = hold_env / slow_env')
  ax.set_ylim(-0.05, 1.05); ax.set_ylabel('gain')
  ax.set_title('Note-end gate — fast/slow envelope ratio')
  ax.legend(loc='upper right', fontsize=8)


# ============================================================
# Driver  — usually no edits needed
# ============================================================

TEST_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'test_audio')
TEST_FILES = [
  'Longer Bass Notes.wav',
  'bass notes bad trigger 2.wav',
  'Bass Notes Bad Trigger.wav',
  'Fourth Test.wav'
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
