"""
Spooler — wrap a chunk-based pipeline so probe signals accumulate into
linear histories for offline plotting.

Pipeline-agnostic: works with any object exposing
  process_chunk(input_array) -> output_array
  get_buffer(name, n) -> 1-D numpy array of the last n samples

Usage:
  sp = Spooler(pipeline, total_samples=N, probe_names=['hr.P', 'lc.gain1'])
  for i in range(0, N, chunk):
    end = min(i+chunk, N)
    out[i:end] = sp.process_chunk(audio_in[i:end])
  full_P = sp.get_history('hr.P')   # 1-D array of length N
"""
import numpy as np

class Spooler:
  def __init__(s, pipeline, total_samples, probe_names):
    s.pipeline = pipeline
    s.total_samples = total_samples
    s.histories = {name: np.zeros(total_samples, dtype=np.float32) for name in probe_names}
    s.pos = 0

  def process_chunk(s, in_chunk):
    n = len(in_chunk)
    assert s.pos + n <= s.total_samples, \
      f"spooler overflow: pos={s.pos} + n={n} > total={s.total_samples}"
    out = s.pipeline.process_chunk(in_chunk)
    for name, hist in s.histories.items():
      hist[s.pos:s.pos+n] = s.pipeline.get_buffer(name, n)
    s.pos += n
    return out

  def get_history(s, name):
    return s.histories[name][:s.pos]
