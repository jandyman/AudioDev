from dataclasses import dataclass, is_dataclass
from typing import List
import numpy as np
from inspect import getfile
import os
import importlib
import sys
from scipy.io import wavfile as wf

def read_wav_data(filename):
  rate, data = wf.read(filename)
  flData = data.astype(float)
  return rate, flData / 2**15

def write_wav_data(data, filename, rate=44100):
  wf.write(filename, rate, data)

def xfer_struct_to_pybind(src, dst, module):
  assert is_dataclass(src), "src must be a data class"
  for name, d_type in src.__dataclass_fields__.items():
    item = getattr(src, name)
    if hasattr(item, 'c_funcs'):
      item = pybind_blk(item, module=module)
    setattr(dst, name, item)

def get_module_name(cls):
  path = getfile(cls)
  return os.path.splitext(os.path.basename(path))[0]

def get_pybind_module(module_name: str):
  pybind_module_name = f'pybind.pybind_{module_name}'
  if pybind_module_name not in sys.modules:
    return importlib.import_module(f'{pybind_module_name}')
  else: return sys.modules[pybind_module_name]

def pybind_blk(py_blk, xfer_state = True, module=None):
  cls = py_blk.__class__
  if not module:
    module_name = get_module_name(cls)
    module = get_pybind_module(module_name)
  c_cls = getattr(module, cls.__name__)
  c_blk = c_cls()
  if hasattr(py_blk, "params"):
    xfer_struct_to_pybind(py_blk.params, c_blk.params, module)
  if xfer_state and hasattr(py_blk, 'state'):
    xfer_struct_to_pybind(py_blk.state, c_blk.state, module)
  if hasattr(c_blk, 'init'): c_blk.init()
  return c_blk

def spool_proc(block, inputs: List[np.ndarray], n_outputs = 1, bufsiz = 512):
  n_inputs = len(inputs)
  input_len = len(inputs[0])
  rd_idx = 0
  assert all([len(x) == input_len for x in inputs]), "all inputs must be the same length"
  outputs = [np.zeros(0) for _ in range(n_outputs)]
  while rd_idx < input_len:
    samps_left = input_len - rd_idx
    n_samps = min(samps_left, bufsiz)
    bufs = []
    for input in inputs:
      bufs.append(np.array(input[rd_idx:rd_idx+n_samps], dtype='float32'))
    bufs += [np.zeros(n_samps, dtype='float32') for _ in range(n_outputs)]
    block.proc(bufs)
    outputs = [np.append(outputs[i], bufs[n_inputs+i]) for i in range(n_outputs)]
    rd_idx += n_samps
  return outputs





