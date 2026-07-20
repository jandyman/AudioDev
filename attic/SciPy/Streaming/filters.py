import signal

import numpy as np
from numpy.typing import NDArray
from typing import List
from scipy.signal import tf2sos, butter, sosfilt
from dataclasses import dataclass
from math import sin, cos
import code_gen

class PlatformBiquadChainState:
  pass # to suppport code generation

class BiquadChain:
  c_funcs = ['init', 'proc']

  def __init__(s, num, den):
    s.num = num; s.den = den
    s.get_coefs()
    s.params = BiquadChain.Params(s.n_stages, np.array(s.coefs, dtype='float32'))
    s.state = BiquadChain.State(np.zeros(4*s.n_stages, dtype='float32'))

  def get_coefs(s):
    s.sos = tf2sos(s.num, s.den)
    s.n_stages = s.sos.shape[0]
    s.coefs = []
    for i in range(s.n_stages):
      stage = s.sos[i, :]
      stage = np.delete(stage, 3)
      stage[3:5] = -stage[3:5]  # CMSIS wants Y coefs set up for add
      s.coefs.extend(stage)

  @dataclass
  class Params:
    n_stages: int
    coefs: np.ndarray  # len = nStages * 5

  @dataclass
  class State:
    dlybuf: np.ndarray
    # c_state: PlatformBiquadChainState
    #dlybuf: np.ndarray # len = nStages * 4

    c_lines = '''
        P_BiquadChainState c_state;
    '''

  def proc(s, buffers: List[np.ndarray]):
    buffers[1][:] = sosfilt(s.sos, buffers[0])

  def init(s):
    assert False, "this function is only a dummy to support code generation"


class BiquadChain64(BiquadChain):
  def __init__(s, num, den):
    s.num = num; s.den = den
    s.get_coefs()
    s.params = BiquadChain.Params(s.n_stages, np.array(s.coefs, dtype='float64'))
    s.state = BiquadChain.State(np.zeros(4*s.n_stages, dtype='float64'))

  @dataclass
  class Params:
    n_stages: int
    coefs: NDArray[np.float64]  # len = nStages * 5

  @dataclass
  class State:
    dlybuf: NDArray[np.float64]
    # c_state: PlatformBiquadChainState
    # dlybuf: np.ndarray # len = nStages * 4

    c_lines = '''
          arm_biquad_cascade_df2T_instance_f64 c_state;
      '''

  def proc(s, buffers: List[NDArray[np.float64]]):
    buffers[1][:] = sosfilt(s.sos, buffers[0])


class XCoupledPoles:
  def __init__(s, r: float, theta: float):
    a1 = r * cos(theta)
    a2 = r * sin(theta)
    s.state = XCoupledPoles.State(a1, a2)

  @dataclass
  class State:
    a1: float
    a2: float
    s1: float = 0
    s2: float = 0

  def proc(s, bufs: List[np.ndarray]):
    st = s.state
    x = bufs[0]; y = bufs[1]
    for i in range(bufs[0].size):
      n1 = st.a1 * st.s1 + st.a2 * st.s2 + x[i]
      n3 = st.a1 * st.s2 - st.a2 * st.s1
      y[i] = st.s2
      st.s1 = n1
      st.s2 = n3



def build_c_files():
  gen = code_gen.CppCodeGen()
  gen.write_struct_file('filters')
  gen.write_pybind_file('filters')


if __name__ == '__main__':
  import matplotlib.pyplot as plt
  from block_streaming import pybind_blk
  from EQ.EQ import freq_plot_db, impulse
  plt.ion()

  build_c_files()

  def sing_pair_to_tf(r, theta):
    p1 = complex(r*cos(theta), r*sin(theta))
    p2 = p1.conjugate()
    return np.convolve([1, -p1], [1, -p2])

  #XCoupledPoles
  from math import pi
  from scipy.signal import lfilter
  r = .95
  theta = pi/3
  x_coupled_poles = XCoupledPoles(r, theta)
  imp = np.zeros(5000)
  imp[0] = 1
  o = np.zeros(5000)
  x_coupled_poles.proc([imp, o])
  ir2 = lfilter(1, sing_pair_to_tf(r, theta), imp)
  freq_plot_db(o, 10000, maxDb=30, impulseResponse=True)
  freq_plot_db(ir2, 10000, maxDb=30, impulseResponse=True)
  pass



  biquad_chain = BiquadChain(*butter(4, 1000/(44100/2)))
  c_biquad_chain = pybind_blk(biquad_chain)
  sig = impulse(1000)
  buffers = [sig, np.zeros(sig.size, dtype='float32')]
  c_biquad_chain.proc(buffers)
  plt.figure()
  freq_plot_db(buffers[1], 44100, minDb=-80, impulseResponse=True)
  plt.show()

  biquad_chain = BiquadChain64(*butter(4, 30/(44100/2)))
  c_biquad_chain = pybind_blk(biquad_chain)
  sig = impulse(10000, dtype='float64')
  buffers = [sig, np.zeros(sig.size, dtype='float64')]
  c_biquad_chain.proc(buffers)
  plt.figure()
  freq_plot_db(buffers[1], 44100, minDb=-80, impulseResponse=True)
  plt.show()

  pass




