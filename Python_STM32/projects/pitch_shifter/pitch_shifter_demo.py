"""
Pitch Shifter demo — using the graph-compiler-generated pipeline.

One process_chunk() call feeds the whole file through; per-block buffers are
probed by name for diagnostics. Saves output WAV and shows interactive plots:
  1. Input (post-LPF) + event markers
  2. Output audio (shifted)
  3. Three tap delays + thresholds
  4. Three tap gains
  5. HR selector tint + P estimate + gated/bailout markers
Scroll wheel zooms x on all panels.
"""
import sys
import os

# Must precede matplotlib.pyplot — diagnostic_plot sets MPLCONFIGDIR and backend.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build'))
from lib.diagnostic_plot import install_x_zoom, mark_events as draw_events

import numpy as np
import scipy.io.wavfile as wav
import matplotlib.pyplot as plt

from build.pybind_pitch_shifter import pitch_shifter

# Mirror the constants from loop_controller.h (kept in sync by eye).
LOWER_THRESHOLD_MS = 50.0
UPPER_THRESHOLD_MS = 200.0
N_HR_FILTERS       = 3

# Drive intervals from equal-tempered semitones so every interval is consistent:
# the playback ratio is 2**(st/12). (Hardcoding e.g. 0.75 for a fourth gives the
# JUST fourth, 3/4; the tempered fourth down is 2**(-5/12) ≈ 0.749.)
SEMITONE_NAMES = {
  0: "unison",            -1: "minor 2nd down",   -2: "major 2nd down",
  -3: "minor 3rd down",   -4: "major 3rd down",   -5: "fourth down",
  -6: "tritone down",     -7: "fifth down",       -8: "minor 6th down",
  -9: "major 6th down",  -10: "minor 7th down",  -11: "major 7th down",
  -12: "octave down",
}

def semitones_to_ratio(semitones):
  return 2.0 ** (semitones / 12.0)

