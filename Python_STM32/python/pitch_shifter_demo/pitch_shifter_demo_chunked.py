"""
Chunked-operation verification.

Runs the generated PitchShifter twice on the same audio:
  1) file-sized — one process_chunk call covers the whole file
  2) chunked   — many process_chunk calls of small batches, via Spooler

If the two runs produce byte-identical audio output AND every spooled probe
matches the corresponding file-sized probe sample-for-sample, every block
preserves state correctly across chunk boundaries.
"""
import sys
import os
import numpy as np
import scipy.io.wavfile as wav

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build'))

from build.pybind_pitch_shifter import PitchShifter
from lib.spooler import Spooler

PROBES = [
  'zc.zc_out', 'atk.trigger',
  'hr.P', 'hr.qualified', 'hr.selected_filter',
  'lc.tap1_delay_ms', 'lc.tap2_delay_ms',
  'lc.gain1', 'lc.gain2',
  'lc.loop_event', 'lc.bailout_event', 'lc.gated_event',
]

def load_audio():
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
  return sample_rate, audio_raw.astype(np.float32)

def init_pipeline(ps, sample_rate, pitch_ratio, lpf_fc_hz):
  ps.init(sample_rate)
  ps.set_param('lpf.fc', lpf_fc_hz)
  ps.set_param('lc.pitch_ratio', pitch_ratio)

def run_file_sized(ps, audio_in):
  N = len(audio_in)
  out = ps.process_chunk(audio_in)
  probes = {name: np.array(ps.get_buffer(name, N), copy=True) for name in PROBES}
  return out, probes

def run_chunked(ps, audio_in, chunk):
  N = len(audio_in)
  sp = Spooler(ps, total_samples=N, probe_names=PROBES)
  out = np.zeros(N, dtype=np.float32)
  for i in range(0, N, chunk):
    end = min(i + chunk, N)
    out[i:end] = sp.process_chunk(audio_in[i:end])
  probes = {name: sp.get_history(name) for name in PROBES}
  return out, probes

def main(pitch_ratio=0.5, lpf_fc_hz=10000.0, chunk=512):
  print("Chunked-operation verification")
  print("=" * 60)
  print(f"Pitch ratio: {pitch_ratio}, LPF fc: {lpf_fc_hz:.0f} Hz, chunk: {chunk}")

  sample_rate, audio_in = load_audio()
  N = len(audio_in)
  print(f"Audio: {N} samples @ {sample_rate} Hz ({N/sample_rate:.2f} s)\n")

  ps = PitchShifter()
  if N > PitchShifter.CHUNK_SIZE:
    raise RuntimeError(f"file size {N} > CHUNK_SIZE {PitchShifter.CHUNK_SIZE}")

  # Run 1: file-sized
  init_pipeline(ps, sample_rate, pitch_ratio, lpf_fc_hz)
  out_file, probes_file = run_file_sized(ps, audio_in)
  print(f"File-sized run: 1 call, {N} samples")

  # Run 2: chunked (re-init resets all state)
  init_pipeline(ps, sample_rate, pitch_ratio, lpf_fc_hz)
  num_chunks = (N + chunk - 1) // chunk
  out_chunked, probes_chunked = run_chunked(ps, audio_in, chunk)
  print(f"Chunked run:    {num_chunks} calls @ {chunk} samples")

  # Compare audio output
  out_diff = np.abs(out_file.astype(np.float64) - out_chunked.astype(np.float64))
  print(f"\nAudio output:")
  print(f"  max abs diff:       {out_diff.max():.6e}")
  print(f"  samples that differ: {int((out_diff > 0).sum())}/{N}")
  print(f"  -> {'IDENTICAL' if out_diff.max() == 0 else 'DIFFER'}")

  # Compare each probe
  print(f"\nProbe signal comparisons:")
  any_diff = False
  for name in PROBES:
    a = probes_file[name].astype(np.float64)
    b = probes_chunked[name].astype(np.float64)
    d = np.abs(a - b)
    differing = int((d > 0).sum())
    if differing:
      any_diff = True
      print(f"  {name:24s}  max diff {d.max():.6e}  differ {differing}/{N}  DIFFER")
    else:
      print(f"  {name:24s}  IDENTICAL")

  print(f"\n{'='*60}")
  if out_diff.max() == 0 and not any_diff:
    print("PASS — chunked operation produces byte-identical output and probes.")
  else:
    print("FAIL — chunked operation diverges from file-sized.")

if __name__ == '__main__':
  pitch_ratio = 0.5
  lpf_fc_hz   = 10000.0
  chunk_size  = 512
  main(pitch_ratio=pitch_ratio, lpf_fc_hz=lpf_fc_hz, chunk=chunk_size)
