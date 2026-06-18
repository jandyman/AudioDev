"""
Diagnostic: why does the pitch detector fail on the first C3 (after a lingering
C2) in "Longer Bass Notes"? Confirms three predictions around the C3 attack:

  1. selected_filter sticks to the lowest-cutoff filter (0).
  2. The selected period P reads ~2x too long (~65 Hz instead of ~131 Hz).
  3. A higher filter's raw tall-peak spacing DOES show ~131 Hz — i.e. the period
     is recoverable; the lowest-cutoff selection + peak gate throw it away.

Prints numbers only (no plots) so it can run headless.
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
  # Highest autocorrelation peak in the bass range; used only in STABLE regions
  # (where the contaminating note has decayed) to label a note's pitch.
  x = x - x.mean()
  if np.sqrt((x * x).mean()) < 1e-4: return 0.0
  corr = np.correlate(x, x, 'full')[len(x) - 1:]
  lo, hi = int(sr / fmax), int(sr / fmin)
  seg = corr[lo:hi]
  if len(seg) == 0: return 0.0
  return sr / (lo + int(np.argmax(seg)))

def peak_spacings_hz(tall_peak, sr, i0, i1):
  # Inter-impulse spacing of a tall_peak probe over [i0, i1) -> implied Hz.
  idx = np.where(tall_peak[i0:i1] > 0.5)[0]
  if len(idx) < 2: return []
  return [round(sr / d, 1) for d in np.diff(idx)]

def run(filename):
  here = os.path.dirname(__file__)
  sr, audio = load_mono(os.path.join(here, '..', '..', '..', 'test_audio', filename))
  N = len(audio)
  print(f"{filename}: {sr} Hz, {N/sr:.2f} s, {N} samples\n")

  ps = pitch_shifter(); ps.init(sr)
  ps.process_chunk(audio.astype(np.float32))

  trig   = ps.get_buffer('atk.trigger', N)
  sel    = ps.get_buffer('pd.selected_filter', N)
  Pbuf   = ps.get_buffer('pd.P', N)
  qual   = ps.get_buffer('pd.qualified', N)
  mu     = [ps.get_buffer(f'pd.mu_{k}', N) for k in range(3)]
  tall   = [ps.get_buffer(f'pd.tall_peak_{k}', N) for k in range(3)]
  cln    = [ps.get_buffer(f'pd.cleanness_{k}', N) for k in range(3)]
  amp    = [ps.get_buffer(f'pd.amplitude_{k}', N) for k in range(3)]
  lat    = ps.get_buffer('lc.latency_ms', N)
  loopev = ps.get_buffer('lc.loop_event', N)
  bailev = ps.get_buffer('lc.bailout_event', N)

  # --- locate notes via attack onsets, label each by stable-window pitch ---
  onsets = np.where(trig > 0.5)[0]
  # collapse onset clusters (within 30 ms) to a single onset
  notes = []
  for o in onsets:
    if notes and o - notes[-1] < int(0.030 * sr): continue
    notes.append(int(o))
  print("Detected notes (onset time, stable-window f0):")
  labels = []
  for i, o in enumerate(notes):
    w0, w1 = o + int(0.060 * sr), o + int(0.180 * sr)
    f0 = estimate_f0(audio[w0:min(w1, N)], sr) if w0 < N else 0.0
    labels.append(f0)
    print(f"  note {i:2d}  t={o/sr:6.3f}s  f0={f0:6.1f} Hz")

  # --- first C3 (~131 Hz) preceded by a C2 (~65 Hz) ---
  target = None
  for i in range(1, len(labels)):
    if 120 <= labels[i] <= 140 and 58 <= labels[i-1] <= 72:
      target = i; break
  if target is None:
    print("\nNo C2->C3 transition found by the heuristic; dumping all notes above.")
    return
  o = notes[target]
  true_hz = labels[target]
  true_period = sr / true_hz
  print(f"\n=== First C2->C3: note {target}, onset t={o/sr:.3f}s, "
        f"true C3 ~{true_hz:.1f} Hz (period ~{true_period:.0f} samples) ===\n")

  # --- behavior across the first 60 ms of the C3 attack ---
  win = int(0.060 * sr)
  i0, i1 = o, min(o + win, N)
  print(f"Across the C3 attack [{i0/sr:.3f}s .. {i1/sr:.3f}s]:")
  print(f"  selected_filter: values seen = "
        f"{dict(zip(*np.unique(sel[i0:i1].astype(int), return_counts=True)))}")
  Pw = Pbuf[i0:i1]; Pw = Pw[Pw > 1.0]
  if len(Pw):
    P_hz = sr / Pw
    print(f"  P (selected period): mean {np.mean(P_hz):6.1f} Hz  "
          f"(median {np.median(P_hz):.1f} Hz)   [true ~{true_hz:.1f}]")
  print(f"  qualified fraction: {(qual[i0:i1] > 0.5).mean():.2f}\n")

  print("  Per-filter readout in the attack window:")
  print(f"    {'filt':>4} {'mu(Hz)':>8} {'cleanness':>10} {'amplitude':>10}  raw tall-peak spacings (Hz)")
  for k in range(3):
    muw = mu[k][i0:i1]; muw = muw[muw > 1.0]
    mu_hz = sr / np.median(muw) if len(muw) else 0.0
    sp = peak_spacings_hz(tall[k], sr, i0, i1)
    sp_str = ", ".join(f"{v:.0f}" for v in sp[:8]) + (" ..." if len(sp) > 8 else "")
    print(f"    {k:>4} {mu_hz:>8.1f} {np.median(cln[k][i0:i1]):>10.2f} "
          f"{np.median(amp[k][i0:i1]):>10.2f}  {sp_str}")

  print("\n  Prediction check:")
  sel_mode = int(np.bincount(sel[i0:i1].astype(int).clip(min=0)).argmax()) \
             if (sel[i0:i1] >= 0).any() else -1
  print(f"   1) lowest-filter selected? selected_filter mode = {sel_mode}")
  if len(Pw):
    ratio = (sr / np.median(Pw)) / true_hz
    print(f"   2) P ~2x too long?       P/true ratio = {ratio:.2f}  "
          f"({'~octave-down error' if ratio < 0.6 else 'NOT 2x' if ratio>0.8 else 'partial'})")
  for k in range(3):
    sp = peak_spacings_hz(tall[k], sr, i0, i1)
    near = [v for v in sp if abs(v - true_hz) < 0.15 * true_hz]
    print(f"   3) filter {k} recovers ~{true_hz:.0f} Hz in raw peaks? "
          f"{len(near)}/{len(sp)} spacings near true")

  # --- full-note pitch + loop-controller behavior, C3 vs neighboring C2 ---
  def note_span(i):
    a = notes[i]
    b = notes[i + 1] if i + 1 < len(notes) else N
    return a, min(b, N)

  print("\n  Full-note pitch stability + loop-controller behavior:")
  print(f"    {'note':>4} {'f0':>6} {'P_med':>6} {'P_std':>6} {'qual':>5} "
        f"{'loops':>5} {'bail':>4} {'lat_min':>7} {'lat_max':>7} {'lat_swing':>9}")
  for i in [target - 2, target - 1, target, target + 1]:
    if i < 0 or i >= len(notes): continue
    a, b = note_span(i)
    Pn = Pbuf[a:b]; q = qual[a:b] > 0.5
    Pn_q = Pn[q & (Pn > 1.0)]
    p_med = sr / np.median(Pn_q) if len(Pn_q) else 0.0
    p_std = np.std(sr / Pn_q) if len(Pn_q) else 0.0
    lp = int((loopev[a:b] > 0.5).sum()); bl = int((bailev[a:b] > 0.5).sum())
    lw = lat[a:b]
    print(f"    {i:>4} {labels[i]:>6.1f} {p_med:>6.1f} {p_std:>6.1f} "
          f"{q.mean():>5.2f} {lp:>5d} {bl:>4d} "
          f"{lw.min():>7.1f} {lw.max():>7.1f} {lw.max()-lw.min():>9.1f}")

  # --- loop-point placement: latency trajectory + per-loop backward jump ---
  print("\n  Loop-point detail (C3 note 6 vs C2 note 7):")
  for i in [target, target + 1]:
    a, b = note_span(i)
    ev = a + np.where(loopev[a:b] > 0.5)[0]
    lat_at = lat[ev]                          # latency just after each loop fires
    lat_before = lat[np.maximum(ev - 1, 0)]
    jumps = lat_before - lat_at              # ms the loop stepped delay backward
    period_ms = 1000.0 / labels[i]
    print(f"    note {i} ({labels[i]:.0f} Hz, period {period_ms:.1f} ms): "
          f"{len(ev)} loops")
    print(f"      backward jump per loop (ms): "
          f"{', '.join(f'{j:.0f}' for j in jumps[:14])}{' ...' if len(jumps)>14 else ''}")
    if len(jumps):
      print(f"      jump / period ratio: "
            f"{', '.join(f'{j/period_ms:.1f}' for j in jumps[:14])}{' ...' if len(jumps)>14 else ''}")

if __name__ == '__main__':
  filename = "Longer Bass Notes.wav"
  run(filename)
