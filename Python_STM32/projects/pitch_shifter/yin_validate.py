"""
Validate the YIN detector block across a whole file: per note, compare the block's
decimated estimate (yd.P, confidence-gated) against a full-rate YIN ground truth,
and report each note's fundamental-vs-2nd-harmonic level so we can see whether any
wrong estimates line up with weak-fundamental (2H-dominant) notes. Print-only.

ratio = yd_Hz / true_Hz: ~1.0 = correct, ~2.0 = locked to 2nd harmonic
(half period), ~0.5 = octave-down error.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build'))
import numpy as np
import scipy.io.wavfile as wav
from build.pybind_pitch_shifter import pitch_shifter

def load_mono(path):
  sr, d = wav.read(path)
  x = d.astype(np.float64) / (32768.0 if d.dtype == np.int16 else
                              2147483648.0 if d.dtype == np.int32 else 1.0)
  return sr, (x[:, 0] if x.ndim > 1 else x)

def yin_f0(x, sr, fmin=40.0, fmax=400.0, thresh=0.15):
  """YIN — robust to weak fundamentals (prefers the true period, not 2H)."""
  x = x - x.mean()
  tau_max = int(sr / fmin); tau_min = max(2, int(sr / fmax))
  W = len(x) - tau_max
  if W <= 0 or np.sqrt(np.mean(x * x)) < 1e-4: return 0.0
  x0 = x[:W]
  d = np.zeros(tau_max + 1)
  for tau in range(tau_min, tau_max + 1):
    diff = x0 - x[tau:tau + W]
    d[tau] = np.dot(diff, diff)
  dp = np.ones(tau_max + 1); cum = 0.0
  for tau in range(1, tau_max + 1):
    cum += d[tau]
    dp[tau] = d[tau] * tau / cum if cum > 0 else 1.0
  for tau in range(tau_min, tau_max):
    if dp[tau] < thresh:
      while tau + 1 <= tau_max and dp[tau + 1] < dp[tau]: tau += 1
      return sr / tau
  tau = tau_min + int(np.argmin(dp[tau_min:tau_max]))
  return sr / tau

def harmonic_levels(x, sr, f0):
  """dB of the 2nd harmonic relative to the fundamental (+ = 2H stronger)."""
  if f0 <= 0: return 0.0, 0.0
  w = x * np.hanning(len(x))
  nfft = 1 << int(np.ceil(np.log2(len(w) * 4)))
  mag = np.abs(np.fft.rfft(w, nfft)); freqs = np.fft.rfftfreq(nfft, 1 / sr)
  def level(f):
    lo, hi = np.searchsorted(freqs, [f * 0.85, f * 1.15])
    return mag[lo:hi].max() if hi > lo else 1e-9
  f1 = level(f0); f2 = level(2 * f0)
  return 20 * np.log10(f1 + 1e-12), 20 * np.log10(f2 + 1e-12)

def run(fn):
  here = os.path.dirname(__file__)
  sr, audio = load_mono(os.path.join(here, '..', '..', '..', 'test_audio', fn))
  N = len(audio)
  ps = pitch_shifter(); ps.init(sr)
  ps.process_chunk(audio.astype(np.float32))
  trig = ps.get_buffer('atk.trigger', N)
  P = ps.get_buffer('yd.P', N)
  conf = 1.0 - np.asarray(ps.get_buffer('yd.aperiodicity', N))   # confident = conf >= 0.6

  onsets = np.where(trig > 0.5)[0]; notes = []
  for o in onsets:
    if notes and o - notes[-1] < int(0.04 * sr): continue
    notes.append(int(o))

  print(f"{fn}: {N/sr:.1f}s, {len(notes)} notes  (block yd.P vs full-rate YIN truth)\n")
  print(f"  {'#':>2} {'onset':>6} {'true':>6} {'yd.P':>6} {'ratio':>5} "
        f"{'conf%':>5} {'2H-fund(dB)':>11}  flag")
  for i, o in enumerate(notes):
    a, b = o + int(0.06 * sr), min(o + int(0.22 * sr), N)
    if a >= N: continue
    seg = audio[a:b]
    true = yin_f0(seg, sr)
    Pn = P[a:b]; cn = conf[a:b] >= 0.6
    Pq = Pn[cn & (Pn > 1.0)]
    det = sr / np.median(Pq) if len(Pq) else 0.0
    ratio = det / true if true > 0 else 0.0
    f1, f2 = harmonic_levels(seg, sr, true)
    flag = ""
    if true > 0 and abs(ratio - 1.0) > 0.2: flag = "<-- WRONG"
    if f2 - f1 > 3: flag += " (2H-dominant)"
    print(f"  {i:>2} {o/sr:>6.3f} {true:>6.1f} {det:>6.1f} {ratio:>5.2f} "
          f"{100*cn.mean():>5.0f} {f2-f1:>+11.1f}  {flag}")

if __name__ == '__main__':
  run("Fourth Test.wav")
