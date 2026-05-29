"""
Attack Detector Diagnostic — probe fast/med/slow envelopes and trigger decisions.

Native pybind only (no STM32 build for attack detector yet — the algorithm work
happens here first, then ports to firmware once tuning settles).

Panels (all sharex'd — scroll wheel zooms all, toolbar Home resets):
  1. Input waveform with trigger markers (red dot = normal, orange triangle = retrigger)
  2. fast/med/slow envelopes with retrigger threshold, note_ended shaded
  3. fast/med ratio with retrigger threshold line
  4. Normal-trigger decision ratio: fast_deriv / threshold  (fires when > 1)

Run from PyCharm.
"""
import os
import sys

# Must precede matplotlib.pyplot — diagnostic_plot sets MPLCONFIGDIR and backend.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build'))
from lib.diagnostic_plot import install_x_zoom, load_audio_mono

import numpy as np
import matplotlib.pyplot as plt

from build.pybind_faust_attack_detector import attack_detector

# Mirror the constants from attack_detector.dsp (kept in sync by eye).
INHIBIT_MS      = 50    # inhibit_time = 0.050
RETRIGGER_RATIO = 1.4   # retrigger_ratio

def classify_triggers(trigger_indices, sample_rate):
  """Tag each trigger as 'normal' or 'retrigger' based on gap to previous."""
  flags = []
  for i, idx in enumerate(trigger_indices):
    if i == 0:
      flags.append(False)
    else:
      gap_ms = (idx - trigger_indices[i - 1]) / sample_rate * 1000.0
      flags.append(gap_ms < INHIBIT_MS + 5)
  return flags

