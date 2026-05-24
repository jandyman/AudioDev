"""
Harmonic-rejection experiment — multi-filter bank for fundamental-period
extraction on bass/guitar signals.

A bank of N LPFs (default: 60 / 120 / 240 Hz, all 2nd-order = 12 dB/oct)
runs in parallel. Each filter has two probe outputs computed in a sliding
window:

  cleanness  =  tall_peak_ratio * spacing_regularity
                where tall_peak_ratio = (peaks above frac*env) / (peaks above small_frac*env)
                and   spacing_regularity = 1 / (1 + std(intervals)/mean(intervals))

  amplitude  =  mean(filtered_envelope) / mean(raw_envelope)
                (guards against locking onto sympathetic vibration during decay,
                 when the filter output is much smaller than the raw signal)

A selector picks the lowest-cutoff filter whose cleanness AND amplitude both
exceed thresholds. This generalizes the dual-LPF spec idea: lower cutoff is
preferred when it works because it rejects H2 most strongly, but we step up
when the fundamental is above the cutoff and the filter no longer dominates.

Pure Python, offline, full-buffer — no chunking, no pybind. Parameters live
at the bottom of the file for PyCharm.
"""
import os
import numpy as np
import scipy.io.wavfile as wav
from scipy.signal import butter, filtfilt, hilbert, find_peaks
import matplotlib
matplotlib.use('macosx')
import matplotlib.pyplot as plt


def load_wav_mono(path):
  sr, data = wav.read(path)
  if data.dtype == np.int16:
    x = data.astype(np.float64) / 32768.0
  elif data.dtype == np.int32:
    x = data.astype(np.float64) / 2147483648.0
  else:
    x = data.astype(np.float64)
  if x.ndim > 1:
    x = x[:, 0]
  return sr, x


def detect_zc(x):
  """Positive-going zero crossings; returns sample indices."""
  s = np.sign(x)
  s[s == 0] = 1
  return np.where(np.diff(s) > 0)[0] + 1


def lpf(x, sr, fc, order=2):
  b, a = butter(order, fc / (sr / 2), btype='low')
  return filtfilt(b, a, x)


def smooth_envelope(x, sr, smooth_hz=30.0):
  """Hilbert magnitude, low-passed to remove ripple."""
  env = np.abs(hilbert(x))
  return lpf(env, sr, smooth_hz, order=2)


def tall_peaks(x, env, frac=0.65, min_distance_samples=20):
  """Positive peaks at least frac * envelope at the same sample."""
  peaks, _ = find_peaks(x, distance=min_distance_samples)
  keep = x[peaks] >= frac * env[peaks]
  return peaks[keep]


def peaks_two_thresholds(x, env, frac_tall, frac_small=0.2, min_distance_samples=20):
  """Returns (tall, small): peak indices above each fraction of envelope.
  small ⊇ tall by construction (frac_small < frac_tall)."""
  peaks, _ = find_peaks(x, distance=min_distance_samples)
  vals, envs = x[peaks], env[peaks]
  return peaks[vals >= frac_tall * envs], peaks[vals >= frac_small * envs]


