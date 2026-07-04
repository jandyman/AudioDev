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
from numpy.lib.stride_tricks import sliding_window_view

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


@njit
def onepole_smooth(x, tau_s, sr=48000.0):
  """Symmetric one-pole smoother — tracks x in both directions (unlike env_ar,
     whose release decays toward zero).  For smoothing signed signals."""
  c = tau_to_c(tau_s, sr)
  y = np.empty_like(x)
  prev = x[0]
  for i in range(len(x)):
    prev = c * prev + (1.0 - c) * x[i]
    y[i] = prev
  return y

@njit
def onepole_asym(x, up_s, down_s, sr=48000.0):
  """One-pole with different time constants rising vs falling.  For the gate:
     close fast (down_s), reopen slowly (up_s) — a soft anti-flutter, so a
     stepwise note-end (slope crossing the knee repeatedly) reads as one
     descent instead of popping back open between steps."""
  c_up   = tau_to_c(up_s, sr)
  c_down = tau_to_c(down_s, sr)
  y = np.empty_like(x)
  prev = x[0]
  for i in range(len(x)):
    c = c_up if x[i] > prev else c_down
    prev = c * prev + (1.0 - c) * x[i]
    y[i] = prev
  return y

@njit
def gate_smooth_pin(x, pin, up_s, down_s, sr=48000.0):
  """onepole_asym with an attack snap: the input is max(x, pin) AND the state
     JUMPS up to pin wherever pin exceeds it.  A detected attack re-opens the
     gate instantly and the onset-pin plateau masks the transient's fast
     settle; when the pin fades the gate hands off to the (by then meaningful)
     damp evidence at its own level — no sag-and-recover after onset."""
  c_up   = tau_to_c(up_s, sr)
  c_down = tau_to_c(down_s, sr)
  y = np.empty_like(x)
  state = x[0]
  for i in range(len(x)):
    xi = x[i] if x[i] > pin[i] else pin[i]
    c = c_up if xi > state else c_down
    state = c * state + (1.0 - c) * xi
    if pin[i] > state:
      state = pin[i]
    y[i] = state
  return y


# ============================================================
# Lab pitch tracker — offline stand-in for the YIN block's latched P
# ============================================================
# The rev-3 dive path (attack_detector_design_notes.md) sizes its energy window
# to the note's period. In the pipeline that P comes from the YIN detector via
# loop_controller's latch; the lab computes its own offline equivalent so the
# dive redesign can be prototyped without the graph: decimate ÷8, frame-based
# CMNDF (YIN), then a per-sample latch that accepts confident frames, holds
# through dips, and resets to the 25 ms fallback on each fire (mirroring
# "invalidate on attack — new note, P unknown").

