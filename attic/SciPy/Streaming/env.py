import importlib

from block_streaming import read_wav_data, pybind_blk
from filters import BiquadChain64
import numpy as np
from numpy.typing import ArrayLike
from scipy.signal import convolve, butter
from scipy.signal.windows import hann

from dataclasses import dataclass
from typing import List
import code_gen
from math_and_logic import Square, Sqrt

def rms_hann(data: ArrayLike, window_len: int) -> np.ndarray:
  ir = hann(window_len)
  ir = ir / np.sum(ir)
  sq = data * data
  filtered = convolve(sq, ir, mode="same")
  return filtered ** .5

def att_rel_coef(Tc, Fs):
  return 1 - np.exp(-1 / (Fs * Tc))

class AttRel:
  c_funcs = ['init', 'proc']
  def __init__(s, fs, attTime = .004, relTime = .03):
    s.params = AttRel.Params(fs, attTime, relTime)
    s.state = AttRel.State()
    s.init()

  def init(s):
    fs = s.params.fs
    s.params.attCoef = att_rel_coef(s.params.attTime, fs)
    s.params.relCoef = att_rel_coef(s.params.relTime, fs)

  @dataclass
  class Params:
    fs: float
    attTime: float
    relTime: float
    attCoef: float = 0
    relCoef: float = 0

  @dataclass
  class State:
    lastout: float = 0

  def proc(s, buffers: List[np.ndarray]):
    st = s.State
    p = s.params
    out_buf = buffers[1]
    in_buf = buffers[0]
    for idx, samp in enumerate(in_buf):
      lastout = st.lastout
      if samp > lastout:
        st.lastout = p.attCoef * (samp - lastout) + lastout
      else:
        st.lastout = p.relCoef * (samp - lastout) + lastout
      out_buf[idx] = st.lastout


class FollowPeaks():
  c_funcs = ['init', 'proc']
  def __init__(s, attTime=.001, fs=44100):
    attCoef = att_rel_coef(attTime, fs)
    div = 1500000
    s.params = FollowPeaks.Params(attCoef, div)
    s.init()

  @dataclass
  class Params:
    attCoef: float
    div: float

  @dataclass
  class State:
    lastpeak: float
    lastout: float
    sampSincePeak: float

  def init(s):
    s.state = FollowPeaks.State(0,0,0)

  def proc(s, buffers: List[np.ndarray]):
    outbuf = buffers[1]
    inbuf = buffers[0]
    st = s.state; p = s.params
    for idx, samp in enumerate(inbuf):
      if samp > st.lastout:
        st.lastout = p.attCoef * (samp - st.lastout) + st.lastout
        st.lastpeak = st.lastout
        st.sampSincePeak = 0
        outbuf[idx] = st.lastout
      else:
        incr = st.lastpeak * st.sampSincePeak / p.div
        st.lastout = st.lastout - incr
        if st.lastout < 0:
          st.lastout = 0
        st.sampSincePeak += 1
        outbuf[idx] = st.lastout


# this isn't transferrable to C++, the block will be a biquad in C++
class ButterRms:
  def __init__(s, fc: float, fs: float):
    num, den = butter(4, fc / (fs / 2))
    s.biquad_chain = pybind_blk(BiquadChain64(num, den))
    s.sqrt = pybind_blk(Sqrt())
    s.square = pybind_blk(Square())

  def proc(s, bufs: List[np.ndarray]):
    s.square.proc(bufs)
    bq_in = bufs[1].astype('float64')
    bq_out = np.zeros(bufs[1].size, dtype='float64')
    s.biquad_chain.proc([bq_in, bq_out])
    bufs[0] = bq_out.astype('float32')
    s.sqrt.proc(bufs)


def build_c_files():
  gen = code_gen.CppCodeGen()
  gen.write_struct_file('env')
  gen.write_pybind_file('env')


if __name__ == '__main__':
  build_c_files()
  import matplotlib.pyplot as plt
  #matplotlib.use(backend="MacOSX")
  plt.ion()

  rate, data = read_wav_data("../OctaveDiv/wav/Bass Notes No Gap.wav")
  inbuf = data.astype(np.float32)

  # create a butterworth RMS composite block
  from filters import BiquadChain
  from math_and_logic import Square, Sqrt
  from block_streaming import pybind_blk
  fc = 20
  num, den = butter(4, fc / (rate / 2))
  square = Square()
  square_out = np.zeros(len(data), dtype='float32')
  filter = pybind_blk(BiquadChain(num, den))
  filt_out = np.zeros(len(data), dtype='float32')
  sqrt = Sqrt()
  sqrt_out = np.zeros(len(data), dtype='float32')
  square.proc([inbuf, square_out])
  filter.proc([square_out, filt_out])
  sqrt.proc([filt_out, sqrt_out])
  plt.plot(sqrt_out*2.75)
  plt.show()

  # create an AttRel RMS composite block
  square = Square()
  square_out = np.zeros(len(data), dtype='float32')
  att_rel = AttRel(rate, attTime=.0005, relTime=.3)
  att_rel_out = np.zeros(len(data), dtype='float32')
  sqrt = Sqrt()
  sqrt_out = np.zeros(len(data), dtype='float32')
  square.proc([inbuf, square_out])
  att_rel.proc([square_out, att_rel_out])
  sqrt.proc([att_rel_out, sqrt_out])
  plt.plot(sqrt_out)
  plt.show()


  follow_peaks_out = np.zeros(len(data), dtype='float32')
  py_follow_peaks = FollowPeaks(100, .001)
  c_follow_peaks = pybind_blk(py_follow_peaks)
  buffers = [inbuf, follow_peaks_out]
  c_follow_peaks.proc(buffers)

  py_att_rel = AttRel(rate, attTime=.0005, relTime=.4)
  buffers = [follow_peaks_out, att_rel_out]

  pass

  from streaming import test_streaming
  # s = data[0:70000]
  # follow_peaks = FollowPeaks(100, .001)
  # att_rel = AttRel(attTime=.004, relTime=.03, Fs=rate)
  # y = np.clip(y, 1e-06, None) # prevent divide by zero
  # r = p/y