def pitch_ratio_label(ratio):
  st = int(round(12.0 * np.log2(ratio)))
  return f"{SEMITONE_NAMES.get(st, f'{st:+d} st')} ({ratio:.4f})"

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
  ps.set_param('splice.attack_to_wet_ms', 10.0)   # attack → wet crossfade time
  ps.set_param('splice.note_end_fade_ms', 50.0)   # note-end fade-to-dry time

  audio_in = audio_raw.astype(np.float32)
  print("\nProcessing...")
  audio_out = ps.process_chunk(audio_in)

  N = num_samples
  audio_lpf   = ps.get_buffer('lpf.out', N)
  atk_trigger = ps.get_buffer('atk.trigger', N)
  atk_thresh  = ps.get_buffer('atk.threshold', N)        # = ref_env * k_live (boosted threshold)
  atk_fast    = ps.get_buffer('atk.fast_env', N)
  atk_slow    = ps.get_buffer('atk.slow_env', N)
  atk_hold    = ps.get_buffer('atk.hold_env', N)
  atk_dive    = ps.get_buffer('atk.dive_strength', N)
  atk_keff    = ps.get_buffer('atk.k_effective', N)
  atk_gain    = ps.get_buffer('atk.active_gain', N)      # = 1 - dive_strength
  atk_ref     = ps.get_buffer('atk.ref_env', N)          # trigger reference (two-stage-attack follower of fast)
  P_samples   = ps.get_buffer('yd.P', N)
  aperiodic   = np.asarray(ps.get_buffer('yd.aperiodicity', N))
  confidence  = 1.0 - aperiodic
  qualified   = (aperiodic <= 0.4).astype(np.float32)   # APERIODICITY_THRESH in loop_controller.h
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
  splice_mix  = ps.get_buffer('splice.dry_mix', N)   # 1 = dry live, 0 = full wet
  gate_mean   = ps.get_buffer('lc.active_gain_mean', N)  # period-mean of active_gain (wet-tap gate)

  loop_indices    = np.where(loop_evts   > 0.5)[0]
  bailout_indices = np.where(bailout_evt > 0.5)[0]
  attack_indices  = np.where(attack_evts > 0.5)[0]
  gated_indices   = np.where(gated_evts  > 0.5)[0]

  print(f"  YIN confident:  {int((qualified > 0.5).sum())}/{N} ({100*int((qualified>0.5).sum())/N:.0f}%)")
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
  semitones = int(round(12.0 * np.log2(pitch_ratio)))   # tempered: 0.5 -> -12, 0.749 -> -5
  input_stem = os.path.splitext(os.path.basename(input_path))[0]
  out_path = os.path.join(out_dir, f"{input_stem}_pitch_shifted_{semitones:+d}st.wav")
  # audio_out shape: (N, 2)  — column 0 = dry (audio_in), column 1 = spliced
  # (dry/wet crossfade from output_splicer). Normalize jointly so the L/R level
  # relationship is preserved.
  ao = np.asarray(audio_out, dtype=np.float64)
  peak = np.abs(ao).max()
  if peak > 0: ao /= peak * 1.05
  out_int16 = np.clip(ao * 32767, -32768, 32767).astype(np.int16)
  wav.write(out_path, sample_rate, out_int16)
  print(f"\nOutput saved (stereo, L=dry / R=spliced): {out_path}")
  # Extract the spliced output channel for in-script plotting/analysis below.
  audio_shifted = ao[:, 1]

  if not show_plot:
    return out_path

  # ---------------------------------------------------------------
  # Two figures (independent windows): pipeline (4 panels), attack-detector
  # probes (3 panels). Each window has its own scroll-wheel x-zoom.
  # ---------------------------------------------------------------
  t = np.arange(N) / sample_rate

  fig, axes = plt.subplots(5, 1, figsize=(16, 13), sharex=True,
                           gridspec_kw={'height_ratios': [2, 2, 3, 1, 2]},
                           num='Pitch Shifter')
  fig.suptitle(f"Pitch Shifter — {pitch_ratio_label(pitch_ratio)}  "
               f"({os.path.basename(input_path)}, LPF {lpf_fc_hz:.0f} Hz)",
               fontsize=14)
  fig.text(0.5, 0.955, "scroll = zoom x  •  toolbar Home resets  "
                       "•  green=loop, red=bailout, orange=attack",
           ha='center', fontsize=9, style='italic', color='#555')

  def mark_events(ax, ymax=None):
    draw_events(ax, t, loop_indices,    color='green',  lw=0.8, alpha=0.35)
    draw_events(ax, t, bailout_indices, color='red',    lw=1.0, alpha=0.6)
    draw_events(ax, t, attack_indices,  color='orange', lw=1.0, alpha=0.6)

  # Panel 1: input post-LPF
  axes[0].plot(t, audio_lpf, 'b-', linewidth=0.3, alpha=0.7, label='Input (post-LPF)')
  mark_events(axes[0])
  axes[0].set_ylabel('Amplitude')
  axes[0].set_title('Input post-LPF')
  axes[0].legend(loc='upper right', fontsize=8)
  axes[0].grid(True, alpha=0.3)
  axes[0].set_xlim(0, t[-1])

  # Panel 2: spliced output + dry-mix envelope (1 = dry live, 0 = full wet).
  axes[1].plot(t, audio_shifted, 'b-', linewidth=0.3, alpha=0.7, label='Output audio (R = spliced)')
  mark_events(axes[1])
  axes[1].set_ylabel('Output amplitude')
  axes[1].grid(True, alpha=0.3)
  a1b = axes[1].twinx()
  a1b.plot(t, splice_mix, color='#c4007a', linewidth=0.8, alpha=0.8, label='dry_mix (1=dry, 0=wet)')
  a1b.set_ylabel('dry_mix', color='#c4007a'); a1b.set_ylim(-0.05, 1.05)
  a1b.tick_params(axis='y', labelcolor='#c4007a')
  l1, lab1 = axes[1].get_legend_handles_labels()
  l2, lab2 = a1b.get_legend_handles_labels()
  axes[1].legend(l1 + l2, lab1 + lab2, loc='upper right', fontsize=8)
  axes[1].set_title('Spliced output + dry/wet mix envelope')

  # Panel 3: tap delays
  axes[2].plot(t, tap1_del, 'b-',  linewidth=0.7, alpha=0.9, label='Tap 1 delay (ms)')
  axes[2].plot(t, tap2_del, 'C1-', linewidth=0.7, alpha=0.9, label='Tap 2 delay (ms)')
  axes[2].plot(t, tap3_del, 'm-',  linewidth=0.7, alpha=0.9, label='Tap 3 delay (ms, attack)')
  axes[2].axhline(LOWER_THRESHOLD_MS, color='green', linewidth=1.0, linestyle='--',
                  label=f'Lower threshold ({LOWER_THRESHOLD_MS:.0f} ms)')
  axes[2].axhline(UPPER_THRESHOLD_MS, color='red',   linewidth=1.0, linestyle='--',
                  label=f'Upper threshold ({UPPER_THRESHOLD_MS:.0f} ms)')
  mark_events(axes[2])
  axes[2].set_ylabel('Delay (ms)')
  axes[2].grid(True, alpha=0.3)
  axes[2].legend(loc='upper right', fontsize=8)
  axes[2].set_title('Tap delays')

  # Panel 4: tap gains + wet-tap gate (raw active_gain vs its period-mean).
  # The raw trace ripples at the note fundamental on low notes; the period-mean
  # (applied to the non-attack taps) nulls that ripple.
  axes[3].plot(t, gain1_arr, 'b-',  linewidth=0.8, alpha=0.9, label='Gain 1')
  axes[3].plot(t, gain2_arr, 'C1-', linewidth=0.8, alpha=0.9, label='Gain 2')
  axes[3].plot(t, gain3_arr, 'm-',  linewidth=0.8, alpha=0.9, label='Gain 3 (attack)')
  axes[3].plot(t, atk_gain,  color='#bbb', linewidth=0.5, alpha=0.8, label='active_gain (raw)')
  axes[3].plot(t, gate_mean, 'k-',  linewidth=0.8, alpha=0.8, label='gate (active_gain period-mean)')
  mark_events(axes[3])
  axes[3].set_ylabel('Gain')
  axes[3].set_ylim(-0.05, 1.1)
  axes[3].legend(loc='upper right', fontsize=8)
  axes[3].grid(True, alpha=0.3)

  # Panel 5: YIN period estimate + confidence
  P_ms = np.asarray(P_samples) / sample_rate * 1000.0
  P_ms_plot = np.where(qualified > 0.5, P_ms, np.nan)
  axes[4].plot(t, P_ms_plot, 'k-', linewidth=0.6, alpha=0.85, label='P (ms, confident only)')
  a4b = axes[4].twinx()
  a4b.plot(t, confidence, color='C2', linewidth=0.6, alpha=0.55, label='confidence')
  a4b.axhline(0.6, color='C2', linewidth=0.8, linestyle='--', alpha=0.5)   # 1 - APERIODICITY_THRESH
  a4b.set_ylabel('confidence', color='C2'); a4b.set_ylim(-0.05, 1.05)
  draw_events(axes[4], t, gated_indices,   marker='v', y=48.0, color='b', ms=6, alpha=0.7, label='loop suppressed')
  draw_events(axes[4], t, bailout_indices, marker='^', y=5.0,  color='r', ms=8, alpha=0.7, label='bailout')
  axes[4].set_xlabel('Time (s)')
  axes[4].set_ylabel('P (ms)')
  axes[4].set_ylim(0, 50)
  axes[4].legend(loc='upper right', fontsize=8)
  axes[4].grid(True, alpha=0.3)
  axes[4].set_title('YIN period P (black, confident only) + confidence (green, dashed = gate)')

  install_x_zoom(fig, x_min=0.0, x_max=t[-1])
  plt.tight_layout(rect=[0, 0, 1, 0.97])
  plt.subplots_adjust(hspace=0.35)

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
                        "•  orange lines = attack events acted on by loop controller",
            ha='center', fontsize=9, style='italic', color='#555')

  # Panel 1: input audio for reference
  ax2[0].plot(t, audio_lpf, 'b-', linewidth=0.3, alpha=0.7, label='Input (post-LPF)')
  for idx in attack_indices: ax2[0].axvline(t[idx], color='orange', linewidth=1.0, alpha=0.6)
  ax2[0].set_ylabel('Amplitude')
  ax2[0].set_title('Input post-LPF (= signal seen by attack detector)')
  ax2[0].legend(loc='upper right', fontsize=8)
  ax2[0].grid(True, alpha=0.3)
  ax2[0].set_xlim(0, t[-1])

  # Panel 2: envelopes + live decision threshold (= ref_env × k_live, the boosted threshold).
  ax2[1].plot(t, atk_fast,   'b-',  linewidth=0.7, alpha=0.9, label='fast_env (peak track, 25ms hold)')
  ax2[1].plot(t, atk_hold,   'm-',  linewidth=0.6, alpha=0.5, label='hold_env (probe/dive only)')
  ax2[1].plot(t, atk_slow,   'g-',  linewidth=0.6, alpha=0.5, label='slow_env (200ms/1s — dive ref)')
  ax2[1].plot(t, atk_ref,    'c-',  linewidth=1.0, alpha=0.95, label='ref_env (two-stage-attack follower of fast — trigger ref)')
  ax2[1].plot(t, atk_thresh, 'r--', linewidth=0.9, alpha=0.85, label='threshold = ref × k_live (boosts on fire)')
  atk_trig_idx = np.where(atk_trigger > 0.5)[0]
  if len(atk_trig_idx):
    ax2[1].plot(t[atk_trig_idx], np.full(len(atk_trig_idx), atk_fast.max() * 0.95),
                'rv', ms=8, alpha=0.8, label=f'atk trigger ({len(atk_trig_idx)})')
  for idx in attack_indices: ax2[1].axvline(t[idx], color='orange', linewidth=1.0, alpha=0.6)
  ax2[1].set_ylabel('Envelope level')
  ax2[1].legend(loc='upper right', fontsize=8)
  ax2[1].grid(True, alpha=0.3)
  ax2[1].set_title('Envelopes + live threshold — trigger fires when fast crosses threshold')

  # Panel 3: trigger decision plane — fast/ref ratio (blue) against the LIVE
  # threshold k (red, recovered as threshold/ref so both live on the same axis).
  # k rests at k_nom=2, snaps to k_boost=20 on each fire, then decays back — the
  # boosted-threshold holdoff. A fire is "blue crosses above red" on a rising
  # edge across the live threshold (no debounce).
  RATIO_CLIP = 22.0
  fr_ratio   = np.clip(atk_fast / (atk_ref + 1e-12), 0, RATIO_CLIP)
  k_live     = np.clip(atk_thresh / (atk_ref + 1e-12), 0, RATIO_CLIP)
  ax_dive    = ax2[2].twinx()
  ax2[2].plot(t, fr_ratio, color='#0066cc', linewidth=0.7, alpha=0.9,
              label='fast/ref ratio')
  ax2[2].plot(t, k_live, 'r-', linewidth=0.9, alpha=0.85,
              label='k_live (rests at 2, boosts to 20 on each fire)')
  ax2[2].axhline(2.0, color='gray', linewidth=0.6, linestyle=':',
                 label='k_nom (resting threshold = 2.0)')
  atk_trig_idx = np.where(atk_trigger > 0.5)[0]
  if len(atk_trig_idx):
    ax2[2].plot(t[atk_trig_idx], fr_ratio[atk_trig_idx],
                'rv', ms=7, alpha=0.85, label=f'fires ({len(atk_trig_idx)})')
  for idx in attack_indices: ax2[2].axvline(t[idx], color='orange', linewidth=1.0, alpha=0.6)
  ax2[2].set_xlabel('Time (s)')
  ax2[2].set_ylabel('fast/ref ratio')
  ax2[2].set_ylim(0, RATIO_CLIP)
  ax_dive.plot(t, atk_dive, color='#0a7', linewidth=0.5, alpha=0.7, label='dive_strength (0..1)')
  ax_dive.set_ylabel('dive_strength', color='#0a7')
  ax_dive.set_ylim(0, 1.0)
  ax_dive.tick_params(axis='y', labelcolor='#0a7')
  lines1, labels1 = ax2[2].get_legend_handles_labels()
  lines2, labels2 = ax_dive.get_legend_handles_labels()
  ax2[2].legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=8)
  ax2[2].grid(True, alpha=0.3)
  ax2[2].set_title('Trigger decision — blue = fast/ref ratio, red = live threshold k_live '
                   '(rests at 2, boosts to 20 per fire, decays back). Blue crossing above red = fire.')

  install_x_zoom(fig2, x_min=0.0, x_max=t[-1])
  fig2.tight_layout(rect=[0, 0, 1, 0.97])
  fig2.subplots_adjust(hspace=0.35)

  plt.show()
  return out_path

if __name__ == '__main__':
  interval_semitones = -5   # equal-tempered; -5 = fourth, -7 = fifth, -4 = major 3rd
  pitch_ratio = semitones_to_ratio(interval_semitones)
  lpf_fc_hz   = 10000.0
  run_demo("Fourth test.wav", pitch_ratio=pitch_ratio, lpf_fc_hz=lpf_fc_hz)
  print("\n" + "=" * 60 + "\nDemo complete")