def fir_decimate(x, dec=8, numtaps=64):
  """Windowed-sinc anti-alias LPF + downsample; cutoff 0.8·(nyquist/dec)."""
  fc = 0.8 / dec
  n = np.arange(numtaps) - (numtaps - 1) / 2
  h = fc * np.sinc(fc * n) * np.hanning(numtaps)
  h /= h.sum()
  return np.convolve(x, h)[(numtaps - 1) // 2:][::dec]

def yin_frames(xd, w, tau_max, hop, pick_thresh, max_lag):
  """Frame-based YIN on the decimated signal.  Returns per-frame start/end
     sample indices (decimated), period estimates (decimated samples,
     parabolic-refined) and the CMNDF minimum (confidence, low = good).
     max_lag caps the doubled-lag preference (the energy-window cap)."""
  frame_len = w + tau_max
  n_frames = max(0, (len(xd) - frame_len) // hop)
  starts  = np.arange(n_frames) * hop
  periods = np.zeros(n_frames)
  confs   = np.ones(n_frames)
  e_db    = np.full(n_frames, -120.0)
  if n_frames == 0:
    return starts, starts, periods, confs, e_db
  wins = sliding_window_view(xd, w)              # wins[t] = xd[t:t+w]
  taus = np.arange(1, tau_max + 1)
  for f in range(n_frames):
    s = starts[f]
    e_db[f] = 10.0 * np.log10(np.mean(wins[s] ** 2) + 1e-30)
    d = ((wins[s][None, :] - wins[s + 1:s + tau_max + 1]) ** 2).sum(axis=1)
    cm = d * taus / np.maximum(np.cumsum(d), 1e-30)
    below = np.nonzero(cm < pick_thresh)[0]
    if len(below):                               # first dip below → walk to its local min
      p = below[0]
      while p + 1 < len(cm) and cm[p + 1] < cm[p]:
        p += 1
    else:
      p = int(np.argmin(cm))
    # Prefer the doubled lag whenever it is also a deep null (and fits the
    # window cap). On a 2H-dominant note the first dip is at P/2 — sometimes
    # even deeper than P (pitch drift decorrelates the longer lag) — and a
    # P/2 window leaves the fundamental rippling. The costs are asymmetric:
    # doubling a true period is harmless (a 2-period window is still
    # commensurate), halving is what hurts, so always take the deep double.
    p2_lo = max(p + 1, 2 * p + 1 - max(2, p // 8))
    p2_hi = 2 * p + 2 + max(2, p // 8)
    if p2_hi < min(len(cm), max_lag):
      p2 = p2_lo + int(np.argmin(cm[p2_lo:p2_hi]))
      if cm[p2] < pick_thresh:
        p = p2
    confs[f] = cm[p]
    tau = float(taus[p])
    if 0 < p < len(cm) - 1:                      # parabolic sub-sample refinement
      a, b, c = cm[p - 1], cm[p], cm[p + 1]
      den = a - 2 * b + c
      if den > 0:
        tau += 0.5 * (a - c) / den
    periods[f] = tau
  return starts, starts + frame_len, periods, confs, e_db

@njit
def latch_period(n, f_start, f_end, f_p, f_conf, f_edb, fires,
                 conf_ok, e_floor, fallback, p_min, p_max):
  """Per-sample latched period (full-rate samples).  A frame is accepted when
     it is confident, LOUD ENOUGH (quiet tails yield spuriously-confident junk
     lags that destroy window commensurability), plausibly ranged, and started
     after the last attack; the latch holds through dips and resets to the
     fallback on each fire."""
  out = np.empty(n)
  cur = fallback
  cand = -1.0                                    # pending candidate period
  fi = 0
  fr = 0
  last_fire = -1000000000
  for i in range(n):
    while fi < len(fires) and fires[fi] <= i:
      last_fire = fires[fi]
      cur = fallback                             # invalidate on attack
      cand = -1.0
      fi += 1
    while fr < len(f_end) and f_end[fr] <= i:
      if (f_conf[fr] < conf_ok and f_edb[fr] > e_floor and
          f_start[fr] > last_fire and p_min <= f_p[fr] <= p_max):
        p = f_p[fr]
        # two consecutive agreeing frames (±10%) before the latch moves —
        # an isolated junk frame can't destabilize the window
        if abs(p - cur) <= 0.1 * cur:
          cur = p                                # refinement of current latch
          cand = -1.0
        elif cand > 0.0 and abs(p - cand) <= 0.1 * cand:
          cur = p
          cand = -1.0
        else:
          cand = p
      fr += 1
    out[i] = cur
  return out

@njit
def onset_ref_track(p_db, fires, capture_s, cap_tau_s, up_tau_s, down_tau_s,
                    cap_floor_db, cap_range_db, sr=48000.0):
  """Leaky note-level onset reference (dB).  For capture_s after each fire it
     fast-tracks the level in BOTH directions, so it settles at the early-
     sustain level rather than the attack peak; afterwards it drifts up on
     undershoot (breaks the missed-attack → stale-reference loop) and leaks
     down only very slowly (volume-knob safety).  Capture is WEIGHTED BY LEVEL
     (the design notes' "weighted by attack confidence"): a spurious fire in a
     quiet tail must not drag the reference down to the noise floor, or
     alive_level reads 1 through the junk that follows."""
  c_cap  = tau_to_c(cap_tau_s, sr)
  c_up   = tau_to_c(up_tau_s, sr)
  c_down = tau_to_c(down_tau_s, sr)
  cap_n  = capture_s * sr
  out = np.empty_like(p_db)
  ref = p_db[0]
  fi = 0
  last_fire = -1000000000
  for i in range(len(p_db)):
    while fi < len(fires) and fires[fi] <= i:
      last_fire = fires[fi]
      fi += 1
    if i - last_fire < cap_n:
      w = (p_db[i] - cap_floor_db) / cap_range_db
      w = 0.0 if w < 0.0 else (1.0 if w > 1.0 else w)
      ref += (1.0 - c_cap) * w * (p_db[i] - ref)
    elif p_db[i] > ref:
      ref = c_up * ref + (1.0 - c_up) * p_db[i]
    else:
      ref = c_down * ref + (1.0 - c_down) * p_db[i]
    out[i] = ref
  return out


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
  # Release: fast already carries the 25 ms anti-ripple hold, so ref does NOT
  # need its own long plateau — a cascaded hold made ref lag ~60-100 ms after
  # a mute, and a 30 ms mute-to-attack gap (fast playing) arrived before ref
  # had fallen at all (the almost-missed 6.45 s attack in bad trigger 2).
  ref_att_slow_s  = 0.050          # slow initial attack — widens the gap at onset
  ref_att_fast_s  = 0.015          # quick catch-up after the slow window (holdoff)
  ref_att_slow_dur_s = 0.012       # how long ref stays in slow attack after onset
  ref_hold_s      = 0.010          # brief settle only — fast owns ripple defense
  ref_hold_rel_s  = 1.000          # essentially "hold" — long TC during plateau
  ref_drop_s      = 0.025          # dive along with fast between notes
  ref = env_ar_2attack_hold(fast, ref_att_slow_s, ref_att_fast_s, ref_att_slow_dur_s,
                            ref_hold_rel_s, ref_drop_s, ref_hold_s, sr)

  # Trigger: rising edge of the ratio across a LIVE threshold k(t). k rests at
  # k_nom; each fire snaps it to k_boost, HOLDS there through the transient
  # (k_hold_s), then drops back fast (k_drop_s TC). The hold-then-drop shape
  # replaces the old plain exponential: doubles are same-transient re-crossings
  # within ~1-20 ms (suppress brutally), real retriggers arrive 40+ ms later
  # (get out of the way fast) — the exponential was weak early and lingering
  # late, exactly backwards. A RE-ARM condition backs it up: a new edge only
  # counts after the ratio has dipped below k_nom since the last fire, so
  # doubles are suppressed by the CONTINUITY of the transient, timing-free —
  # an unlucky false fire can't mask a later real attack. Level-independent:
  # k rests at a fixed nominal value (level lives in the qualification below).
  k_nom     = 1.6          # resting threshold (shape sensitivity)
  k_boost   = 30.0         # threshold during the post-fire hold
  k_hold_s  = 0.015        # full suppression through the transient
  k_drop_s  = 0.008        # then drop back toward k_nom with this TC
  ratio     = fast / np.maximum(ref, 1e-12)

  # Level qualification — deliberately separate from k: k is the
  # level-INDEPENDENT shape holdoff; this term is level-DEPENDENT. A leaky
  # previous-note-strength memory sets the bar a candidate must approach;
  # string perturbations (fret rattle, brushes) sit far below the last real
  # note and get weighted out before edge detection. Soft: w ramps over
  # qual_band_db, so mid-note (w=1) nothing changes and a borderline-soft real
  # note still fires on a strong enough ratio spike. mem_floor_db is a
  # CONSTANT backstop (not a noise detector): the memory can't leak below it,
  # so qualification never opens up to digital silence / file-start junk.
  qual_rel_db  = -30.0     # bar sits this far below the note memory
  qual_band_db = 10.0      # soft transition width
  mem_att_s    = 0.030     # memory rises to a new note's level in ~this
  mem_leak_s   = 8.0       # slow leak (volume-knob / long-silence recovery)
  mem_floor_db = -45.0     # memory never leaks below this
  note_mem = env_ar(fast, mem_att_s, mem_leak_s, sr)
  mem_db   = np.maximum(20.0 * np.log10(note_mem + 1e-12), mem_floor_db)
  # Startup guard: the memory's initial condition is "a loud note just ended",
  # not "eternal silence" — start the bar high and leak it down, so pre-first-
  # note junk can't fire but a real first note (loud, near the bar) punches
  # through. Kills the known file-start fire cluster.
  mem_init_db, mem_init_leak_s = -10.0, 3.0
  init_ramp = mem_init_db + (mem_floor_db - mem_init_db) * \
              np.minimum(np.arange(len(x)) / (mem_init_leak_s * sr), 1.0)
  mem_db = np.maximum(mem_db, init_ramp)
  fast_db  = 20.0 * np.log10(fast + 1e-12)
  qual_w   = np.clip((fast_db - (mem_db + qual_rel_db)) / qual_band_db, 0.0, 1.0)
  ratio_q  = ratio * qual_w

  # Plain Python loop is fine here — the heavy lifting is in the envelopes.
  # Edge detection runs on the QUALIFIED ratio.
  drop_c     = tau_to_c(k_drop_s, sr)
  hold_n     = int(k_hold_s * sr)
  k          = np.empty(len(ratio_q))
  fires      = []
  cur_k      = k_nom
  prev_ratio = 0.0
  timer      = 10 ** 9
  armed      = True
  for i in range(len(ratio_q)):
    if armed and ratio_q[i] > cur_k and prev_ratio <= cur_k:
      fires.append(i)
      cur_k = k_boost
      timer = 0
      armed = False
    elif timer < hold_n:
      cur_k = k_boost                               # hold through the transient
      timer += 1
    else:
      cur_k = (cur_k - k_nom) * drop_c + k_nom      # then drop back fast
      timer += 1
    if not armed and ratio_q[i] < k_nom:            # re-arm: transient has ended
      armed = True
    prev_ratio = ratio_q[i]
    k[i] = cur_k
  fires_arr = np.array(fires, dtype=np.int64)

  # ------------------------------------------------------------------
  # Dive path, rev 3 (attack_detector_design_notes.md): period-commensurate
  # energy window → ripple-free log-envelope; decay-rate damp evidence ×
  # note-relative level evidence, soft product → active_gain. The previous
  # fast/slow RMS ratio is still computed (dashed in the gate panel) for A/B.
  # ------------------------------------------------------------------
  eps = 1.0e-12

  # Lab YIN stand-in → per-sample latched period = energy window length.
  dec          = 8
  sr_d         = sr / dec
  yin_w        = int(round(0.043 * sr_d))    # integration window ~43 ms
  yin_tau_max  = int(sr_d / 28.0)            # lowest trackable pitch ~28 Hz
  yin_hop      = int(round(0.005 * sr_d))    # new estimate every ~5 ms
  yin_pick     = 0.15                        # CMNDF first-below pick threshold
  yin_accept   = 0.20                        # latch accepts frames below this
  fallback_p_s = 0.025                       # window with no P (≈ one low-E period)

  win_cap_s = 0.032                          # energy-window cap (> one low-E period)
  frame_floor = -55.0                        # frames quieter than this can't latch
  xd = fir_decimate(x, dec)
  f_start, f_end, f_p, f_conf, f_edb = yin_frames(xd, yin_w, yin_tau_max, yin_hop,
                                                  yin_pick, int(win_cap_s * sr_d))
  latched = latch_period(len(x), f_start * dec, f_end * dec, f_p * dec, f_conf, f_edb,
                         fires_arr, yin_accept, frame_floor, fallback_p_s * sr,
                         sr / 400.0, win_cap_s * sr)
  window = np.clip(np.round(latched), 8, int(win_cap_s * sr)).astype(np.int64)

  # Period-commensurate mean power (true boxcar, exactly one period), in dB.
  # For a periodic signal this is constant — zero ripple by construction.
  idx = np.arange(len(x))
  cs = np.concatenate((np.zeros(1), np.cumsum(x * x)))
  lo = np.maximum(idx + 1 - window, 0)
  p_db = 10.0 * np.log10((cs[idx + 1] - cs[lo]) / np.maximum(idx + 1 - lo, 1) + eps)

  # Decay rate: energy of THIS period vs the period before it, as dB/s. Both
  # windows use the CURRENT latched length — comparing p_db[i] to p_db[i−W]
  # would compare values computed with two different window lengths whenever
  # the latch switches, and the switch reads as a huge spurious slope spike.
  # Natural bass ring-down ≈ −9 dB/s; a hand damp is orders faster. Smoothing
  # is deliberately heavy (25 ms): string-mode beating on 2H-dominant notes is
  # genuine ~20 Hz AM that no window can remove, swinging the raw slope to
  # ~±100 dB/s — while a real damp (−500+ dB/s) still crosses the knee in
  # well under 10 ms through this filter. Beat rejection is nearly free.
  lo2 = np.maximum(idx + 1 - 2 * window, 0)
  e_prev = (cs[lo] - cs[lo2]) / np.maximum(lo - lo2, 1)
  slope = (p_db - 10.0 * np.log10(e_prev + eps)) * sr / np.maximum(window, 1)
  slope = onepole_smooth(slope, 0.025, sr)

  # Note-level onset reference: early-sustain capture (30 ms, 8 ms TC, weighted
  # by level so quiet spurious fires barely move it) after each fire, then
  # upward drift (0.5 s) on undershoot, slow downward leak (10 s).
  onset_ref = onset_ref_track(p_db, fires_arr, 0.030, 0.008, 0.5, 10.0,
                              -50.0, 15.0, sr)

  # Soft memberships → active_gain (product; nothing hardens into a mode).
  s_edge   = -60.0    # slope ≥ this → decaying naturally (dB/s)
  s_damp   = -240.0   # slope ≤ this → certainly damped
  drop_hi  = 25.0     # fully alive down to onset − drop_hi (dB)
  drop_lo  = 45.0     # fully ended at onset − drop_lo (dB)
  floor_lo = -60.0    # absolute floor: fully dead below this (dBFS)
  floor_hi = -45.0    #                 fully alive above this
  alive_decay = np.clip((slope - s_damp) / (s_edge - s_damp), 0.0, 1.0)
  alive_level = np.clip(((p_db - onset_ref) + drop_lo) / (drop_lo - drop_hi), 0.0, 1.0)
  alive_floor = np.clip((p_db - floor_lo) / (floor_hi - floor_lo), 0.0, 1.0)

  # Onset pin: the first tens of ms after a fire are the transient's fast
  # multi-slope settle — genuinely −300 dB/s on percussive notes — which is
  # onset, not note-end; the attack just re-armed everything, so hold the gate
  # open through it (hold then decay). Scaled by the post-attack level so a
  # spurious fire in a quiet tail doesn't open the gate on junk. A real damp
  # has no fire, so muting speed is unaffected.
  pin_hold_s, pin_decay_s = 0.040, 0.040
  pin = np.zeros(len(x))
  n = len(x)
  for f in fires_arr:
    amp = alive_floor[min(f + int(0.005 * sr), n - 1)]
    e = min(n, f + int(pin_hold_s * sr))
    pin[f:e] = np.maximum(pin[f:e], amp)
    te = min(n, e + int(5 * pin_decay_s * sr))
    if te > e:
      pin[e:te] = np.maximum(pin[e:te], amp * np.exp(-np.arange(te - e) / (pin_decay_s * sr)))

  # Asymmetric smoothing: close fast, reopen slow — a stepwise note-end (slope
  # crossing the knee repeatedly) reads as one descent, not flutter. The pin
  # SNAPS the smoother state open (see gate_smooth_pin): no sag-and-recover
  # handoff after onset.
  active_gain = gate_smooth_pin(alive_decay * alive_level * alive_floor, pin,
                                0.050, 0.002, sr)
  dive_strength = 1.0 - active_gain

  # Previous dive path (fast/slow RMS envelope ratio) for the A/B overlay.
  rms      = rms_env(x, 0.025, sr)
  hold_env = env_ar_hold(rms, 0.005, 0.5, 0.050, 28e-3, sr)
  slow_env = env_ar(rms, 0.005, 1.0, sr)
  active_gain_old = np.clip(hold_env / (slow_env + 1e-9), 0.0, 1.0)

  return {
    'fast':               fast,
    'ref':                ref,
    'ratio':              ratio,
    'ratio_q':            ratio_q,                 # level-qualified ratio (drives fires)
    'qual_w':             qual_w,                  # level-qualification weight 0..1
    'qual_bar':           10.0 ** ((mem_db + qual_rel_db) / 20.0),  # bar in level units
    'k':                  k,                       # live threshold (ratio units)
    'threshold':          ref * k,                 # threshold in level units
    'latched_p_ms':       latched / sr * 1000.0,   # energy window (= latched P)
    'frame_t':            (f_end * dec) / sr,      # frame availability times (s)
    'frame_p_ms':         f_p * dec / sr * 1000.0,
    'frame_ok':           f_conf < yin_accept,
    'p_db':               p_db,
    'onset_ref':          onset_ref,
    'level_hi':           onset_ref - drop_hi,     # alive_level = 1 above this
    'level_lo':           onset_ref - drop_lo,     # alive_level = 0 below this
    'slope':              slope,
    's_edge':             s_edge,
    's_damp':             s_damp,
    'alive_decay':        alive_decay,
    'alive_level':        alive_level,
    'alive_floor':        alive_floor,
    'onset_pin':          pin,
    'active_gain':        active_gain,
    'dive_strength':      dive_strength,
    'active_gain_old':    active_gain_old,
    'fires':              fires_arr,
  }


# ============================================================
# Plot panels  — EDIT THIS to match the signals you return
# ============================================================
# axes is a list of NUM_PANELS already-sharex'd matplotlib Axes.
# sigs[<name>] is whatever you put in compute()'s return dict, plus
# sigs['audio'] which the driver adds for convenience.
# Fire markers and the scroll-wheel zoom are added by the driver.

NUM_PANELS = 7

def plot_panels(axes, sigs, t):
  ax = axes[0]
  ax.plot(t, sigs['audio'], 'b-', lw=0.3, alpha=0.5)
  ax.set_ylabel('amplitude'); ax.set_title('Input waveform')

  ax = axes[1]
  # dB axis: the qualification decisions live 25-45 dB down, invisible on a
  # linear axis. ref × k spikes to k_boost× ref on every fire; clip to the top
  # of the axis (the boost dynamics live in the ratio panel below).
  db = lambda v: 20.0 * np.log10(np.abs(v) + 1e-12)
  ax.plot(t, db(sigs['fast']), 'r-',  lw=0.8, label='fast')
  ax.plot(t, db(sigs['ref']), 'c-',  lw=1.0, label='ref')
  ax.plot(t, np.clip(db(sigs['threshold']), -80, 0), 'r--', lw=0.6, alpha=0.7, label='ref × k (clipped)')
  ax.plot(t, db(sigs['qual_bar']), 'g--', lw=0.8, alpha=0.8, label='qual bar (note_mem − 30 dB)')
  ax.set_ylim(-80, 0)
  ax.set_ylabel('dBFS'); ax.set_title('Envelopes (dB)')
  ax.legend(loc='upper right', fontsize=8)

  ax = axes[2]
  ax.plot(t, np.clip(sigs['ratio'], 0, 20), color='0.7', lw=0.4, alpha=0.7, label='fast/ref ratio (raw)')
  ax.plot(t, np.clip(sigs['ratio_q'], 0, 20), 'm-', lw=0.6, alpha=0.8, label='qualified ratio (fires)')
  ax.plot(t, sigs['k'], 'r--', lw=1, label='k (live threshold)')
  ax.set_ylim(0, 20); ax.set_ylabel('fast / ref')
  ax.set_title('Qualified ratio vs live threshold — fire when it crosses k (k boosts on each fire, then decays)')
  ax.legend(loc='upper right', fontsize=8)

  ax = axes[3]
  ok = sigs['frame_ok']
  ax.plot(sigs['frame_t'][~ok], sigs['frame_p_ms'][~ok], '.', color='0.8', ms=3, label='frame P (rejected)')
  ax.plot(sigs['frame_t'][ok], sigs['frame_p_ms'][ok], '.', color='g', ms=3, label='frame P (confident)')
  ax.plot(t, sigs['latched_p_ms'], 'b-', lw=1.0, label='latched P = energy window')
  ax.set_ylim(0, 40); ax.set_ylabel('ms')
  ax.set_title('Lab YIN → latched period (25 ms fallback, reset on attack)')
  ax.legend(loc='upper right', fontsize=8)

  ax = axes[4]
  ax.plot(t, sigs['p_db'], 'b-', lw=0.7, label='period-commensurate power (dB)')
  ax.plot(t, sigs['onset_ref'], 'r-', lw=1.0, label='onset reference')
  ax.plot(t, sigs['level_hi'], 'r--', lw=0.6, alpha=0.6, label='alive_level 1 → 0 band')
  ax.plot(t, sigs['level_lo'], 'r--', lw=0.6, alpha=0.6)
  ax.set_ylim(-90, 0); ax.set_ylabel('dB')
  ax.set_title('Commensurate-window energy vs leaky onset reference')
  ax.legend(loc='upper right', fontsize=8)

  ax = axes[5]
  ax.plot(t, np.clip(sigs['slope'], -300, 100), 'm-', lw=0.6, label='decay rate')
  ax.axhline(sigs['s_edge'], color='g', ls='--', lw=0.8, label='s_edge (natural)')
  ax.axhline(sigs['s_damp'], color='r', ls='--', lw=0.8, label='s_damp (damped)')
  ax.set_ylim(-300, 100); ax.set_ylabel('dB/s')
  ax.set_title('Decay rate — dB change across one period (alive_decay ramps between the lines)')
  ax.legend(loc='upper right', fontsize=8)

  ax = axes[6]
  ax.plot(t, sigs['alive_decay'], 'm-', lw=0.7, alpha=0.7, label='alive_decay (rate)')
  ax.plot(t, sigs['alive_level'], 'c-', lw=0.7, alpha=0.7, label='alive_level (vs onset)')
  ax.plot(t, sigs['alive_floor'], 'y-', lw=0.7, alpha=0.7, label='alive_floor (abs)')
  ax.plot(t, sigs['onset_pin'], 'r-', lw=0.6, alpha=0.5, label='onset pin')
  ax.plot(t, sigs['active_gain'], 'g-', lw=1.4, label='active_gain (new = product)')
  ax.plot(t, sigs['active_gain_old'], '--', color='0.5', lw=0.9, label='active_gain (old ratio)')
  ax.set_ylim(-0.05, 1.05); ax.set_ylabel('gain')
  ax.set_title('Note-end gate — soft memberships and their product, vs old fast/slow ratio')
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
