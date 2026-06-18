"""
Timeline of the pitch detector's internals across the FIRST C3 note, to see
whether the period estimate degrades as the 2nd harmonic grows through the note
(low-pass bank can't reject a harmonic below its cutoff). Sampled every ~25 ms:
selected_filter, P, qualified, each band's mu (Hz) and amplitude.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build'))
import numpy as np
import scipy.io.wavfile as wav
from build.pybind_pitch_shifter import pitch_shifter

def load_mono(path):
  sr, data = wav.read(path)
  x = data.astype(np.float64) / (32768.0 if data.dtype == np.int16 else
                                 2147483648.0 if data.dtype == np.int32 else 1.0)
  return sr, (x[:, 0] if x.ndim > 1 else x)

def estimate_f0(x, sr, fmin=40.0, fmax=320.0):
  x = x - x.mean()
  if np.sqrt((x * x).mean()) < 1e-4: return 0.0
  corr = np.correlate(x, x, 'full')[len(x) - 1:]
  lo, hi = int(sr / fmax), int(sr / fmin)
  return sr / (lo + int(np.argmax(corr[lo:hi]))) if hi > lo else 0.0

def hz(buf):  # period-in-samples buffer -> Hz, 0 where invalid
  return np.where(buf > 1.0, 44100.0 / np.maximum(buf, 1.0), 0.0)

def run(filename):
  here = os.path.dirname(__file__)
  sr, audio = load_mono(os.path.join(here, '..', '..', '..', 'test_audio', filename))
  N = len(audio)
  ps = pitch_shifter(); ps.init(sr); ps.process_chunk(audio.astype(np.float32))

  trig = ps.get_buffer('atk.trigger', N)
  sel  = ps.get_buffer('pd.selected_filter', N)
  P    = ps.get_buffer('pd.P', N)
  qual = ps.get_buffer('pd.qualified', N)
  mu   = [ps.get_buffer(f'pd.mu_{k}', N) for k in range(3)]
  amp  = [ps.get_buffer(f'pd.amplitude_{k}', N) for k in range(3)]

  onsets = np.where(trig > 0.5)[0]
  notes = []
  for o in onsets:
    if notes and o - notes[-1] < int(0.030 * sr): continue
    notes.append(int(o))

  # first C3
  target = None
  for i, o in enumerate(notes):
    w0 = o + int(0.06 * sr)
    if w0 < N and 120 <= estimate_f0(audio[w0:o + int(0.18 * sr)], sr) <= 140:
      if i and 58 <= estimate_f0(audio[notes[i-1] + int(0.06*sr):notes[i-1]+int(0.18*sr)], sr) <= 72:
        target = i; break
  o = notes[target]; b = notes[target + 1] if target + 1 < len(notes) else N
  print(f"First C3: note {target}, onset {o/sr:.3f}s, span {(b-o)/sr*1000:.0f} ms (true ~131 Hz)\n")

  print(f"  {'t_ms':>5} {'sel':>3} {'P_Hz':>6} {'qual':>4} | "
        f"{'mu0':>5} {'mu1':>5} {'mu2':>5} | {'amp0':>5} {'amp1':>5} {'amp2':>5}")
  step = int(0.025 * sr)
  for t in range(o, min(b, N), step):
    w = slice(t, min(t + step, N))
    s = int(np.median(sel[w]))
    p = np.median(hz(P[w])[hz(P[w]) > 0]) if (P[w] > 1).any() else 0.0
    q = (qual[w] > 0.5).mean()
    mus = [np.median(hz(mu[k][w])[hz(mu[k][w]) > 0]) if (mu[k][w] > 1).any() else 0.0 for k in range(3)]
    amps = [np.median(amp[k][w]) for k in range(3)]
    print(f"  {(t-o)/sr*1000:>5.0f} {s:>3d} {p:>6.1f} {q:>4.2f} | "
          f"{mus[0]:>5.0f} {mus[1]:>5.0f} {mus[2]:>5.0f} | "
          f"{amps[0]:>5.2f} {amps[1]:>5.2f} {amps[2]:>5.2f}")

if __name__ == '__main__':
  run("Longer Bass Notes.wav")