def run(input_path):
  print("Attack Detector Diagnostic")
  print("=" * 60)

  sample_rate, audio_in = load_audio_mono(input_path)
  num_samples = len(audio_in)
  t = np.arange(num_samples) / sample_rate
  print(f"Input: {os.path.basename(input_path)}")
  print(f"  Sample rate: {sample_rate} Hz,  Duration: {num_samples/sample_rate:.2f} s,  Samples: {num_samples}")

  det = attack_detector()
  det.init(sample_rate)
  outs = det.process([audio_in.astype(np.float32)])
  trigger, threshold, fast_env, slow_env, note_ended, med_env = (np.asarray(o) for o in outs)

  trigger_indices = np.where(trigger > 0.5)[0]
  retrigger_flags = classify_triggers(trigger_indices, sample_rate)
  normal_idx = [idx for idx, rt in zip(trigger_indices, retrigger_flags) if not rt]
  retrig_idx = [idx for idx, rt in zip(trigger_indices, retrigger_flags) if rt]

  print(f"\nDetected {len(trigger_indices)} triggers "
        f"({len(normal_idx)} normal, {len(retrig_idx)} retrigger)")
  for i, idx in enumerate(trigger_indices):
    gap_ms = (idx - trigger_indices[i - 1]) / sample_rate * 1000 if i > 0 else 999
    kind = "RETRIG" if retrigger_flags[i] else "normal"
    fm_ratio = fast_env[idx] / (med_env[idx] + 1e-10)
    print(f"  {i+1:2d}. t={idx/sample_rate:.3f}s  {kind:6s}  "
          f"fast={fast_env[idx]:.4f}  med={med_env[idx]:.4f}  "
          f"fast/med={fm_ratio:.2f}  gap={gap_ms:.0f}ms")

  # Derivative of fast_env — the actual quantity tested against `threshold`
  # for normal triggers.  Per-sample diff (Faust uses x - x', i.e. n-vs-n-1).
  fast_deriv = np.diff(fast_env, prepend=fast_env[0])
  # Decision ratio for the normal trigger: fires when this exceeds 1.0 while armed.
  # Dimensionless, so a single y-range works across armed (tiny abs values) and
  # active (large abs values) regimes — unlike the raw deriv/threshold pair.
  deriv_ratio = fast_deriv / (threshold + 1e-12)

  # ---- Plot: 4 sharex'd panels, scroll-zoom on any propagates to all ----
  fig, axes = plt.subplots(4, 1, figsize=(13, 9), sharex=True)
  fig.suptitle(f"Attack Detector — {os.path.basename(input_path)}", fontsize=14)

  # Panel 1: waveform + triggers as oversized markers at signal amplitude
  ax0 = axes[0]
  ax0.plot(t, audio_in, 'b-', linewidth=0.3, alpha=0.5)
  if normal_idx:
    ax0.plot(t[normal_idx], audio_in[normal_idx], 'ro', ms=8, alpha=0.75, label=f'normal ({len(normal_idx)})')
  if retrig_idx:
    ax0.plot(t[retrig_idx], audio_in[retrig_idx], 'v', color='darkorange', ms=9, alpha=0.8, label=f'retrigger ({len(retrig_idx)})')
  ax0.set_ylabel('Amplitude')
  ax0.set_title('Input waveform with triggers')
  ax0.legend(loc='upper right', fontsize=8)
  ax0.grid(True, alpha=0.3)

  # Panel 2: absolute envelope levels with note_ended shaded
  ax1 = axes[1]
  ax1.plot(t, fast_env, 'r-', linewidth=0.8, label='fast_env (1ms/10ms)')
  ax1.plot(t, med_env,  'g-', linewidth=0.8, label='med_env (5ms/50ms)')
  ax1.plot(t, slow_env, 'b-', linewidth=0.8, label='slow_env (50ms/200ms)')
  ax1.plot(t, med_env * RETRIGGER_RATIO, 'g--', linewidth=0.6, alpha=0.7,
           label=f'med × {RETRIGGER_RATIO} (retrigger thresh)')
  ne = note_ended > 0.5
  ax1.fill_between(t, 0, fast_env.max() * 1.05, where=ne, color='yellow', alpha=0.15, label='note_ended (armed)')
  for idx in normal_idx: ax1.axvline(t[idx], color='red',        linewidth=0.5, alpha=0.4)
  for idx in retrig_idx: ax1.axvline(t[idx], color='darkorange', linewidth=0.5, alpha=0.4)
  ax1.set_ylabel('Level')
  ax1.set_title('Envelope levels (yellow = note_ended/armed)')
  ax1.legend(loc='upper right', fontsize=8)
  ax1.grid(True, alpha=0.3)

  # Panel 3: fast/med ratio (retrigger-path decision)
  ax2 = axes[2]
  fm_ratio = fast_env / (med_env + 1e-10)
  ax2.plot(t, fm_ratio, 'b-', linewidth=0.5, alpha=0.7)
  ax2.axhline(RETRIGGER_RATIO, color='red',  linewidth=1, linestyle='--', label=f'retrigger threshold ({RETRIGGER_RATIO})')
  ax2.axhline(1.0,             color='gray', linewidth=0.5, linestyle=':')
  for idx in normal_idx: ax2.axvline(t[idx], color='red',        linewidth=0.5, alpha=0.4)
  for idx in retrig_idx: ax2.axvline(t[idx], color='darkorange', linewidth=0.5, alpha=0.4)
  ax2.set_ylabel('fast / med')
  ax2.set_title('fast_env / med_env ratio (retrigger fires above red dashed)')
  ax2.legend(loc='upper right', fontsize=8)
  ax2.grid(True, alpha=0.3)
  ax2.set_ylim(0.4, 2.8)

  # Panel 4: Normal-trigger decision ratio — fast_deriv / threshold.
  # The trigger fires when this crosses 1.0 while armed. Dot height above the
  # red line is the trigger margin (1.0 = barely; 3.0 = comfortable).
  ax3 = axes[3]
  ylo, yhi = -0.5, 6.0
  ax3.plot(t, deriv_ratio, 'b-', linewidth=0.5, alpha=0.7, label='fast_deriv / threshold')
  ax3.axhline(1.0, color='red',  linewidth=1, linestyle='--', label='fire line (ratio = 1)')
  ax3.axhline(0.0, color='gray', linewidth=0.5, linestyle=':')
  ne = note_ended > 0.5
  ax3.fill_between(t, ylo, yhi, where=ne, color='yellow', alpha=0.12, label='note_ended (armed)')
  # Clip marker y-values into view so off-scale triggers still show at the top edge.
  if normal_idx:
    y = np.clip(deriv_ratio[normal_idx], ylo + 0.1, yhi - 0.2)
    ax3.plot(t[normal_idx], y, 'ro', ms=8, alpha=0.75, label=f'normal ({len(normal_idx)})')
  if retrig_idx:
    y = np.clip(deriv_ratio[retrig_idx], ylo + 0.1, yhi - 0.2)
    ax3.plot(t[retrig_idx], y, 'v', color='darkorange', ms=9, alpha=0.8, label=f'retrigger ({len(retrig_idx)})')
  ax3.set_xlabel('Time (s)')
  ax3.set_ylabel('deriv / thresh')
  ax3.set_title('Normal-trigger decision — fires when ratio crosses 1.0 while armed (yellow). Dot height above 1.0 = trigger margin.')
  ax3.legend(loc='upper right', fontsize=8)
  ax3.grid(True, alpha=0.3)
  ax3.set_ylim(ylo, yhi)

  # Set xlim on one axis — sharex propagates to the others.
  ax0.set_xlim(0, t[-1])

  plt.tight_layout(rect=[0, 0.02, 1, 0.97])
  plt.subplots_adjust(hspace=0.35)
  install_x_zoom(fig, x_min=0.0, x_max=t[-1])

  out_png = os.path.join(os.path.dirname(__file__), 'attack_detector_diagnostic.png')
  plt.savefig(out_png, dpi=150)
  print(f"\nPlot saved: {out_png}")
  plt.show()
  print("=" * 60 + "\nDiagnostic complete")

if __name__ == '__main__':
  input_path = os.path.join(os.path.dirname(__file__), '..', '..', '..',
                            'test_audio', 'Bass Notes No Gap.wav')
  run(input_path)
