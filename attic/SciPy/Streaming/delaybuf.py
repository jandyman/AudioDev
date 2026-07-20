import numpy as np
from dataclasses import dataclass
from typing import List

class DelayBuf:
  c_funcs = ['push', 'get_values']

  @dataclass
  class State:
    data: np.ndarray
    wr_idx: int = 0

  def __init__(s, size: int):
    data = np.zeros(size)
    s.state = DelayBuf.State(data)

  def push(s, samples: np.ndarray):
    st = s.state
    siz = st.data.size
    for sample in samples:
      st.data[st.wr_idx] = sample
      st.wr_idx += 1
      if st.wr_idx >= siz: st.wr_idx -= siz

  def get_values(s, delay: int, output: np.ndarray):
    cnt = output.size
    assert delay >= cnt, "delay must be >= cnt"
    st = s.state
    d_siz = st.data.size
    rd_idx = st.wr_idx - delay
    if rd_idx < 0: rd_idx += d_siz
    to_end_cnt = d_siz - rd_idx
    if cnt <= to_end_cnt:
      output[0:cnt] = st.data[rd_idx:rd_idx+cnt]
    else:
      output[0:to_end_cnt] = st.data[rd_idx:d_siz]
      output[d_siz-rd_idx:cnt] = st.data[0:cnt-to_end_cnt]

  def get_value(s, idx: int) -> float:
    st = s.state
    siz = st.data.size
    d_idx = siz - idx - 1 + st.wr_idx
    d_idx %= siz
    return st.data[d_idx]


class Delays:
  def __init__(s, capacity: int, taps: List[int]):
    s.delay_buf = DelayBuf(capacity)
    s.taps = taps

  def proc(s, bufs):
    assert len(bufs) == len(s.taps) + 1
    s.delay_buf.push(bufs[0])
    for i,tap in enumerate(s.taps):
      s.delay_buf.get_values(tap+bufs[0].size, bufs[i+1])





def build_c_files():
  import code_gen
  gen = code_gen.CppCodeGen()
  gen.write_struct_file('delaybuf')
  gen.write_pybind_file('delaybuf')
  # call out to make and stubgen here


if __name__ == '__main__':
  t = DelayBuf(3)
  t.push([0, 1, 2, 3, 4])
  assert t.get_value(0) == 4
  assert t.get_value(2) == 2

  build_c_files()

  import pybind.pybind_delaybuf as tst
  state = tst.DelayBufState()
  state.data = np.zeros(12)
  blk = tst.DelayBuf()
  blk.state = state
  blk.push(np.zeros(4, dtype='float32'))
  blk.push(np.array([1,2,3,4,5,6,7,8], dtype='float32'))
  output = np.zeros(10, dtype='float32')
  blk.get_values(8, output)
  pass
