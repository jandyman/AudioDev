from math import ceil, pi
from numpy import linspace
import numpy as np
from scipy.special import sinc
from scipy.signal.windows import kaiser
from EQ.EQ import freq_plot_db
from Streaming.delaybuf import DelayBuf
from dataclasses import dataclass, is_dataclass
from typing import List

c_dependencies = ['delaybuf']

def windowed_sinc_set(freq: float, len: int, beta = 14, oversamp: int = 1):
  freq = freq / 2  # change domain from 2pi to pi
  n_pts = len * oversamp + 1  # TODO - handle case of no oversampling
  r = linspace(-ceil(len/2), ceil(len/2), n_pts)
  s = 2 * freq * sinc(2 * freq * r)
  w = kaiser(n_pts, beta)
  h = s * w
  h *= h.size / (oversamp * sum(h))  # normalize
  results = []
  for i in range(0, oversamp):
    h_i = h[np.arange(i, h.size-1, oversamp)]
    h_i = np.flip(h_i)
    results.append(h_i)
  return results

class JosFractDelay:
  c_funcs = ['fixed_delay']

  @dataclass
  class Params:
    buffer: np.ndarray
    h_coef_set: List[np.ndarray]
    oversamp_bits: int
    allow_overflow: bool

  def __init__(s, Fc, length, oversamp_bits, beta = 10):
    coef_set = windowed_sinc_set(Fc, length, beta, 2 ** oversamp_bits)
    s.params = JosFractDelay.Params(np.zeros(length), coef_set, oversamp_bits, True)

  # delay must be greater than one half the filter length
  def fixed_delay(s, delaybuf: DelayBuf, delay: float) -> float:
    p = s.params
    if delay >= delaybuf.state.data.size:
      if p.allow_overflow: return 0
      else: raise Exception("delaybuf not large enough for delay")
    samps_delay = ceil(delay)
    h_offset = int((samps_delay-delay) * (2**p.oversamp_bits))
    h = p.h_coef_set[h_offset]
    delaybuf.get_values(samps_delay, p.buffer)
    result = sum(p.buffer * h)
    return result


class Resampler:
  c_funcs = ['proc']

  def __init__(s, resampler: JosFractDelay, dly_len:int):
    s.state = Resampler.State(resampler, DelayBuf(dly_len))

  @dataclass()
  class State:
    frac_dly : JosFractDelay
    dly_buf : DelayBuf

  def proc(s, bufs: List[np.ndarray]):
    st = s.state
    n_bufs = len(bufs)
    assert n_bufs % 2 != 0, "number of buffers must be odd"
    n_outs = int((n_bufs-1) / 2)
    bufsiz = bufs[0].size
    assert all(i.size == bufsiz for i in bufs)
    st.dly_buf.push(bufs[0])
    for j in range(1,n_outs+1):
      out_buf_idx = j + n_outs
      for i in range(bufsiz):
        bufs[out_buf_idx][i] = st.frac_dly.fixed_delay(st.dly_buf, bufsiz - i + bufs[j][i])


class LoopFinder:
  def __init__(s, s_incr: float, delaybuf: DelayBuf):
    s.delaybuf = delaybuf
    s.sampcnt = 0
    s.zerocrossings = []
    s.slope_x_dst = 50
    s.s_incr = s_incr
    s.prev_samp = 0

  def proc(s, bufs: List[np.ndarray]):
    insig = bufs[0]
    # first find any zero crossings
    for i in range(insig.size):
      if insig[i] > 0 and s.prev_samp <= 0:
        s.zerocrossings.append(s.sampcnt+i)
        bufs[1][i] = 1
      else: bufs[1][i] = 0






def build_c_files():
  import code_gen
  gen = code_gen.CppCodeGen()
  gen.write_struct_file('resample')
  gen.write_pybind_file('resample')


if __name__ == '__main__':
  import numpy as np
  from block_streaming import pybind_blk, get_pybind_module, spool_proc
  from matplotlib.pyplot import plot
  import matplotlib.pyplot as plt
  import matplotlib
  matplotlib.use(backend="MacOSX")
  plt.ion()
  build_c_files()

  from scipy.io.wavfile import write
  def write_wav(sig, fn):
    rate = 44100
    data = np.random.uniform(-1, 1, rate)  # 1 second worth of random samples between -1 and 1
    scaled = np.int16(sig / np.max(np.abs(data)) * 32700)
    write(f'{fn}.wav', rate, scaled)

  Fs = 44100
  Fc = 10000
  filt_length = 16
  oversamp_bits = 2
  bufsiz = 1000

  fract_delay = JosFractDelay(Fc / (Fs / 2), filt_length, oversamp_bits)
  plt.figure()
  hs = fract_delay.params.h_coef_set
  for h in hs:
    plot(h)
  plt.figure()
  freq_plot_db([h, 1], 44100, minDb=-120)
  plt.grid(True)

  sig = np.sin(np.arange(0, 22050, dtype='float32') * 400 * 2 * pi / 44100)
  delay_buf = DelayBuf(25000)
  module = get_pybind_module('resample')
  c_fract_delay = pybind_blk(fract_delay, module=module)
  c_delaybuf = pybind_blk(delay_buf, module=module)

  def test_resample(delay_buf, fract_delay):
    delay_buf.push(sig)
    dlys = np.zeros(sig.size, dtype='float32')
    dly = filt_length
    dly_increment = 1 - 2**(-5/12)
    for i in range(sig.size):
      dlys[i] = dly
      dly += dly_increment
    output = np.zeros(25000, dtype='float32')
    for i, dly in enumerate(dlys):
      output[i] = fract_delay.fixed_delay(delay_buf, dly)
    return output

  py_out = test_resample(delay_buf, fract_delay)
  write_wav(sig, 'sig')
  write_wav(py_out/4.1, 'out_py')
  c_out = test_resample(c_delaybuf, c_fract_delay)
  write_wav(c_out/4.1, 'out_c')

  resampler = Resampler(fract_delay, 25000)
  c_resampler = pybind_blk(resampler)
  dlys = np.array([filt_length + (1-2**(-5/12)) * i for i in range(sig.size)], dtype='float32')
  outputs = spool_proc(resampler, [sig, dlys], 1)
  c_outputs = spool_proc(c_resampler, [sig, dlys], 1, bufsiz=12000)

  from OctaveDiv.Misc import read_wav_data
  rate, data = read_wav_data("../OctaveDiv/wav/Bass Notes No Gap.wav")
  dly_buf = DelayBuf(len(data))
  loop_finder = LoopFinder(10, dly_buf)
  loop_finder.out = np.zeros(len(data))
  loop_finder.proc([data, loop_finder.out])


  pass


