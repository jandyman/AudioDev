"""
Measure the attack-tap fade-in time (gain 0.2 -> 0.8 rise) at each attack event.
Expected ~1 ms (ATTACK_FADEIN_MS). Reports per-event rise time, the rising tap,
and active_gain at the event (to see if gating is dragging it). Print-only.
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

def run(fn):
  sr, audio = load_mono(os.path.join(os.path.dirname(__file__), '..', '..', '..',
                                     'test_audio', fn))
  N = len(audio)
  ps = pitch_shifter(); ps.init(sr); ps.process_chunk(audio.astype(np.float32))
  aev  = ps.get_buffer('lc.attack_event', N)
  agn  = ps.get_buffer('atk.active_gain', N)
  g    = [ps.get_buffer(f'lc.gain{k+1}', N) for k in range(3)]

  ev = np.where(aev > 0.5)[0]
  print(f"{fn}: {len(ev)} attack events. ATTACK_FADEIN_MS should be ~1 ms.\n")
  print(f"  {'t(s)':>7} {'tap':>3} {'0.2→0.8 ms':>11} {'active_gain@evt':>15}")
  rises = []
  for e in ev:
    w = slice(e, min(e + int(0.025 * sr), N))
    best = None
    for k in range(3):
      gk = g[k][w]
      if gk[0] < 0.2 and gk.max() > 0.8:
        i2 = np.argmax(gk > 0.2); i8 = np.argmax(gk > 0.8)
        if i8 > i2:
          rise = (i8 - i2) / sr * 1000.0
          if best is None or rise < best[1]:
            best = (k, rise)
    if best:
      rises.append(best[1])
      print(f"  {e/sr:>7.3f} {best[0]:>3d} {best[1]:>11.2f} {agn[e]:>15.2f}")
  if rises:
    print(f"\n  median rise: {np.median(rises):.2f} ms   "
          f"(min {min(rises):.2f}, max {max(rises):.2f})")

if __name__ == '__main__':
  run("Longer Bass Notes.wav")
