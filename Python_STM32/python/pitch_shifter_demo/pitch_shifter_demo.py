"""
Pitch Shifter demo — using the graph-compiler-generated pipeline.

One process_chunk() call feeds the whole file through; per-block buffers are
probed by name for diagnostics. Saves output WAV + a 4-panel probe plot:
  1. Input (post-LPF) + event markers
  2. Three tap delays (left) + output audio (right) + thresholds
  3. Three tap gains
  4. HR selector tint + P estimate + gated/bailout markers
Scroll wheel zooms x on all panels.
"""
import sys
import os

# Must precede matplotlib.pyplot — diagnostic_plot sets MPLCONFIGDIR and backend.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build'))
from lib.diagnostic_plot import install_x_zoom

import numpy as np
import scipy.io.wavfile as wav
import matplotlib.pyplot as plt

from build.pybind_pitch_shifter import pitch_shifter

# Mirror the constants from loop_controller.h (kept in sync by eye).
LOWER_THRESHOLD_MS = 100.0
UPPER_THRESHOLD_MS = 200.0
N_HR_FILTERS       = 3

def pitch_ratio_label(ratio):
  return {0.5: "octave down", 0.75: "fourth down", 0.667: "fifth down",
          0.794: "major third down"}.get(round(ratio, 3), f"ratio {ratio:.3f}")

