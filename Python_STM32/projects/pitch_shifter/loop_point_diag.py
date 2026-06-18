"""
Loop-point decision diagnostic. Reconstructs, per loop event, the backward jump
the loop controller chose (= latency sawtooth peak -> trough) and whether it was
a gated (integer-multiple-of-P) match or the nearest-ZC fallback. Answers:
  - is the "reset at ~100ms" a bailout or a loop?
  - does the first loop step back ~1 period, or dump latency toward MIN?
  - gated vs fallback, low note vs C3.
Prints numbers only.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build'))
import numpy as np
import scipy.io.wavfile as wav
from build.pybind_pitch_shifter import pitch_shifter

def load_mono(path):
  sr, data = wav.read(path)
  if data.dtype == np.int16:    x = data.astype(np.float64) / 32768.0
  elif data.dtype == np.int32:  x = data.astype(np.float64) / 2147483648.0
  else:                         x = data.astype(np.float64)
  if x.ndim > 1: x = x[:, 0]
  return sr, x

def estimate_f0(x, sr, fmin=40.0, fmax=320.0):
  x = x - x.mean()
  if np.sqrt((x * x).mean()) < 1e-4: return 0.0
  corr = np.correlate(x, x, 'full')[len(x) - 1:]
  lo, hi = int(sr / fmax), int(sr / fmin)
  seg = corr[lo:hi]
  if len(seg) == 0: return 0.0
  return sr / (lo + int(np.argmax(seg)))

def analyze_note(idx, f0, a, b, sr, lat, loopev, gatedev, bailev):
  period_ms = 1000.0 / f0 if f0 > 0 else 0.0
  ev   = a + np.where(loopev[a:b]  > 0.5)[0]
  gat  = set(a + np.where(gatedev[a:b] > 0.5)[0])
  nbail = int((bailev[a:b] > 0.5).sum())
  print(f"\n  note {idx}  f0={f0:.1f} Hz  period={period_ms:.1f} ms  "
        f"span={ (b-a)/sr*1000:.0f} ms  loops={len(ev)}  bailouts={nbail}")
  if len(ev) == 0: return
  print(f"    first loop at {(ev[0]-a)/sr*1000:.0f} ms into note "
        f"(latency then = {lat[ev[0]-1]:.0f} ms)")
  guard = int(0.004 * sr)
  print(f"    {'#':>2} {'fire_lat':>8} {'target':>7} {'jump':>6} {'jmp/per':>7} {'kind':>9}")
  for j, e in enumerate(ev[:16]):
    nxt  = ev[j + 1] if j + 1 < len(ev) else b
    peak = lat[max(a, e - guard):e + 1].max()
    trough = lat[e:nxt].min()
    jump = peak - trough
    # nearest event sample with a gated flag (crossfade can offset by a sample)
    kind = "gated" if any(abs(g - e) <= 2 for g in gat) else "fallback"
    print(f"    {j:>2} {peak:>8.0f} {trough:>7.0f} {jump:>6.0f} "
          f"{(jump/period_ms if period_ms else 0):>7.1f} {kind:>9}")

def run(filename):
  here = os.path.dirname(__file__)
  sr, audio = load_mono(os.path.join(here, '..', '..', '..', 'test_audio', filename))
  N = len(audio)
  ps = pitch_shifter(); ps.init(sr)
  ps.process_chunk(audio.astype(np.float32))

  trig   = ps.get_buffer('atk.trigger', N)
  lat    = ps.get_buffer('lc.latency_ms', N)
  loopev = ps.get_buffer('lc.loop_event', N)
  gatedev= ps.get_buffer('lc.gated_event', N)
  bailev = ps.get_buffer('lc.bailout_event', N)
  zc     = ps.get_buffer('zc.zc_out', N)

  print(f"{filename}: {sr} Hz, {N/sr:.2f} s")
  print(f"GLOBAL: loop_events={int((loopev>0.5).sum())}  "
        f"gated_events={int((gatedev>0.5).sum())}  "
        f"bailout_events={int((bailev>0.5).sum())}")

  onsets = np.where(trig > 0.5)[0]
  notes = []
  for o in onsets:
    if notes and o - notes[-1] < int(0.030 * sr): continue
    notes.append(int(o))

  # analyze the first clear low note (~65 Hz) and the first C3 (~131 Hz)
  for i, o in enumerate(notes):
    w0, w1 = o + int(0.060 * sr), o + int(0.180 * sr)
    f0 = estimate_f0(audio[w0:min(w1, N)], sr) if w0 < N else 0.0
    b = notes[i + 1] if i + 1 < len(notes) else N
    if 58 <= f0 <= 72 or 120 <= f0 <= 140:
      analyze_note(i, f0, o, min(b, N), sr, lat, loopev, gatedev, bailev)
      # ZC-stream regularity over the sustained part of the note
      a2 = o + int(0.25 * sr)
      zt = a2 + np.where(zc[a2:min(b, N)] > 0.5)[0]
      if len(zt) > 3:
        iv = np.diff(zt) / sr * 1000.0
        per = 1000.0 / f0
        print(f"    ZC stream: {len(zt)} crossings, interval "
              f"mean={iv.mean():.1f} ms std={iv.std():.1f} ms "
              f"(period={per:.1f} ms, ZC/period={per/iv.mean():.2f})")
        print(f"      intervals(ms): {', '.join(f'{v:.1f}' for v in iv[:14])}"
              f"{' ...' if len(iv) > 14 else ''}")

if __name__ == '__main__':
  run("Longer Bass Notes.wav")
