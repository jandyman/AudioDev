from __future__ import annotations
from dataclasses import dataclass, is_dataclass
from typing import List
import numpy as np
from inspect import getfile
import os
import importlib
import sys
from scipy.io import wavfile as wf
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class SignalSpec:
  block_size: int
  sample_rate: int
  n_channels: int

@dataclass
class Port:
  block: Block
  sig_idx: int

  # For now, we just support a single SampleSpec, will add more later
  def get_signal_spec(s):
    top_level = s.block.parent.get_top_level()
    assert hasattr(s.block, "signal_spec"), "top level graph has no SignalSpec"

@dataclass
class InPort(Port):
  src: Port

@dataclass
class OutPort(Port):
  dsts: List[InPort]

  def replace_dst(s, old_dst: InPort, new_dst: InPort):
    dsts = [x for x in s.dsts if x != old_dst]
    dsts.append(new_dst)
    s.dsts = dsts
  
@dataclass 
class GraphPort(InPort, OutPort):
  pass

# Will only return a GraphPort if the corresponding graph is top level
def find_src(port: InPort) -> OutPort:
  assert port.__class__ != OutPort, "can't find src for an output port"
  src = port.src
  if src is None:
    # check for input to top level graph
    if isinstance(port, GraphPort) and port.block.parent == None: return port
    else: return None
  if isinstance(src, GraphPort): return find_src(src)
  elif isinstance(src, OutPort): return src
  else: raise TypeError('unexpected src type')

def find_dsts(port: OutPort) -> List[InPort]:
  assert not isinstance(port, InPort), "can't find dst for an input port"
  dsts = []
  for dst in port.dsts:
    if isinstance(dst, InPort): dsts.append(dst)
    elif isinstance(dst, GraphPort): dsts += find_dsts(dst)
    else: raise TypeError('unexpected src type')
  return dsts


class Block(ABC):
  instance_count = 0
  input_names = ["input"]
  output_names = ["output"]

  def __init__(s, name = None):
    cls = s.__class__
    s.in_ports = [InPort(s,i,None) for i in range(len(cls.input_names))]
    s.out_ports = [OutPort(s,i,[],[]) for i in range(len(cls.output_names))]
    s.name = name if name else f'{cls.__name__}_{cls.instance_count}'
    cls.instance_count += 1

  @abstractmethod
  def proc(s, inputs: List[np.ndarray], outputs: List[np.ndarray]):
    pass


