"""
keybass_1 Step 1 — pure-sensing diagnostic (no synthesis, sample resolution).

Tests the core hypothesis from keybass_1.md: that qualified same-polarity extrema
in the bass signal reliably mark one period (and the 2nd same-polarity extremum
after the attack gives the first period estimate), well before YIN locks.

Chain (all reusing the now-shared blocks): audio -> input_lpf -> attack_detector
(fast_env, trigger), and YIN (yd.P / aperiodicity) for comparison. A pure-numpy
extremum detector then finds + qualifies extrema (curvature side / fast_env
threshold / refractory), self-calibrates anchor polarity per note, and measures
peak-to-peak period. Parabolic interp + fractional pulse placement are Step 2.

Run from PyCharm (scipy env). No CLI args; config vars at the bottom. Uses the
diagnostic_plot toolset. See docs/python_experimentation.md and keybass_1.md.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'python'))
from lib.diagnostic_plot import install_x_zoom, load_audio_mono, mark_events, event_indices
from lib.audio_buf_tools import run_faust

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import lfilter, butter, sosfilt

# YIN pybind module from the sibling project (build it: cd ../yin && make -f yin.make).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'yin'))
try:
  from build.pybind_yin import yin
except ImportError:
  yin = None

DSP_FAUST = os.path.join(os.path.dirname(__file__), '..', '..', 'dsp_faust')

def detect_extrema(x, fast_env, sr, k_qual, deriv_lp_ms, refractory_ms):
  """Qualified extrema of x as derivative zero-crossings. Returns (pos_idx,
  neg_idx, d_lp). Qualifiers: curvature opposite-signed to value (a positive max /
  negative min), |value| > fast_env*k_qual, and a per-polarity refractory gap."""
  d = np.gradient(x)
  a = np.exp(-1.0 / max(1e-6, deriv_lp_ms * 1e-3 * sr))   # one-pole smoother
  d_lp = lfilter([1.0 - a], [1.0, -a], d)

  # Crossing of the smoothed derivative between samples j and j+1.
  maxc = np.where((d_lp[:-1] > 0) & (d_lp[1:] <= 0))[0]   # + -> -  : local max
  minc = np.where((d_lp[:-1] < 0) & (d_lp[1:] >= 0))[0]   # - -> +  : local min
  mk = maxc + (x[maxc + 1] > x[maxc]).astype(int)         # snap to the larger sample
  nk = minc + (x[minc + 1] < x[minc]).astype(int)

  # Qualify: right side of zero + prominent vs the envelope.
  mk = mk[(x[mk] > 0) & (x[mk] > fast_env[mk] * k_qual)]
  nk = nk[(x[nk] < 0) & (-x[nk] > fast_env[nk] * k_qual)]

  refr = int(refractory_ms * 1e-3 * sr)
  def refract(idx):
    out = []; last = -(1 << 30)
    for k in idx:
      if k - last >= refr:
        out.append(k); last = k
    return np.array(out, dtype=int)
  return refract(mk), refract(nk), d_lp

def per_note_table(trig_idx, pos_idx, neg_idx, f0_yin, sr, n):
  """For each note onset: anchor polarity (1st qualified extremum after trigger),
  the 1st->2nd same-polarity interval as the first period, vs YIN at that time."""
  allk = np.concatenate([pos_idx, neg_idx])
  pol = np.concatenate([np.ones(len(pos_idx)), -np.ones(len(neg_idx))])
  order = np.argsort(allk); allk = allk[order]; pol = pol[order]
  print(f"\n{'trig(s)':>8} {'pol':>4} {'1st(s)':>8} {'2nd(s)':>8} "
        f"{'P(smp)':>7} {'f0_pk':>7} {'f0_yin':>7}")
  bounds = list(trig_idx) + [n]
  for i, t0 in enumerate(trig_idx):
    seg = (allk >= t0) & (allk < bounds[i + 1])
    ks, ps = allk[seg], pol[seg]
    if len(ks) == 0:
      print(f"{t0/sr:8.3f} {'--':>4}  (no qualified extrema before next onset)"); continue
    apol = ps[0]
    same = ks[ps == apol]
    row = f"{t0/sr:8.3f} {('+ ' if apol>0 else '- '):>4} {same[0]/sr:8.3f}"
    if len(same) >= 2:
      P = same[1] - same[0]; t2 = same[1]
      fy = f0_yin[t2] if t2 < n else np.nan
      print(f"{row} {same[1]/sr:8.3f} {P:7d} {sr/P:7.1f} {fy:7.1f}")
    else:
      print(f"{row} {'--':>8}  (only one same-polarity extremum)")

def run(in_file, fc, det_fc, det_order, k_qual, deriv_lp_ms, refractory_ms, conf_gate):
  sr, audio = load_audio_mono(in_file)
  n = len(audio); t = np.arange(n) / sr

  # Audio-path anti-HF (broad). YIN runs on this, like the pitch shifter.
  lpf = run_faust(audio.astype(np.float32), os.path.join(DSP_FAUST, 'input_lpf.dsp'),
                  params={'fc': fc}, sr=sr)
  # Detection-path low-pass — much more aggressive, to strip the attack-region HF
  # (~2 kHz) that causes false extrema. Causal (sosfilt) so its group delay is
  # honest. Feeds BOTH the attack detector and the extremum detector, so fast_env
  # and the extrema share a scale. (Prototype stand-in for a real filter block.)
  det = sosfilt(butter(det_order, det_fc, btype='low', fs=sr, output='sos'),
                lpf).astype(np.float32)

  atk = run_faust(det, os.path.join(DSP_FAUST, 'attack_detector.dsp'),
                  sr=sr, all_outputs=True)
  trigger, fast_env = atk[0], atk[2]

  f0_yin = np.full(n, np.nan)
  if yin is not None:
    yd = yin(); yd.init(sr); yd.process_chunk(lpf.astype(np.float32))
    P = yd.get_buffer('yd.P', n); conf = 1.0 - yd.get_buffer('yd.aperiodicity', n)
    good = (P > 0) & (conf >= conf_gate)
    f0_yin[good] = sr / P[good]
  else:
    print("yin module not built — skipping YIN overlay (cd ../yin && make -f yin.make)")

  pos_idx, neg_idx, d_lp = detect_extrema(det, fast_env, sr, k_qual, deriv_lp_ms, refractory_ms)
  trig_idx = event_indices(trigger)
  per_note_table(trig_idx, pos_idx, neg_idx, f0_yin, sr, n)

  def stream_f0(idx):
    if len(idx) < 2: return idx[:0], idx[:0]
    return idx[1:], sr / np.diff(idx)

  fig, ax = plt.subplots(3, 1, figsize=(15, 9), sharex=True)
  ax[0].plot(t, det, lw=0.5, color='0.6'); ax[0].set_ylabel('det + extrema')
  ax[0].plot(t, fast_env, lw=0.8, color='C2', label='fast_env')
  ax[0].plot(t, fast_env * k_qual, lw=0.6, color='C2', ls=':', label=f'fast_env*{k_qual:g}')
  ax[0].plot(t, -fast_env * k_qual, lw=0.6, color='C2', ls=':')
  ax[0].plot(t[pos_idx], det[pos_idx], '^', ms=5, color='C3', label='pos extremum')
  ax[0].plot(t[neg_idx], det[neg_idx], 'v', ms=5, color='C0', label='neg extremum')
  ax[0].legend(loc='upper right', ncol=2)

  ax[1].plot(t, d_lp, lw=0.5, color='C4'); ax[1].axhline(0, color='0.7', lw=0.6)
  ax[1].set_ylabel('d/dt (LP)')

  pk_t, pk_f0 = stream_f0(pos_idx); nk_t, nk_f0 = stream_f0(neg_idx)
  ax[2].plot(t, f0_yin, lw=1.2, color='C1', label='YIN f0')
  ax[2].plot(t[pk_t], pk_f0, '.', ms=4, color='C3', label='pos peak-to-peak f0')
  ax[2].plot(t[nk_t], nk_f0, '.', ms=4, color='C0', label='neg peak-to-peak f0')
  ax[2].set_ylabel('f0 (Hz)'); ax[2].set_ylim(0, 400); ax[2].set_xlabel('s')
  ax[2].legend(loc='upper right', ncol=3)

  mark_events(ax, t, trigger, color='orange', lw=0.9, label='attack')
  ax[0].set_xlim(0, t[-1])
  for a in ax: a.grid(True, alpha=0.3)
  fig.tight_layout()
  install_x_zoom(fig, x_min=0.0, x_max=t[-1])
  plt.show()

if __name__ == '__main__':
  in_file       = "Bass Notes Bad Trigger 2.wav"
  fc            = 10000.0   # input_lpf (audio path + YIN), Hz
  det_fc        = 1000.0    # detection low-pass cutoff, Hz (aggressive — strips ~2 kHz attack HF)
  det_order     = 4         # detection low-pass order (Butterworth)
  k_qual        = 0.5       # qualify extremum if |value| > fast_env * k_qual
  deriv_lp_ms   = 0.2       # one-pole smoothing of the derivative (noise immunity)
  refractory_ms = 3.0       # per-polarity min gap (~just under min expected period)
  conf_gate     = 0.5       # mask YIN f0 below this confidence
  run(in_file, fc, det_fc, det_order, k_qual, deriv_lp_ms, refractory_ms, conf_gate)
