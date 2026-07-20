import numpy as np
from numpy.typing import ArrayLike
from matplotlib.pyplot import plot


# for blocks with a single sample rate
def check_signals(inputs:[np.ndarray], outputs:[np.ndarray],
                  n_inputs:int=1, n_outputs:int=1, bufsize=None):
  siz = inputs[0].size
  assert len(inputs) == n_inputs
  assert len(outputs) == n_outputs
  assert all(x.size == siz for x in inputs+outputs)
  if bufsize != None: assert siz == bufsize

def create_buffers(siz:int, n_buffers:int=1):
  return [np.zeros(siz) for _ in range(n_buffers)]

# if there is a trailing partial buffer, it is ignored
def test_streaming(action, stream: ArrayLike, bufsize: int) -> ArrayLike:
  sig_size = stream.size
  bufcnt = sig_size // bufsize
  result = np.zeros(bufcnt * bufsize)
  for i in range(0, sig_size, bufsize):
    sig = stream[i:i+bufsize]
    buf_result = action(sig)
    result[i:i+bufsize] = buf_result
  return result

def test_streaming_x_1(action, inputs:[np.ndarray],
                       bufsize:int, expand_args = True) -> np.ndarray:
  sig_size = inputs[0].size
  assert all(x.size == sig_size for x in inputs), "Input array sizes do not match"
  bufcnt = sig_size // bufsize
  result = np.zeros(bufcnt * bufsize)
  for i in range(0, sig_size, bufsize):
    data = []
    for sig in inputs:  data.append(sig[i:i+bufsize])
    if expand_args: buf_result = action(*data)
    else: buf_result = action(data)
    result[i:i+bufsize] = buf_result
  return result

# New Protocol, list of input signals and list of output signals
def test_streaming_np(action, inputs:[np.ndarray], n_outs:int, bufsize:int) -> np.ndarray:
  sig_size = inputs[0].size
  assert all(x.size == sig_size for x in inputs), "Input array sizes do not match"
  result = [np.zeros(sig_size) for _ in range(n_outs)]
  for i in range(0, sig_size, bufsize):
    data = []
    t_bufsiz = min(bufsize, sig_size-i)
    for sig in inputs: data.append(sig[i:i+t_bufsiz])
    print(f't buf size is {t_bufsiz}')
    buf_result = action(data)
    assert len(buf_result) == n_outs
    for j,r in enumerate(buf_result):
      result[j][i:i+t_bufsiz] = r
  return

# Even Newer Protocol, outputs are passed in
def test_streaming_nnp(action, inputs:[np.ndarray], outputs:[np.ndarray], bufsize:int):
  sig_size = inputs[0].size
  n_outs = len(outputs)
  assert all(x.size == sig_size for x in inputs+outputs), "Input or Output array sizes do not match"
  for i in range(0, sig_size, bufsize):
    t_bufsiz = min(bufsize, sig_size-i)
    t_inputs = []; buf_results = []
    for sig in inputs:
      x = sig[i:i+t_bufsiz]
      if x.size < bufsize:
        x = np.pad(x, (0, bufsize-x.size))
      t_inputs.append(x)
    for _ in outputs:  buf_results.append(np.zeros(bufsize))
    print(f't buf size is {t_bufsiz}')
    action(t_inputs, buf_results)
    assert len(buf_results) == n_outs
    for j,r in enumerate(buf_results):
      outputs[j][i:i+t_bufsiz] = r[0:t_bufsiz]