def run_demo(filename, pitch_ratio=0.5, lpf_fc_hz=10000.0, show_plot=True):
  print("Pitch Shifter (generated pipeline)")
  print("=" * 60)
  print(f"Pitch ratio: {pitch_ratio}")
  print(f"Input LPF:   {lpf_fc_hz:.0f} Hz")

  input_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'test_audio', filename)
  sample_rate, audio_data = wav.read(input_path)
  if audio_data.dtype == np.int16:
    audio_raw = audio_data.astype(np.float64) / 32768.0
  elif audio_data.dtype == np.int32:
    audio_raw = audio_data.astype(np.float64) / 2147483648.0
  else:
    audio_raw = audio_data.astype(np.float64)
  if audio_raw.ndim > 1:
    audio_raw = audio_raw[:, 0]
  num_samples = len(audio_raw)
  print(f"\nInput: {os.path.basename(input_path)}")
  print(f"  Sample rate: {sample_rate} Hz,  Duration: {num_samples/sample_rate:.2f} s,  Samples: {num_samples}")

  if num_samples > pitch_shifter.CHUNK_SIZE:
    raise RuntimeError(f"file length {num_samples} exceeds CHUNK_SIZE {pitch_shifter.CHUNK_SIZE}; rebuild with larger CHUNK_SIZE")

  ps = pitch_shifter()
  ps.init(sample_rate)
  ps.set_param('lpf.fc', lpf_fc_hz)
  ps.set_param('lc.pitch_ratio', pitch_ratio)

  audio_in = audio_raw.astype(np.float32)
  print("\nProcessing...")
  audio_out = ps.process_chunk(audio_in)

  N = num_samples
  audio_lpf   = ps.get_buffer('lpf.out', N)
  zc_impulse  = ps.get_buffer('zc.zc_out', N)
  atk_trigger = ps.get_buffer('atk.trigger', N)
  atk_thresh  = ps.get_buffer('atk.threshold', N)
  atk_fast    = ps.get_buffer('atk.fast_env', N)
  atk_slow    = ps.get_buffer('atk.slow_env', N)
  atk_med     = ps.get_buffer('atk.med_env', N)
  atk_hold    = ps.get_buffer('atk.hold_env', N)
  atk_ended   = ps.get_buffer('atk.note_ended', N)
  P_samples   = ps.get_buffer('hr.P', N)
  qualified   = ps.get_buffer('hr.qualified', N)
  selected    = ps.get_buffer('hr.selected_filter', N)
  tap1_del    = ps.get_buffer('lc.tap1_delay_ms', N)
  tap2_del    = ps.get_buffer('lc.tap2_delay_ms', N)
  tap3_del    = ps.get_buffer('lc.tap3_delay_ms', N)
  gain1_arr   = ps.get_buffer('lc.gain1', N)
  gain2_arr   = ps.get_buffer('lc.gain2', N)
  gain3_arr   = ps.get_buffer('lc.gain3', N)
  loop_evts   = ps.get_buffer('lc.loop_event', N)
  bailout_evt = ps.get_buffer('lc.bailout_event', N)
  gated_evts  = ps.get_buffer('lc.gated_event', N)
  attack_evts = ps.get_buffer('lc.attack_event', N)

  loop_indices    = np.where(loop_evts   > 0.5)[0]
  bailout_indices = np.where(bailout_evt > 0.5)[0]
  attack_indices  = np.where(attack_evts > 0.5)[0]
  gated_indices   = np.where(gated_evts  > 0.5)[0]

  print(f"  ZC qualified:   {int((zc_impulse > 0.5).sum())}")
  print(f"  HR qualified:   {int((qualified > 0.5).sum())}/{N} ({100*int((qualified>0.5).sum())/N:.0f}%)")
  print(f"  Loop trans:     {len(loop_indices)} (gate-redirected: {len(gated_indices)})")
  print(f"  Bailouts:       {len(bailout_indices)}")
  if len(bailout_indices):
    print(f"    Times (s):    {', '.join(f'{i/sample_rate:.3f}' for i in bailout_indices)}")
  print(f"  Attack det:     {int((atk_trigger > 0.5).sum())}  (acted on: {len(attack_indices)})")
  print(f"  Max tap1 delay: {tap1_del.max():.1f} ms")
  print(f"  Max tap2 delay: {tap2_del.max():.1f} ms")
  print(f"  Max tap3 delay: {tap3_del.max():.1f} ms")

  out_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'test_audio_out')
  os.makedirs(out_dir, exist_ok=True)
  ratio_str = f"{int(round(pitch_ratio*100))}pct"
  out_path = os.path.join(out_dir, f"pitch_shifted_generated_{ratio_str}.wav")
  ao = np.asarray(audio_out, dtype=np.float64)
  peak = np.abs(ao).max()
  if peak > 0: ao /= peak * 1.05
  out_int16 = np.clip(ao * 32767, -32768, 32767).astype(np.int16)
  wav.write(out_path, sample_rate, out_int16)
  print(f"\nOutput saved: {out_path}")

  if not show_plot:
    return out_path

  # ---------------------------------------------------------------
  # Two figures (independent windows): pipeline (4 panels), attack-detector
  # probes (3 panels). Each window has its own scroll-wheel x-zoom.
  # ---------------------------------------------------------------
  t = np.arange(N) / sample_rate

  fig, axes = plt.subplots(4, 1, figsize=(16, 11), sharex=True,
                           gridspec_kw={'height_ratios': [2, 3, 1, 2]},
                           num='Pitch Shifter')
  fig.suptitle(f"Pitch Shifter — {pitch_ratio_label(pitch_ratio)}  "
               f"({os.path.basename(input_path)}, LPF {lpf_fc_hz:.0f} Hz)",
               fontsize=14)
  fig.text(0.5, 0.955, "scroll = zoom x  •  toolbar Home resets  "
                       "•  green=loop, red=bailout, orange=attack",
           ha='center', fontsize=9, style='italic', color='#555')

  def mark_events(ax, ymax=None):
    for idx in loop_indices:    ax.axvline(t[idx], color='green',  linewidth=0.8, alpha=0.35)
    for idx in bailout_indices: ax.axvline(t[idx], color='red',    linewidth=1.0, alpha=0.6)
    for idx in attack_indices:  ax.axvline(t[idx], color='orange', linewidth=1.0, alpha=0.6)

  # Panel 1: input post-LPF
  axes[0].plot(t, audio_lpf, 'b-', linewidth=0.3, alpha=0.7, label='Input (post-LPF)')
  mark_events(axes[0])
  axes[0].set_ylabel('Amplitude')
  axes[0].set_title('Input post-LPF')
  axes[0].legend(loc='upper right', fontsize=8)
  axes[0].grid(True, alpha=0.3)
  axes[0].set_xlim(0, t[-1])

  # Panel 2: tap delays (left) + output audio (right twin)
  ax_out = axes[1].twinx()
  axes[1].plot(t, tap1_del, 'b-',  linewidth=0.7, alpha=0.9, label='Tap 1 delay (ms)')
  axes[1].plot(t, tap2_del, 'C1-', linewidth=0.7, alpha=0.9, label='Tap 2 delay (ms)')
  axes[1].plot(t, tap3_del, 'm-',  linewidth=0.7, alpha=0.9, label='Tap 3 delay (ms, attack)')
  axes[1].axhline(LOWER_THRESHOLD_MS, color='green', linewidth=1.0, linestyle='--',
                  label=f'Lower threshold ({LOWER_THRESHOLD_MS:.0f} ms)')
  axes[1].axhline(UPPER_THRESHOLD_MS, color='red',   linewidth=1.0, linestyle='--',
                  label=f'Upper threshold ({UPPER_THRESHOLD_MS:.0f} ms)')
  mark_events(axes[1])
  axes[1].set_ylabel('Delay (ms)')
  axes[1].grid(True, alpha=0.3)
  ax_out.plot(t, ao, color='#999', linewidth=0.3, alpha=0.8, label='Output audio')
  ax_out.set_ylabel('Output amplitude', color='#555')
  ax_out.tick_params(axis='y', labelcolor='#555')
  lines1, labels1 = axes[1].get_legend_handles_labels()
  lines2, labels2 = ax_out.get_legend_handles_labels()
  axes[1].legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=8)
  axes[1].set_title('Tap delays (left) + output audio (grey, right)')

  # Panel 3: tap gains
  axes[2].plot(t, gain1_arr, 'b-',  linewidth=0.8, alpha=0.9, label='Gain 1')
  axes[2].plot(t, gain2_arr, 'C1-', linewidth=0.8, alpha=0.9, label='Gain 2')
  axes[2].plot(t, gain3_arr, 'm-',  linewidth=0.8, alpha=0.9, label='Gain 3 (attack)')
  mark_events(axes[2])
  axes[2].set_ylabel('Gain')
  axes[2].set_ylim(-0.05, 1.1)
  axes[2].legend(loc='upper right', fontsize=8)
  axes[2].grid(True, alpha=0.3)

  # Panel 4: HR selector + P estimate
  filter_colors = ['green', 'C1', 'purple']
  sel = selected.astype(int)
  boundaries = np.concatenate(([0], np.where(np.diff(sel) != 0)[0] + 1, [len(sel)]))
  for s, e in zip(boundaries[:-1], boundaries[1:]):
    fi = sel[s]
    if 0 <= fi < N_HR_FILTERS:
      axes[3].axvspan(t[s], t[e-1], color=filter_colors[fi], alpha=0.15, lw=0)
  P_ms = P_samples / sample_rate * 1000.0
  P_ms_plot = np.where(qualified > 0.5, P_ms, np.nan)
  axes[3].plot(t, P_ms_plot, 'k-', linewidth=0.6, alpha=0.85, label='P (ms, qualified only)')
  if len(gated_indices):
    axes[3].plot(t[gated_indices], np.full(len(gated_indices), 48.0),
                 'bv', ms=6, alpha=0.7, label='gate-redirected loop')
  if len(bailout_indices):
    axes[3].plot(t[bailout_indices], np.full(len(bailout_indices), 5.0),
                 'r^', ms=8, alpha=0.7, label='bailout')
  axes[3].set_xlabel('Time (s)')
  axes[3].set_ylabel('P (ms)')
  axes[3].set_ylim(0, 50)
  axes[3].legend(loc='upper right', fontsize=8)
  axes[3].grid(True, alpha=0.3)
  axes[3].set_title('HR selector tint (green=0 / orange=1 / purple=2); black=P; markers per legend')

  install_x_zoom(fig, x_min=0.0, x_max=t[-1])
  plt.tight_layout(rect=[0, 0, 1, 0.97])
  plt.subplots_adjust(hspace=0.35)
  plot_path = os.path.join(out_dir, f"pitch_shifter_generated_{ratio_str}.png")
  plt.savefig(plot_path, dpi=150)
  print(f"Plot saved:   {plot_path}")

  # ---------------------------------------------------------------
  # Figure 2: attack-detector probes (3 panels). Input audio for time
  # reference, then envelopes+threshold, then decision ratios.
  # ---------------------------------------------------------------
  fig2, ax2 = plt.subplots(3, 1, figsize=(16, 10), sharex=True,
                           gridspec_kw={'height_ratios': [2, 3, 2]},
                           num='Attack Detector Probes')
  fig2.suptitle(f"Attack Detector — {os.path.basename(input_path)}  "
                f"(detected: {int((atk_trigger > 0.5).sum())} triggers, acted on: {len(attack_indices)})",
                fontsize=14)
  fig2.text(0.5, 0.955, "scroll = zoom x  •  toolbar Home resets  "
                        "•  yellow tint = note_ended (armed regime)",
            ha='center', fontsize=9, style='italic', color='#555')

  # Panel 1: input audio for reference
  ax2[0].plot(t, audio_lpf, 'b-', linewidth=0.3, alpha=0.7, label='Input (post-LPF)')
  for idx in attack_indices: ax2[0].axvline(t[idx], color='orange', linewidth=1.0, alpha=0.6)
  ax2[0].set_ylabel('Amplitude')
  ax2[0].set_title('Input post-LPF (= signal seen by attack detector)')
  ax2[0].legend(loc='upper right', fontsize=8)
  ax2[0].grid(True, alpha=0.3)
  ax2[0].set_xlim(0, t[-1])

  # Panel 2: envelopes + decision threshold; legacy note_ended tinted for ref.
  ended_runs = np.concatenate(([0], np.where(np.diff(atk_ended > 0.5) != 0)[0] + 1, [len(atk_ended)]))
  for s, e in zip(ended_runs[:-1], ended_runs[1:]):
    if atk_ended[s] > 0.5:
      ax2[1].axvspan(t[s], t[e-1], color='yellow', alpha=0.10, lw=0)
  ax2[1].plot(t, atk_fast,   'b-',  linewidth=0.7, alpha=0.9, label='fast_env (1/10 ms)')
  ax2[1].plot(t, atk_med,    'C1-', linewidth=0.6, alpha=0.6, label='med_env (5/50 ms, legacy)')
  ax2[1].plot(t, atk_slow,   'g-',  linewidth=0.7, alpha=0.9, label='slow_env (50/200 ms)')
  ax2[1].plot(t, atk_hold,   'm-',  linewidth=0.7, alpha=0.9, label='hold_env (5ms / 24ms hold / 50ms)')
  ax2[1].plot(t, atk_thresh, 'r--', linewidth=0.8, alpha=0.8, label='threshold = slow × K (decision line)')
  atk_trig_idx = np.where(atk_trigger > 0.5)[0]
  if len(atk_trig_idx):
    ax2[1].plot(t[atk_trig_idx], np.full(len(atk_trig_idx), atk_fast.max() * 0.95),
                'rv', ms=8, alpha=0.8, label=f'atk trigger ({len(atk_trig_idx)})')
  for idx in attack_indices: ax2[1].axvline(t[idx], color='orange', linewidth=1.0, alpha=0.6)
  ax2[1].set_ylabel('Envelope level')
  ax2[1].legend(loc='upper right', fontsize=8)
  ax2[1].grid(True, alpha=0.3)
  ax2[1].set_title('Envelopes + decision threshold (yellow tint = legacy note_ended, no longer used)')

  # Panel 3: candidate denominators — fast/slow (current rule) vs fast/hold
  # (proposed alternative). Both above 1.0 indicate fast has exceeded the
  # reference; the dashed red line is the K=1.5 fire level for fast/slow.
  fs_ratio = atk_fast / (atk_slow + 1e-12)
  fh_ratio = atk_fast / (atk_hold + 1e-12)
  ax2[2].plot(t, fs_ratio, 'g-', linewidth=0.6, alpha=0.85, label='fast / slow (current rule denominator)')
  ax2[2].plot(t, fh_ratio, 'm-', linewidth=0.6, alpha=0.85, label='fast / hold (proposed alternative)')
  ax2[2].axhline(1.0, color='black', linewidth=0.5, linestyle=':',  alpha=0.5)
  ax2[2].axhline(1.5, color='red',   linewidth=0.8, linestyle='--', alpha=0.6, label='K = 1.5 (fire level)')
  for idx in attack_indices: ax2[2].axvline(t[idx], color='orange', linewidth=1.0, alpha=0.6)
  ax2[2].set_xlabel('Time (s)')
  ax2[2].set_ylabel('Ratio')
  ax2[2].set_ylim(0, 4.0)
  ax2[2].legend(loc='upper right', fontsize=8)
  ax2[2].grid(True, alpha=0.3)
  ax2[2].set_title('Decision ratios: fast/slow vs fast/hold — pick the one that separates attacks from sustain most cleanly')

  install_x_zoom(fig2, x_min=0.0, x_max=t[-1])
  fig2.tight_layout(rect=[0, 0, 1, 0.97])
  fig2.subplots_adjust(hspace=0.35)
  plot2_path = os.path.join(out_dir, f"attack_detector_in_pipeline_{ratio_str}.png")
  fig2.savefig(plot2_path, dpi=150)
  print(f"Plot saved:   {plot2_path}")

  plt.show()
  return out_path

if __name__ == '__main__':
  pitch_ratio = 0.5
  lpf_fc_hz   = 10000.0
  run_demo("bass notes no gap.wav", pitch_ratio=pitch_ratio, lpf_fc_hz=lpf_fc_hz)
  print("\n" + "=" * 60 + "\nDemo complete")
