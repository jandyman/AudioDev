import sys, os
import numpy as np
import matplotlib.pyplot as plt
from scipy import signal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build'))
from pybind_eq import EqChannel, compute_hishelf, compute_lpf


def coeffs_to_scipy(b0, b1, b2, a1_stored, a2_stored):
  # a1/a2 in biquad.h are stored negated vs. standard form.
  # scipy freqz convention: H = (b[0]+b[1]z^-1+...) / (a[0]+a[1]z^-1+...)
  # with a[0]=1 and a[k] = standard positive denominator coefficients.
  return ([b0, b1, b2], [1.0, -a1_stored, -a2_stored])


def theoretical_response(shelf_gain_db, shelf_fc_hz, lp_fc_hz, sample_rate, freqs):
  shelf_b, shelf_a = coeffs_to_scipy(*compute_hishelf(shelf_gain_db, shelf_fc_hz, sample_rate))
  lp_b,    lp_a    = coeffs_to_scipy(*compute_lpf(lp_fc_hz, sample_rate))
  cascade_b = np.convolve(shelf_b, lp_b)
  cascade_a = np.convolve(shelf_a, lp_a)
  _, H = signal.freqz(cascade_b, cascade_a, worN=freqs, fs=sample_rate)
  return 20 * np.log10(np.abs(H) + 1e-12)


def measured_response(shelf_gain_db, shelf_fc_hz, lp_fc_hz, sample_rate, freqs):
  db = []
  for f in freqs:
    n_samples = max(int(30 * sample_rate / f), 1024)
    t = np.arange(n_samples, dtype=np.float32) / sample_rate
    x = np.sin(2 * np.pi * float(f) * t).astype(np.float32)

    eq = EqChannel()
    eq.init(shelf_gain_db, shelf_fc_hz, lp_fc_hz, sample_rate)
    y = eq.process_block(x)

    # discard first half to let the transient settle
    half = n_samples // 2
    rms_in  = np.sqrt(np.mean(x[half:] ** 2))
    rms_out = np.sqrt(np.mean(y[half:] ** 2))
    db.append(20 * np.log10(rms_out / rms_in + 1e-12))
  return np.array(db)


def run(shelf_gain_db, shelf_fc_hz, lp_fc_hz, sample_rate):
  freqs = np.logspace(np.log10(20), np.log10(sample_rate / 2 * 0.95), 300)

  theory_db  = theoretical_response(shelf_gain_db, shelf_fc_hz, lp_fc_hz, sample_rate, freqs)
  meas_db    = measured_response(shelf_gain_db, shelf_fc_hz, lp_fc_hz, sample_rate, freqs)
  error_db   = meas_db - theory_db

  fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
  fig.suptitle(
    f'EQ Frequency Response  —  shelf {shelf_gain_db:+.1f} dB @ {shelf_fc_hz:.0f} Hz, '
    f'LP @ {lp_fc_hz:.0f} Hz,  fs = {sample_rate:.0f} Hz'
  )

  ax1.semilogx(freqs, theory_db, 'b-',  linewidth=2,   label='Theoretical (scipy freqz)')
  ax1.semilogx(freqs, meas_db,   'r--', linewidth=1.5, label='Measured (pybind11 sine sweep)')
  ax1.set_ylabel('Gain (dB)')
  ax1.legend()
  ax1.grid(True, which='both', alpha=0.3)

  ax2.semilogx(freqs, error_db, 'k-', linewidth=1)
  ax2.axhline(0, color='gray', linewidth=0.8, linestyle='--')
  ax2.set_xlabel('Frequency (Hz)')
  ax2.set_ylabel('Error (dB)')
  ax2.set_title('Measured − Theoretical')
  ax2.grid(True, which='both', alpha=0.3)

  plt.tight_layout()
  plt.show()


# ── params ──────────────────────────────────────────────
shelf_gain_db = 6.0      # hi-shelf gain
shelf_fc_hz   = 2000.0   # hi-shelf corner
lp_fc_hz      = 12000.0  # low-pass corner
sample_rate   = 48000.0

run(shelf_gain_db, shelf_fc_hz, lp_fc_hz, sample_rate)