class Graph(Block):
  def __init__(s, name = None):
    Block.__init__(s, name)
    cls = s.__class__
    s.parent = None
    s.in_ports = [GraphPort(s, i, [], [], None) for i in range(len(cls.input_names))]
    s.out_ports = [GraphPort(s, i, [], [], None) for i in range(len(cls.output_names))]
    s.proc_order = []
    s.blocks = []

  def proc(s, inputs: List[np.ndarray], outputs: List[np.ndarray]):
    pass

  def add_block(s, block: Block):
    s.blocks.append(block)
    block.parent = s
    
  def connect_input(s, block: Block, graph_idx: int=0, block_idx: int=0):
    src = s.in_ports[graph_idx]
    dst = block.in_ports[block_idx]
    src.dsts.append(dst)
    dst.src = src

  def connect_output(s, block: Block, graph_idx: int=0, block_idx: int=0):
    dst = block.out_ports[block_idx]
    src = s.out_ports[graph_idx]
    src.dsts.append(dst)
    dst.src = src

  def get_top_level(s):
    return s if s.parent is None else s.parent.get_top_level(s.parent)

  def collect_subgraph_blocks(s) -> List[Block]:
    blocks = []
    for block in s.blocks:
      if isinstance(block, Graph):
        blocks += block.collect_subgraph_blocks()
      else:
        blocks.append(block)
    return blocks

  def determine_proc_order(s):
    s.proc_order = []
    iter = 0
    blocks = s.collect_subgraph_blocks()
    while True:
      iter += 1
      found_blk_this_pass = False
      for blk in blocks:
        if s.has_been_processed(blk): continue
        if s.can_be_processed(blk):
          s.proc_order.append(blk)
          found_blk_this_pass = True
          break
      if not found_blk_this_pass: break
    # check that all blocks have been processed
    assert all(s.has_been_processed for blk in blocks)

  def has_been_processed(s, blk: Block):
    return blk in s.proc_order

  def can_be_processed(s, blk: Block):
    in_ports = blk.in_ports
    if len(in_ports) == 0: return True  # it's a source block
    in_srcs = [find_src(port) for port in in_ports]
    # exclude input to top level graph
    cond = lambda src: not (isinstance(src, GraphPort) and s.parent == None)
    input_blks = [src.block for src in in_srcs if cond(src)]
    return not any(blk not in s.proc_order for blk in input_blks)

  # Because we want to maintain hierarchy, we don't want to descructively modify connections.
  # Therefore, we store and reference buffers in a different way
  def allocate_and_connect_blocks(s):
    assert s.parent == None, "can't allocate and connect blocks for a subgraph"
    blocks = s.collect_subgraph_blocks()
    # Allocate buffers for the output ports
    for blk in blocks:
      out_bufs = {}
      for out_port in blk.out_ports:
        sigspec = out_port.get_signal_spec()
        out_bufs[out_port] = np.array([sigspec.n_channels, sigspec.block_size])
      blk.out_buffers = out_bufs
    # Buffers for input ports
    for port in s.in_ports:
      sigspec = port.get_signal_spec()
      s.in_bufs = {}
      s.in_bufs[port] = np.array([sigspec.n_channels, sigspec.block_size])
    # Now create references for the input ports
    for blk in blocks:
      in_bufs = {}
      for in_port in blk.in_ports:
        src = find_src(in_port)
        out_bufs = src.out_buffers
        if not isinstance(src, GraphPort):
          in_bufs[src] = out_bufs[src]
      blk.in_buffers = in_bufs
    # Now connect the ports of the top level graph
    for port in s.out_ports:
      s.out_bufs = {}
      src = find_src(port)
      assert not isinstance(src, GraphPort), "output port of graph points to input port"
      s.out_bufs[port] = s.out_bufs[src]

  def run_graph(s):
    assert s.parent is None, "can only run a top level graph"
    for blk in s.proc_order:
      in_bufs = [blk.in_buffers[p] for p in blk.in_ports]
      out_bufs = [blk.out_buffers[p] for p in blk.out_ports]
      blk.proc(in_bufs, out_bufs)


def connect(src: Block, dst: Block, src_idx: int=0, dst_idx: int=0):
  src_port = src.out_ports[src_idx]
  dst_port = dst.in_ports[dst_idx]
  src_port.dsts.append(dst_port)
  dst_port.src = src_port

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



class TestBlk_1_1(Block):
  def __init__(s, gain, name = None):
    super().__init__(name)
    s.gain = gain

  def proc(s, inputs: List[np.ndarray], outputs: List[np.ndarray]):
    pass

class TestBlk_1_2(Block):
  input_names = ["input"]
  output_names = ["output1", "output2"]

  def proc(s, inputs: List[np.ndarray], outputs: List[np.ndarray]):
    pass

  def __init__(s, gain, name = None):
    super().__init__(name)
    s.gain = gain

  def proc(s, inputs: List[np.ndarray], outputs: List[np.ndarray]):
    pass

  class TestBlk_2_1(Block):
    input_names = ["input1", "input2"]
    output_names = ["output1"]

    def __init__(s, gain, name=None):
      super().__init__(name)
      s.gain = gain

    def proc(s, inputs: List[np.ndarray], outputs: List[np.ndarray]):
      pass




if __name__ == '__main__':
  outer_graph = Graph('outer')
  inner_graph = Graph('inner')
  t11_1 = TestBlk_1_1(1)
  outer_graph.add_block(t11_1)
  t11_2 = TestBlk_1_1(2)
  inner_graph.add_block(t11_2)
  inner_graph.connect_input(t11_2)
  inner_graph.connect_output(t11_2)
  outer_graph.add_block(inner_graph)
  outer_graph.connect_input(t11_1)
  connect(t11_1,inner_graph)
  outer_graph.signal_spec = SignalSpec(block_size=2000,
                                       sample_rate=44100,
                                       n_channels=1)
  outer_graph.determine_proc_order()
  pass





