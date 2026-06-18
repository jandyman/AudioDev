"""
Step (a) check: is pd.selected_peak a clean one-per-period loop clock, vs the
wideband zc.zc_out it would replace? Compares interval regularity on the first
C3 (sustained part). Print-only.
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

def f0(x, sr, fmin=40, fmax=320):
  x = x - x.mean()
  if np.sqrt((x*x).mean()) < 1e-4: return 0.0
  c = np.correlate(x, x, 'full')[len(x)-1:]
  lo, hi = int(sr/fmax), int(sr/fmin)
  return sr/(lo+int(np.argmax(c[lo:hi]))) if hi > lo else 0.0

def intervals(impulse, sr, a, b):
  idx = a + np.where(impulse[a:b] > 0.5)[0]
  return np.diff(idx)/sr*1000.0 if len(idx) > 2 else np.array([])

def run(fn):
  here = os.path.dirname(__file__)
  sr, audio = load_mono(os.path.join(here, '..', '..', '..', 'test_audio', fn))
  N = len(audio)
  ps = pitch_shifter(); ps.init(sr); ps.process_chunk(audio.astype(np.float32))
  trig = ps.get_buffer('atk.trigger', N)
  zc   = ps.get_buffer('zc.zc_out', N)
  pk   = ps.get_buffer('pd.selected_peak', N)

  onsets = np.where(trig > 0.5)[0]; notes = []
  for o in onsets:
    if notes and o - notes[-1] < int(0.03*sr): continue
    notes.append(int(o))
  tgt = None
  for i, o in enumerate(notes):
    if o+int(0.06*sr) < N and 120 <= f0(audio[o+int(0.06*sr):o+int(0.18*sr)], sr) <= 140:
      tgt = i; break
  o = notes[tgt]; b = notes[tgt+1] if tgt+1 < len(notes) else N
  a2 = o + int(0.10*sr)            # sustained part
  per = 1000.0 / f0(audio[o+int(0.06*sr):o+int(0.18*sr)], sr)
  print(f"First C3: note {tgt}, {o/sr:.3f}s, period ~{per:.1f} ms\n")
  for name, sig in [("wideband zc.zc_out", zc), ("pd.selected_peak", pk)]:
    iv = intervals(sig, sr, a2, min(b, N))
    if len(iv):
      print(f"  {name:>20}: {len(iv)+1} events, mean {iv.mean():.2f} ms, "
            f"std {iv.std():.2f} ms, per/mean {per/iv.mean():.2f}")
      print(f"  {'':>20}  {', '.join(f'{v:.1f}' for v in iv[:14])}")
    else:
      print(f"  {name:>20}: <3 events")

if __name__ == '__main__':
  run("Longer Bass Notes.wav")
