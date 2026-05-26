"""
Pitch Shifter demo — using the graph-compiler-generated pipeline.

One process_chunk() call feeds the whole file through; per-block buffers are
probed by name for diagnostics. Compare against the manual demo's WAV output.
"""
import sys
import os
import numpy as np
import scipy.io.wavfile as wav
import matplotlib
matplotlib.use('macosx')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build'))

from build.pybind_pitch_shifter import PitchShifter

def run_demo(pitch_ratio=0.5, lpf_fc_hz=10000.0):
  print("Pitch Shifter (generated pipeline)")
  print("=" * 60)
  print(f"Pitch ratio: {pitch_ratio}")
  print(f"Input LPF:   {lpf_fc_hz:.0f} Hz")

  input_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'test_audio', 'Longer Bass Notes.wav')
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

  if num_samples > PitchShifter.CHUNK_SIZE:
    raise RuntimeError(f"file length {num_samples} exceeds CHUNK_SIZE {PitchShifter.CHUNK_SIZE}; rebuild with larger CHUNK_SIZE")

  ps = PitchShifter()
  ps.init(sample_rate)
  ps.set_param('lpf.fc', lpf_fc_hz)
  ps.set_param('lc.pitch_ratio', pitch_ratio)

  audio_in = audio_raw.astype(np.float32)
  print("\nProcessing...")
  audio_out = ps.process_chunk(audio_in)

  # Probe diagnostic signals (all the same length as audio_in)
  N = num_samples
  zc_impulse  = ps.get_buffer('zc.zc_out', N)
  atk_trigger = ps.get_buffer('atk.trigger', N)
  P_samples   = ps.get_buffer('hr.P', N)
  qualified   = ps.get_buffer('hr.qualified', N)
  selected    = ps.get_buffer('hr.selected_filter', N)
  tap1_del    = ps.get_buffer('lc.tap1_delay_ms', N)
  tap2_del    = ps.get_buffer('lc.tap2_delay_ms', N)
  gain1_arr   = ps.get_buffer('lc.gain1', N)
  gain2_arr   = ps.get_buffer('lc.gain2', N)
  loop_evts   = ps.get_buffer('lc.loop_event', N)
  bailout_evt = ps.get_buffer('lc.bailout_event', N)
  gated_evts  = ps.get_buffer('lc.gated_event', N)

  print(f"  ZC qualified:   {int((zc_impulse > 0.5).sum())}")
  print(f"  HR qualified:   {int((qualified > 0.5).sum())}/{N} ({100*int((qualified>0.5).sum())/N:.0f}%)")
  print(f"  Loop trans:     {int((loop_evts > 0.5).sum())} (gate-redirected: {int((gated_evts > 0.5).sum()) })")
  print(f"  Bailouts:       {int((bailout_evt > 0.5).sum())}")
  print(f"  Attack det:     {int((atk_trigger > 0.5).sum())}")
  print(f"  Max tap1 delay: {tap1_del.max():.1f} ms")
  print(f"  Max tap2 delay: {tap2_del.max():.1f} ms")

  # Save output WAV
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

  return out_path, ao, audio_in, P_samples, qualified, selected, tap1_del, tap2_del, gain1_arr, gain2_arr, loop_evts, gated_evts

if __name__ == '__main__':
  pitch_ratio = 0.5
  lpf_fc_hz   = 10000.0
  run_demo(pitch_ratio=pitch_ratio, lpf_fc_hz=lpf_fc_hz)
  print("\n" + "=" * 60 + "\nDemo complete")
