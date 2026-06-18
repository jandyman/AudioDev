"""
Raw latency_ms trajectory over the first low note, with loop-event marks, to see
the actual sawtooth shape (the peak/trough jump metric is confounded by the
crossfade). Print-only.
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

sr, audio = load_mono(os.path.join(os.path.dirname(__file__), '..', '..', '..',
                                   'test_audio', "Longer Bass Notes.wav"))
N = len(audio)
ps = pitch_shifter(); ps.init(sr); ps.process_chunk(audio.astype(np.float32))
trig = ps.get_buffer('atk.trigger', N)
lat  = ps.get_buffer('lc.latency_ms', N)
lev  = ps.get_buffer('lc.loop_event', N)

# first low note onset (~0.69-0.75s region)
onsets = [int(o) for o in np.where(trig > 0.5)[0]]
notes = []
for o in onsets:
  if notes and o - notes[-1] < int(0.03*sr): continue
  notes.append(o)
o = next(n for n in notes if 0.70 < n/sr < 0.80)

print(f"note onset {o/sr:.3f}s — latency_ms every ~2 ms, * = loop_event in window\n")
step = int(0.002 * sr)
for t in range(o + int(0.10*sr), o + int(0.30*sr), step):
  w = slice(t, t+step)
  mark = '*' if (lev[w] > 0.5).any() else ' '
  bar = '#' * int(lat[t] / 1.5)
  print(f"  {(t-o)/sr*1000:5.0f} ms  {lat[t]:5.1f} {mark} {bar}")