def windowed_scores(tall, small, env_filt, env_raw, sr, window_ms, hop_ms):
  """Per-window cleanness + amplitude scores for one filter.

  cleanness = (tall/small ratio) * (peak-spacing regularity)
  amplitude = mean(env_filt) / mean(env_raw)

  Both are in [0, ~1]. Cleanness needs ≥3 tall peaks in the window to compute
  regularity; otherwise it's 0 (silence/sparse).
  """
  N = len(env_filt)
  W = int(window_ms * sr / 1000)
  H = int(hop_ms    * sr / 1000)
  centers = np.arange(W // 2, N - W // 2, H)
  cleanness = np.zeros(len(centers))
  amplitude = np.zeros(len(centers))
  for i, c in enumerate(centers):
    a, b = c - W // 2, c + W // 2
    tall_in  = tall [(tall  >= a) & (tall  < b)]
    small_in = small[(small >= a) & (small < b)]
    tall_ratio = len(tall_in) / max(len(small_in), 1)
    if len(tall_in) >= 3:
      d = np.diff(tall_in)
      cv = d.std() / max(d.mean(), 1.0)
      regularity = 1.0 / (1.0 + cv)
    else:
      regularity = 0.0
    cleanness[i] = tall_ratio * regularity
    amplitude[i] = env_filt[a:b].mean() / max(env_raw[a:b].mean(), 1e-6)
  return centers, cleanness, amplitude


def select_filter(cleanness, amplitude, cleanness_thresh, amp_thresh):
  """At each window, pick the lowest filter index passing both thresholds.
  Returns int array, -1 where no filter qualifies. Shape: (n_windows,).
  cleanness/amplitude shape: (n_filters, n_windows)."""
  n_filt, n_win = cleanness.shape
  sel = np.full(n_win, -1, dtype=int)
  for wi in range(n_win):
    for fi in range(n_filt):
      if cleanness[fi, wi] >= cleanness_thresh and amplitude[fi, wi] >= amp_thresh:
        sel[wi] = fi
        break
  return sel


def period_from_events(idx, sr):
  """Period (ms) at each event, computed from spacing to the previous event."""
  if len(idx) < 2:
    return np.array([], dtype=int), np.array([])
  per_ms = np.diff(idx) / sr * 1000.0
  return idx[1:], per_ms


def run_experiment(filter_fcs=(60.0, 120.0, 240.0), peak_frac=0.65,
                   small_frac=0.20, envelope_smooth_hz=30.0,
                   window_ms=100.0, hop_ms=25.0,
                   cleanness_thresh=0.50, amp_thresh=0.15,
                   period_ylim_ms=50.0):
  input_path = os.path.join(os.path.dirname(__file__), '..', '..',
                            'test_audio', 'Longer Bass Notes.wav')
  sr, x = load_wav_mono(input_path)
  N = len(x)
  t = np.arange(N) / sr
  env_raw = smooth_envelope(x, sr, envelope_smooth_hz)

  # --- Per-filter analysis ---
  n_filt = len(filter_fcs)
  filter_colors = ['green', 'C1', 'purple', 'brown', 'teal'][:n_filt]
  env_floor = 1e-3

  x_lpfs   = [lpf(x, sr, fc, order=2) for fc in filter_fcs]
  env_lpfs = [smooth_envelope(xl, sr, envelope_smooth_hz) for xl in x_lpfs]
  x_lpfs_n = [xl / np.maximum(el, env_floor) for xl, el in zip(x_lpfs, env_lpfs)]
  peaks_pairs    = [peaks_two_thresholds(xl, el, peak_frac, small_frac)
                    for xl, el in zip(x_lpfs, env_lpfs)]
  tall_peaks_per = [p[0] for p in peaks_pairs]
  small_peaks_per = [p[1] for p in peaks_pairs]

  # --- Per-window probe signals ---
  centers = None
  cleanness = np.zeros((n_filt, 0))
  amplitude = np.zeros((n_filt, 0))
  for fi in range(n_filt):
    c, cl, am = windowed_scores(tall_peaks_per[fi], small_peaks_per[fi],
                                env_lpfs[fi], env_raw, sr, window_ms, hop_ms)
    if centers is None:
      centers   = c
      cleanness = np.zeros((n_filt, len(c)))
      amplitude = np.zeros((n_filt, len(c)))
    cleanness[fi] = cl
    amplitude[fi] = am
  t_win = centers / sr

  # --- Selector: lowest filter with both scores above thresholds ---
  selected = select_filter(cleanness, amplitude, cleanness_thresh, amp_thresh)

  # Per-sample selection (step-held between window hops) so we can pick out
  # the "merged" peak stream — peaks from whichever filter is currently chosen.
  H = int(hop_ms * sr / 1000)
  selected_per_sample = np.full(N, -1, dtype=int)
  for wi in range(len(centers)):
    a = max(0, centers[wi] - H // 2)
    b = min(N, centers[wi] + H // 2)
    selected_per_sample[a:b] = selected[wi]
  merged_peaks = []
  for fi in range(n_filt):
    keep = selected_per_sample[tall_peaks_per[fi]] == fi
    merged_peaks.append(tall_peaks_per[fi][keep])
  merged_peaks = np.sort(np.concatenate(merged_peaks)) if merged_peaks else np.array([], dtype=int)

  print(f"Loaded {os.path.basename(input_path)}  ({N/sr:.2f} s, {sr} Hz)")
  for fi, fc in enumerate(filter_fcs):
    print(f"  LPF {fc:6.1f} Hz  tall={len(tall_peaks_per[fi]):4d}  small={len(small_peaks_per[fi]):4d}  "
          f"mean cleanness={cleanness[fi].mean():.2f}  mean amp={amplitude[fi].mean():.2f}")
  picked_counts = [int((selected == fi).sum()) for fi in range(n_filt)]
  none_count = int((selected < 0).sum())
  print(f"  Selector window counts: " +
        "  ".join(f"{fc:.0f}Hz={picked_counts[fi]}" for fi, fc in enumerate(filter_fcs)) +
        f"  none={none_count}")
  print(f"  Merged peaks (from selected filter): {len(merged_peaks)}")

  # ---- Figure 1: waveform stack ----
  fig, axes = plt.subplots(n_filt + 1, 1, figsize=(16, 2.0 * (n_filt + 1) + 2),
                           sharex=True)
  fig.suptitle("Harmonic-rejection — filter bank with cleanness selector", fontsize=13)

  axes[0].plot(t, x,        'b-', lw=0.3, alpha=0.7, label='raw')
  axes[0].plot(t,  env_raw, 'k-', lw=0.6, alpha=0.7, label='envelope')
  axes[0].plot(t, -env_raw, 'k-', lw=0.6, alpha=0.7)
  axes[0].plot(t[merged_peaks], np.zeros(len(merged_peaks)), 'mv',
               ms=5, alpha=0.7, label='merged peaks (selector output)')
  axes[0].set_title('Raw signal + envelope; merged peak stream from selected filter (magenta)')
  axes[0].legend(loc='upper right', fontsize=8)
  axes[0].grid(True, alpha=0.3)
  axes[0].set_xlim(0, t[-1])

  # One panel per filter: normalized signal + tall peaks; background tinted
  # whenever the selector picks that filter for that window.
  for fi in range(n_filt):
    ax = axes[fi + 1]
    color = filter_colors[fi]
    ax.plot(t, x_lpfs_n[fi], color=color, lw=0.6, alpha=0.85,
            label=f'LPF {filter_fcs[fi]:.0f} Hz (env-norm)')
    ax.axhline( peak_frac, color='k', lw=0.6, alpha=0.4, linestyle='--',
               label=f'frac threshold = {peak_frac:.2f}')
    tall = tall_peaks_per[fi]
    ax.plot(t[tall], x_lpfs_n[fi][tall], 'o', color='m', ms=3, alpha=0.7,
            label='tall peaks')
    # Tint background where this filter is selected
    for wi in range(len(t_win) - 1):
      if selected[wi] == fi:
        ax.axvspan(t_win[wi], t_win[wi + 1], color='yellow', alpha=0.15, lw=0)
    ax.set_ylim(-1.5, 1.5)
    ax.set_title(f'LPF {filter_fcs[fi]:.0f} Hz — yellow band = selector chose this filter')
    ax.legend(loc='upper right', fontsize=8)
    ax.grid(True, alpha=0.3)
  axes[-1].set_xlabel('Time (s)')

  _install_x_zoom(fig, 0.0, t[-1])
  plt.tight_layout(rect=[0, 0, 1, 0.97])

  # ---- Figure 2: probe signals (cleanness, amplitude, selection) ----
  fig2, axp = plt.subplots(3, 1, figsize=(16, 8), sharex=True)
  fig2.suptitle("Probe signals — per-filter cleanness & amplitude + selector decision",
                fontsize=13)

  for fi in range(n_filt):
    axp[0].plot(t_win, cleanness[fi], color=filter_colors[fi], lw=1.0, alpha=0.85,
                label=f'{filter_fcs[fi]:.0f} Hz')
  axp[0].axhline(cleanness_thresh, color='k', lw=0.8, alpha=0.5, linestyle='--',
                 label=f'threshold = {cleanness_thresh:.2f}')
  axp[0].set_title('Cleanness  =  tall/small peak ratio  ×  spacing regularity')
  axp[0].set_ylabel('cleanness')
  axp[0].set_ylim(0, 1.1)
  axp[0].legend(loc='upper right', fontsize=8)
  axp[0].grid(True, alpha=0.3)

  for fi in range(n_filt):
    axp[1].plot(t_win, amplitude[fi], color=filter_colors[fi], lw=1.0, alpha=0.85,
                label=f'{filter_fcs[fi]:.0f} Hz')
  axp[1].axhline(amp_thresh, color='k', lw=0.8, alpha=0.5, linestyle='--',
                 label=f'threshold = {amp_thresh:.2f}')
  axp[1].set_title('Amplitude  =  mean(filtered envelope) / mean(raw envelope)')
  axp[1].set_ylabel('amplitude ratio')
  axp[1].set_ylim(0, 1.1)
  axp[1].legend(loc='upper right', fontsize=8)
  axp[1].grid(True, alpha=0.3)

  # Step trace of selected filter index; color-code segments by filter.
  for wi in range(len(t_win) - 1):
    if selected[wi] >= 0:
      axp[2].plot([t_win[wi], t_win[wi + 1]],
                  [selected[wi], selected[wi]],
                  color=filter_colors[selected[wi]], lw=3, solid_capstyle='butt')
  axp[2].set_yticks(range(n_filt))
  axp[2].set_yticklabels([f'{fc:.0f} Hz' for fc in filter_fcs])
  axp[2].set_ylim(-0.5, n_filt - 0.5)
  axp[2].set_title(f'Selector — lowest filter with cleanness≥{cleanness_thresh:.2f} AND amp≥{amp_thresh:.2f}  (gaps = no filter qualified)')
  axp[2].set_xlabel('Time (s)')
  axp[2].grid(True, alpha=0.3)
  axp[2].set_xlim(0, t[-1])

  _install_x_zoom(fig2, 0.0, t[-1])
  plt.tight_layout(rect=[0, 0, 1, 0.97])

  # ---- Figure 3: period plot (per-filter peak-derived + merged) ----
  fig3, ax3 = plt.subplots(1, 1, figsize=(16, 4))
  for fi in range(n_filt):
    t_p, per_p = period_from_events(tall_peaks_per[fi], sr)
    if len(per_p):
      ax3.plot(t[t_p], per_p, '.', color=filter_colors[fi], ms=2, alpha=0.5,
               label=f'{filter_fcs[fi]:.0f} Hz peaks')
  t_m, per_m = period_from_events(merged_peaks, sr)
  if len(per_m):
    ax3.plot(t[t_m], per_m, 'o', color='m', ms=3, alpha=0.8, label='selector output')
  ax3.set_title('Period (ms) from successive tall-peak spacing — per filter + selector output')
  ax3.set_xlabel('Time (s)')
  ax3.set_ylabel('Period (ms)')
  ax3.set_ylim(0, period_ylim_ms)
  ax3.set_xlim(0, t[-1])
  ax3.grid(True, alpha=0.3)
  ax3.legend(loc='upper right', fontsize=8)
  _install_x_zoom(fig3, 0.0, t[-1])

  plt.show()


def _install_x_zoom(fig, x_min, x_max, base_scale=1.3):
  def on_scroll(event):
    ax = event.inaxes
    if ax is None or event.xdata is None:
      return
    factor = (1.0 / base_scale) if event.step > 0 else base_scale
    xc = event.xdata
    x0, x1 = ax.get_xlim()
    new_left  = max(xc - (xc - x0) * factor, x_min)
    new_right = min(xc + (x1 - xc) * factor, x_max)
    if new_right - new_left < 1e-6:
      return
    ax.set_xlim(new_left, new_right)
    fig.canvas.draw_idle()
  fig.canvas.mpl_connect('scroll_event', on_scroll)


if __name__ == "__main__":
  # ---- Experiment parameters ----  (all LPFs are 2nd-order Butterworth = 12 dB/oct)
  filter_fcs         = (60.0, 120.0, 240.0)  # bank cutoffs, low → high (Hz)
  peak_frac          = 0.65    # peak must reach this fraction of env to count as "tall"
  small_frac         = 0.20    # peak must reach this fraction to count as "small" (denom)
  envelope_smooth_hz = 30.0    # Hilbert envelope smoothing cutoff
  window_ms          = 100.0   # sliding window length for cleanness/amp scoring
  hop_ms             = 25.0    # window hop interval
  cleanness_thresh   = 0.50    # selector: min cleanness to qualify a filter
  amp_thresh         = 0.15    # selector: min amplitude ratio to qualify a filter
  period_ylim_ms     = 50.0    # period-plot y-axis upper limit (ms)
  # --------------------------------
  run_experiment(filter_fcs=filter_fcs,
                 peak_frac=peak_frac, small_frac=small_frac,
                 envelope_smooth_hz=envelope_smooth_hz,
                 window_ms=window_ms, hop_ms=hop_ms,
                 cleanness_thresh=cleanness_thresh, amp_thresh=amp_thresh,
                 period_ylim_ms=period_ylim_ms)
