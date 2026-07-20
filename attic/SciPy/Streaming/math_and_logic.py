import numpy as np
from numpy.typing import ArrayLike
from enum import Enum
from dataclasses import dataclass
from typing import List
import code_gen

class Square:
  c_funcs = ['proc']
  def proc(s, buffers: List[np.ndarray]):
    buffers[1][:]= buffers[0] * buffers[0]

class Sqrt:
  c_funcs = ['proc']
  def proc(s, buffers: List[np.ndarray]):
    buffers[1][:] = np.sqrt([buffers[0]])

class Log:
  c_funcs = ['proc']
  def proc(s, buffers: List[np.ndarray]):
    buffers[1][:] = np.log([buffers[0]])

class Exp:
  c_funcs = ['proc']
  def proc(s, buffers: List[np.ndarray]):
    buffers[1][:] = np.exp([buffers[0]])

class Abs:
  c_funcs = ['proc']
  def proc(s, buffers: List[np.ndarray]):
    buffers[1][:] = np.abs([buffers[0]])

class Sub:
  c_funcs = ['proc']
  def proc(s, buffers: List[np.ndarray]):
    buffers[2][:] = buffers[0] - buffers[1]

class Add:
  c_funcs = ['proc']
  def proc(s, buffers: List[np.ndarray]):
    buffers[2][:] = buffers[0] + buffers[1]

class Mult:
  c_funcs = ['proc']
  def proc(s, buffers: List[np.ndarray]):
    buffers[2][:] = buffers[0] * buffers[1]

class Comparator:
  c_funcs = ['proc']
  def proc(s, bufs: List[np.ndarray]):
    t = bufs[0] > bufs[1]
    bufs[2][:] = t.astype(int)

class SetResetFlop:
  def __init__(s):
    s._output = False

  def proc(s, set: np.ndarray, reset: np.ndarray) -> np.ndarray:
    size = set.size
    assert size == reset.size
    result = np.zeros(size)
    for i in range(size):
      if reset[i] != 0:  s._output = False
      if set[i] != 0:    s._output = True
      result[i] = s._output
    return result


class EdgeDetector:
  c_funcs = ['proc']

  class Mode(Enum):
    Rising = 1
    Either = 0
    Falling = -1

  @dataclass
  class State:
    prev_samp: float

  @dataclass
  class Params:
    thresh: float
    mode: int

  def __init__(s, thresh, mode:Mode = Mode.Rising):
    s.state = EdgeDetector.State(0)
    s.params = EdgeDetector.Params(0, mode.value)

  def proc(s, bufs: List[np.ndarray]):
    (insig, out) = (bufs[0], bufs[1])
    p = s.params
    st = s.state
    match s.mode:
      case EdgeDetector.Mode.Rising:
        f = lambda x: x > p.thresh and st.prev_samp <= p.thresh
      case EdgeDetector.Mode.Falling:
        f = lambda x: x < p.thresh and st.prev_samp >= p.thresh
      case EdgeDetector.Mode.Either:
        f = lambda x: x > p.thresh != st.prev_samp > p.thresh
    for i in range(insig.size):
      cond = f(insig[i])
      out[i] = insig[i] - st.prev_samp if cond else 0
      st.prev_samp = insig[i]


def build_c_files():
  gen = code_gen.CppCodeGen()
  gen.write_struct_file('math_and_logic')
  gen.write_pybind_file('math_and_logic')


@dataclass
class ZeroCrossing:
  samp_cnt: int
  delta: float  # between present value and previous value

class ZeroCrossingDetector:
  def __init__(s):
    s.samp_cnt = 0
    s.prev_samp = 0
    s.total_crossings = []
    s.buf_crossings = []

  def proc(s, insig: np.ndarray):
    s.buf_crossings = []
    for i in range(insig.size):
      if insig[i] > 0 != s.prev_samp:
        delta = insig[i] - s.prev_samp
        crossing = ZeroCrossing(samp_cnt=s.n_delaybuf.samp_cnt + i,
                                delta=delta)
        s.total_crossings.append(crossing)
        s.buf_crossings.append(crossing)

if __name__ == '__main__':
  from block_streaming import pybind_blk
  import matplotlib.pyplot as plt
  build_c_files()

  py_square = Square()
  c_square = pybind_blk(py_square)

  py_log = Log()
  c_log = pybind_blk(py_log)
  log_in = np.linspace(1,10, 10, dtype='float32')
  log_out = np.zeros(len(log_in), dtype='float32')
  c_log_out = np.zeros(len(log_in), dtype='float32')
  py_log.proc([log_in, log_out])
  c_log.proc([log_in, c_log_out])

  sig = np.linspace(0,1, 200, dtype='float32')
  out1 = np.zeros(len(sig), dtype='float32')
  out2 = np.zeros(len(sig), dtype='float32')
  py_square.proc([sig, out1])
  plt.plot(out1)
  c_square.proc([sig, out2])
  plt.plot(out2)
  print(f'max diff for square is {max(out1-out2)}')
  plt.show()

  pass


