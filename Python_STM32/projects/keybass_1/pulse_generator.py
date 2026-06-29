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

def pulse_shape(phase, duty, w):
  """Raised-cosine pulse shape in [0,1] from a phase in [0,1).

  phase  per-sample phase, 0..1 over one period
  duty   high fraction of the period
  w      raised-cosine edge width in phase units (scalar or per-sample array)

  Shared by the free-running pulse() and the event-synced builder, so the edge
  geometry is defined in exactly one place.
  """
  phase = np.asarray(phase, dtype=float)
  w = np.broadcast_to(np.asarray(w, dtype=float), phase.shape)
  shape = np.zeros_like(phase)
  rise = phase < w
  shape[rise] = 0.5 * (1.0 - np.cos(np.pi * phase[rise] / w[rise]))
  shape[(phase >= w) & (phase < duty)] = 1.0
  fall = (phase >= duty) & (phase < duty + w)
  shape[fall] = 0.5 * (1.0 + np.cos(np.pi * (phase[fall] - duty) / w[fall]))
  return shape

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

  return low + (high - low) * pulse_shape(phase, duty, w)
