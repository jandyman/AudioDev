"""
keybass_1 — raised-cosine pulse generator.

A duty-cycle pulse oscillator whose high<->low edges are raised-cosine S-curves
(not instantaneous steps, not linear ramps) of a fixed width N samples. Keeping N
short relative to the period leaves genuine flat plateaus, so the wave stays a
pulse rather than collapsing into a triangle/ramp. N is the harmonic-softness
knob: N->0 approaches a hard rectangle (rich, aliasing-prone); larger N rolls off
the upper harmonics.

Pure-numpy prototyping stage (per the architecture, DSP settles in C++/Faust
later). `freq` may be a scalar or a per-sample array, so glides drive it directly.
"""
import numpy as np

def pulse(freq, n, sr=48000, duty=0.5, transition=5, low=-1.0, high=1.0):
  """Generate a raised-cosine-edged duty-cycle pulse.

  freq       scalar Hz, or a per-sample array of length n (for glide/vibrato)
  n          number of output samples
  sr         sample rate, Hz
  duty       high fraction of the period, 0..1
  transition raised-cosine edge width N, in samples (the harmonic-softness knob)
  low        output value of the low plateau
  high       output value of the high plateau

  returns    float64 array of length n
  """
  freq = np.asarray(freq, dtype=float)
  if freq.ndim == 0:
    freq = np.full(n, float(freq))
  elif len(freq) != n:
    raise ValueError(f"freq array length {len(freq)} != n {n}")

  # Phase accumulator in [0,1) per period; starts at 0 (subtract the first inc).
  inc = freq / sr
  phase = (np.cumsum(inc) - inc) % 1.0

  # Edge width in phase units: N samples / period-in-samples = N * freq / sr.
  w = transition * inc
  if np.any(w >= duty) or np.any(duty + w >= 1.0):
    # Transitions eat the plateaus -> degrades toward a ramp/triangle.
    print("pulse: transition too wide for this freq/duty — plateaus collapse")

  # Piecewise within the period, normalized to [0,1] then scaled to [low,high]:
  #   [0, w)        rising raised cosine   0 -> 1
  #   [w, duty)     high plateau                1
  #   [duty, duty+w) falling raised cosine 1 -> 0
  #   [duty+w, 1)   low plateau                 0
  shape = np.zeros(n)
  rise = phase < w
  shape[rise] = 0.5 * (1.0 - np.cos(np.pi * phase[rise] / w[rise]))
  shape[(phase >= w) & (phase < duty)] = 1.0
  fall = (phase >= duty) & (phase < duty + w)
  shape[fall] = 0.5 * (1.0 + np.cos(np.pi * (phase[fall] - duty) / w[fall]))
  # remaining region stays 0 (low plateau)

  return low + (high - low) * shape
