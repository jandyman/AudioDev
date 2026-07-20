from copy import copy
import numpy as np
import math
from OctaveDiv.Misc import read_wav_data
from dataclasses import dataclass
import matplotlib.pyplot as plt
from code_gen import CppCodeGen, struct_entries
from typing import List
from inflection import underscore
import regex as re


@dataclass
class Params:
  pass

@dataclass
class WireSpec:
  fs: float
  bufsiz: int
  n_chans: int = 1

class Pin:
  def __init__(s, block, name):
    s.name = name
    s.block = block

class OutputPin(Pin):
  def __init__(s, block, name = "output"):
    super().__init__(block, name)
    s.wire_spec = None
    s.buffers = []
    s.input_pins: [InputPin] = []

class InputPin(Pin):
  def __init__(s, block, name = "input"):
    super().__init__(block, name)
    s.output_pin: OutputPin = None

  @property
  def buffers(s): return s.output_pin.buffers

  @property
  def wire_spec(s):
    out_pin = s.output_pin
    return out_pin.wire_spec if out_pin is not None else None


@dataclass
class BlockState:
  pass

class Block:
  instance_count = 0
  in_pin_names = ["input"]
  out_pin_names = ["output"]

  def __init__(s, name = None):
    s.instance_count = Block.instance_count
    s.name = name if name else f'{s.__class__.__name__}_{s.instance_count}'
    s.name = underscore(s.name)
    Block.instance_count += 1
    s.in_pins = [InputPin(s, n) for n in s.__class__.in_pin_names]
    s.out_pins = [OutputPin(s, n) for n in s.__class__.out_pin_names]

  def _find_pin(s, pins:[Pin], name:str):
    for pin in pins:
      if pin.name == name: return pin
    raise Exception(f"can't find pin named {name}")

  def find_in_pin(s, name:str = "input"): return s._find_pin(s.in_pins, name)
  def find_out_pin(s, name:str = "output"): return s._find_pin(s.out_pins, name)
  def get_in_buffer(s, chan: int = 0, pin_name: str = "input"):
    return s._find_pin(pin_name).buffers[chan]
  def get_out_buffer(s, chan: int = 0, pin_name: str = "output"):
    return s.find_out_pin(s, pin_name).buffers[chan]

  def buffers(s, in_pin_idx: int = None, out_pin_idx: int = None,
              chan: int = 0) -> (np.ndarray, np.ndarray):
    in_pin = s.in_pins[in_pin_idx].buffers[chan] if in_pin_idx else None
    out_pin =  s.out_pins[out_pin_idx].buffers[chan] if out_pin_idx else None
    return (in_pin, out_pin)

  @property
  def wire_specs_complete(s) -> bool:
    return True if all(x.wire_spec != None for x in s.out_pins) else False

  # called after wire specs have been propagated, override as needed
  def update_params(s):
    pass

  def c_parameter_list(s):
    fields = s.Params.__dataclass_fields__
    param_names = [k for k,_ in fields.items()]
    values_str = str([getattr(s.params, n) for n in param_names])
    comment_str = f'// {param_names}'
    for i in (("[", ""), ("]", ""), ("\'", "")):
      comment_str = comment_str.replace(i[0], i[1])
    for i in (("[", "{"), ("]", "}")):
      values_str = values_str.replace(i[0], i[1])
    return values_str, comment_str

class SingleFsBlock(Block):
  def __init__(s):
    super().__init__()
    s.shared_wire_spec = None  # dummy pin for storing pin spec

  def propagate_wire_specs(s) -> bool:
    did_set = False
    # first find any input pin specs
    for pin in s.in_pins:
      if (ws := pin.wire_spec) is None:
        continue
      else:
        s.shared_wire_spec = ws
        break
    # check for input pin conflicts
    for pin in s.in_pins:
      if (ws := pin.wire_spec) is None: continue
      if ws != s.shared_wire_spec:
        raise Exception("Input Pin wirespec conflict")
    # set output pin wire specs
    if s.shared_wire_spec is not None:
      for pin in s.out_pins:
        if pin.wire_spec is None:
          pin.wire_spec = copy(s.shared_wire_spec)
          did_set = True
    return did_set


class MultiChannelWrapper(Block):
  c_procs = ('proc', 'init', 'signal_specs_finalized')

  def get_wire_spec(s):
    if len(s.out_pins) > 0: return s.out_pins[0].wire_spec
    else: return s.in_pins[0].wire_spec

  def allocate(s):
    s.n_channels = s.get_wire_spec().n_chans
    s.blocks = [s.Chan(s.params) for chan in range(s.n_channels)]

  def init(s):
    for i in range(s.n_channels):
      s.blocks[i].init()

  def proc(s):
    for i in range(s.n_channels):
      in_bufs = [p.buffers[i] for p in s.in_pins]
      out_bufs = [p.buffers[i] for p in s.out_pins]
      s.blocks[i].proc(in_bufs + out_bufs)

  @classmethod
  def c_create_block_code(cls, gen: CppCodeGen):
    gen.statement(f'class {cls.__name__}')
    gen.ensure_blank_line()
    cls.c_chan_declaration(gen)
    gen.ensure_blank_line()
    cls.c_container_def(gen)
    gen.ensure_blank_line()
    cls.c_chan_methods(gen)
    gen.ensure_blank_line()
    pass

  @classmethod
  def c_container_def(cls, gen: CppCodeGen):
    cls_name = cls.__name__
    chan_name = f'{cls_name}Chan'
    param_name = f'{cls_name}Params'
    n_pins = len(cls.in_pin_names) + len(cls.out_pin_names)
    gen.open_block(f'struct {cls_name} : SingleChanContainer<{chan_name}, {param_name}>')
    # instance var
    if hasattr(cls, "State"):
      instance_defs = struct_entries(cls.State)
      for s in instance_defs: gen.statement(s)
    # constructor
    gen.write_ln(f'{cls_name}(int n_chans, {param_name} params) :')
    gen.indent += 2
    gen.write_ln(f'SingleChanContainer({n_pins}, n_chans, params) {{}}')
    gen.indent -= 2
    # constructor done
    # look for init or proc overrides
    for proc in cls.c_procs:
      if hasattr(cls, f'c_{proc}'):
        gen.ensure_blank_line()
        gen.open_block(f'void {proc}()')
        gen.emit_c_lines(getattr(cls, f'c_{proc}'))
        gen.close_block()
    gen.close_block(semicolon=True)

  @classmethod
  def c_chan_declaration(cls, gen: CppCodeGen):
    cls_name = cls.__name__
    chan_name = f'{cls_name}Chan'
    gen.open_block(f'struct {chan_name} : SingleChanBlock')
    gen.statement(f'{cls_name}* c')
    if hasattr(cls, "Chan"):
      if hasattr(cls.Chan, "State"):
        inst_vars = struct_entries(cls.Chan.State)
        for s in inst_vars: gen.statement(s)
    gen.write_ln(f'{chan_name}(void* c) : c(({cls_name}*)c) {{}}')
    gen.statement('void proc(vector<float*> buffers)')
    for proc in cls.c_procs[1:]:
      if hasattr(cls.Chan, f'c_{proc}'):
        gen.statement(f'void {proc}()')
    gen.close_block(semicolon=True)

  @classmethod
  def c_chan_methods(cls, gen: CppCodeGen):
    def emit_proc(name, arg_list_str = ''):
      gen.ensure_blank_line()
      gen.open_block(f'void {cls.__name__}Chan::{name}({arg_list_str})')
      gen.emit_c_lines(getattr(cls.Chan, f'c_{name}'))
      gen.close_block()
    emit_proc('proc', 'vector<float*> buffers')
    for p in cls.c_procs[1:]:
      if hasattr(cls.Chan, f'c_{p}'):
        emit_proc(p)


class SingleChanBlock:
  def init(s):
    pass


class GainBlock(MultiChannelWrapper, SingleFsBlock):
  def __init__(s, gain):
    super().__init__()
    s.params = GainBlock.Params(gain)

  @dataclass
  class Params:
    gain: float

  class Chan(SingleChanBlock):
    def __init__(s, params):
      s.params = params
      s.state = SingleChanBlock.State()

    def proc(s, buffers):
      buffers[1][:] = buffers[0] * s.gain

    c_proc = '''
      // multiply gain by input buffer
      float* i_ptr = buffers[0];
      float* o_ptr = buffers[1];
      for (int s=0; s < c->bufsiz; s++) {
        o_ptr[s] = i_ptr[s] * c->params.gain;
      }
    '''


class SineBlock(MultiChannelWrapper, SingleFsBlock):
  in_pin_names = []

  def __init__(s, freq):
    super().__init__()
    s.params = SineBlock.Params(freq)

  def update_params(s):
    s.params.fs = s.shared_wire_spec.fs

  @dataclass
  class Params:
    freq: float
    fs: float = 0

  @dataclass
  class State:
    incr: float

  c_init = '''
    auto fs = pins[0].fs;
    incr = 2 * M_PI * params.freq / fs;
    // call channel inits
    SingleChanContainer::init();
  '''

  class Chan(SingleChanBlock):

    @dataclass
    class State:
      phase: float

    def init(s):
      s.state.incr = 2 * math.pi * s.freq / s.params.fs
      s.state.phase = 0

    c_init = '''
      phase = 0;
    '''

    def proc(s, buffers):
      buf = buffers[0]
      for i in range(buf.size):
        buf[i] = math.sin(s.state.phase)
        s.state.phase += s.state.incr

    c_proc = '''
      float* ptr = buffers[0];
      for (int s=0; s < c->bufsiz; s++) {
        ptr[s] = sin(phase);
        phase += c->incr;
      }
    '''


class FixedThreshComparator(MultiChannelWrapper, SingleFsBlock):
  def __init__(s, thresh: float = .75, name = 'single_thresh_comparator'):
    super().__init__(name)
    s.thresh = thresh

  # returns a list of tuples with sample idx and state
  def ch_proc(s, chan, st):
    inbuf, outbuf = s.buffers(0,0,chan)
    outbuf[:] = inbuf > s.thresh


class Divide(MultiChannelWrapper, SingleFsBlock):
  in_pin_names = ["num", "den"]

  def __init__(s, name = 'divide'):
    super().__init__(name)

  def ch_proc(s, chan, st):
    den = s.buffers(0, chan)
    num, outbuf = s.buffers(0,0,chan)
    outbuf[:] = num / den


class Clip(MultiChannelWrapper, SingleFsBlock):
  def __init__(s, min: float = None, max = None, name = 'single_thresh_comparator'):
    super().__init__(name)
    s.min = min
    s.max = max

  # returns a list of tuples with sample idx and state
  def ch_proc(s, chan, st):
    inbuf, outbuf = s.buffers(0,0,chan)
    outbuf[:] = np.clip(inbuf, s.min, s.max)

class FileInput(Block):
  in_pin_names = []

  def __init__(s, filename:str, bufsiz: int, name = "file_input"):
    super().__init__(name)
    s.bufsiz = bufsiz
    s.filename = filename
    s.fs, s.data = read_wav_data(s.filename)
    assert len(s.data.shape) <= 2
    if len(s.data.shape) < 2: s.data = np.expand_dims(s.data, axis=0)
    s.n_channels = 1 if len(s.data.shape) == 1 else s.data.shape[0]
    s.out_pins[0].wire_spec = WireSpec(s.fs, bufsiz, s.n_channels)

  def init(s):
    s._offset = 0
    s.out_buffers = s.out_pins[0].buffers

  def proc(s):
    end_idx = s._offset + s.bufsiz
    d_size = s.data.shape[1]
    for ch in range(s.n_channels):
      if end_idx <= d_size:
        s.out_buffers[ch][:] = s.data[ch][s._offset:end_idx]
      else:
        buf = np.zeros(s.bufsiz)
        bufsiz = d_size-s._offset
        buf[:bufsiz] = s.data[ch][s._offset:d_size]
        s.out_buffers[ch][:] = buf
    s._offset += s.bufsiz

  def propagate_wire_specs(s):
    s.out_pins[0].wire_spec = WireSpec(s.fs, s.bufsiz, s.n_channels)

  @property
  def eof(s):
    siz = len(s.data) if len(s.data.shape) == 1 else s.data.shape[1]
    return s._offset >= siz


class DataSource(SingleFsBlock, MultiChannelWrapper):
  def __init__(s, data: np.ndarray, fs: int, bufsiz: int, name = "file_input"):
    super().__init__(name)
    s.bufsiz = bufsiz
    s.data = data
    s.fs = fs
    assert len(s.data.shape) <= 2
    if len(s.data.shape) < 2: s.data = np.expand_dims(s.data, axis=0)
    s.n_channels = 1 if len(s.data.shape) == 1 else s.data.shape[0]
    s.out_pins[0].wire_spec = WireSpec(s.fs, bufsiz, s.n_channels)

  def init(s):
    s._offset = 0
    s.out_buffers = s.out_pins[0].buffers

  def proc(s):
    end_idx = s._offset + s.bufsiz
    d_size = s.data.shape[1]
    for ch in range(s.n_channels):
      if end_idx <= d_size:
        s.out_buffers[ch][:] = s.data[ch][s._offset:end_idx]
      else:
        buf = np.zeros(s.bufsiz)
        bufsiz = d_size-s._offset
        buf[:bufsiz] = s.data[ch][s._offset:d_size]
        s.out_buffers[ch][:] = buf
    s._offset += s.bufsiz

  def propagate_wire_specs(s):
    s.out_pins[0].wire_spec = WireSpec(s.fs, s.bufsiz, s.n_channels)

  @property
  def eof(s):
    siz = len(s.data) if len(s.data.shape) == 1 else s.data.shape[1]
    return s._offset >= siz


class FileInput(DataSource):
  in_pin_names = []

  def __init__(s, filename:str, bufsiz: int, name = "file_input"):
    fs, data = read_wav_data(s.filename)
    super().__init__(data, fs, bufsiz, name)


class AccumulateData(SingleFsBlock, MultiChannelWrapper):
  out_pin_names = []

  @dataclass
  class Params:
    n_buffers: int

  def __init__(s, n_buffers: int):
    super().__init__()
    s.params = AccumulateData.Params(n_buffers)
    # s.buf_idx = 0
    # s.data = []

  @dataclass
  class State:
    buf_idx: int

  def init(s):
    super().init()
    ws = s.in_pins[0].wire_spec
    data = []
    for i in range(ws.n_chans):
      data.append(np.zeros(0))
      s.state = AccumulateData.State(0, data)

  def proc(s):
    s.state.buf_idx += 1

  c_proc = '''
    SingleChanContainer::proc();
    buf_idx += 1;
  '''

  c_signal_specs_finalized = '''
    for (auto block : blocks) {
      for (int i=0; i<params.n_buffers; i++) {
        block.data.push_back(new float[bufsiz]);
      }
    }
    SingleChanContainer::signal_specs_finalized();
  '''

  class Chan:

    @dataclass
    class State:
      data: List[np.ndarray]

    def proc(s, buffers):
      in_buf = buffers[0]
      if s.buf_idx < s.n_buffers:
        s.data = np.concatenate((s.data, in_buf))

    c_proc = '''
      auto in_buf = buffers[0];
      auto& buf_idx = c->buf_idx;
      if (buf_idx < c->params.n_buffers) {
        std::copy(in_buf, in_buf + c->bufsiz, data[buf_idx]);
        buf_idx += 1; 
      }
    '''



class PlotBuffer(AccumulateData):

  def plot(s):
    plt.figure()
    for state in s.states:
      plt.plot(state.data)



## ----------- Graphs ----------------

def connect(out_block: Block, in_block: Block,
            out_pin_name: str = "output", in_pin_name: str = "input"):
  assert all(isinstance(x, Block) for x in [out_block, in_block])
  assert all(isinstance(x, str) for x in [out_pin_name, in_pin_name])
  out_pin = out_block.find_out_pin(out_pin_name)
  in_pin = in_block.find_in_pin(in_pin_name)
  assert all(isinstance(x, Pin) for x in [out_pin, in_pin])
  out_pin.input_pins.append(in_pin)
  in_pin.output_pin = out_pin

class Graph:
  def __init__(s):
    s._blocks = set([])
    s.processing_order: [Block] = []
    s.code_gen = CppCodeGen()

  def add_block(s, block: Block):
    pass

  def connect(s, out_block: Block, in_block: Block,
              out_pin_name: str = "output", in_pin_name: str = "input"):
    # if either block is not part of the graph, add it, then
    for block in [out_block, in_block]: s._blocks.add(block)
    connect(out_block, in_block, out_pin_name, in_pin_name)

  def determine_proc_order(s):
    proc_order = []
    iter = 0
    while True:
      iter += 1
      found_blk_this_pass = False
      for blk in s._blocks:
        if s.has_been_processed(blk): continue
        if s.can_be_processed(blk):
          s.processing_order.append(blk)
          found_blk_this_pass = True
          break
      if not found_blk_this_pass: break
    # check that all blocks have been processed
    assert all(s.has_been_processed for blk in s._blocks)

  def has_been_processed(s, blk: Block):
    return blk in s.processing_order

  def can_be_processed(s, blk: Block):
    if len(blk.in_pins) == 0: return True  # it's a source block
    input_blks = [pin.output_pin.block for pin in blk.in_pins]
    for blk in input_blks:
      if blk in s.processing_order: continue
      return False
    return True

  # Before calling this, determine_proc_order must be called
  def propagate_wire_specs(s):
    while True:
      did_set = False
      for blk in s.processing_order:
        if blk.propagate_wire_specs() == True: did_set = True
      if did_set == False: break
    assert all(x.wire_specs_complete for x in s.processing_order)

  def update_params(s):
    for blk in s.processing_order:
      blk.update_params()

  # Keep it wasteful and simple for now
  def allocate_buffers(s):
    for blk in s.processing_order:
      for pin in blk.out_pins:
        bufsiz = pin.wire_spec.bufsiz
        pin.buffers = [np.zeros(bufsiz) for _ in range(pin.wire_spec.n_chans)]

  def init_blocks(s):
    for blk in s.processing_order:
      blk.init()

  def run_graph(s):
    for blk in s.processing_order:
      blk.proc()

  def c_allocate_blocks(s):
    for blk in s.processing_order:
      cls_name = blk.__class__.__name__
      inst_name = blk.name
      param_str, comment_str = blk.c_parameter_list()
      if isinstance(blk, MultiChannelWrapper):
        n_chans = blk.get_wire_spec().n_chans
        s.code_gen.write_ln(f'{cls_name} {inst_name}({n_chans}, {cls_name}Params{param_str}); {comment_str}')
      else:
        s.code_gen.write_ln(f'{cls_name} {inst_name}({cls_name}Params{param_str}); {comment_str}')

  def c_setup_pins(s):
    for blk in s.processing_order:
      for i, pin in enumerate(blk.in_pins + blk.out_pins):
        ws = pin.wire_spec
        pin_str = f'Pin({ws.fs}, {ws.n_chans}, {ws.bufsiz})'
        s.code_gen.statement(f'{blk.name}.set_signal_specs({i}, {pin_str})')
      s.code_gen.statement(f'{blk.name}.signal_specs_finalized()')

  def c_allocate_buffers(s):
    buf_idx = 0
    s.c_buf_sizes = []
    s.c_buf_assignments = []
    # create records for allocation and assignment
    for blk in s.processing_order:
      for p,out_pin in enumerate(blk.out_pins):
        n_channels = out_pin.wire_spec.n_chans
        for c in range(n_channels):
          s.c_buf_sizes.append(out_pin.wire_spec.bufsiz)
          s.c_buf_assignments.append((blk.name, buf_idx, p+len(blk.in_pins), c))
        for in_pin in out_pin.input_pins:
          in_blk = in_pin.block
          pin_idx = in_blk.in_pins.index(in_pin)
          blk_name = in_blk.name
          for c in range(n_channels):
            s.c_buf_assignments.append((blk_name, buf_idx, pin_idx, c))
        buf_idx += n_channels
    # emit c code for buffer allocation
    buf_ctr = 0
    buf_init_list = []
    for bufsiz in s.c_buf_sizes:
      name = f'bufdata_{buf_ctr}'
      s.code_gen.statement(f'float {name}[{bufsiz}]')
      buf_init_list.append((name, bufsiz))
      buf_ctr += 1
    s.code_gen.ensure_blank_line()
    s.code_gen.open_block(f'Buffer buffer_pool[{len(buf_init_list)}] =')
    for buf in buf_init_list:
      s.code_gen.write_ln(f'Buffer({buf[1]}, {buf[0]}),')
    s.code_gen.close_block(semicolon=True)

  def assign_buffers(s):
    s.code_gen.ensure_blank_line()
    s.code_gen.write_ln('// Assign Buffers (args are buf_idx, pin_idx, chan_idx)')
    for a in s.c_buf_assignments:
      s.code_gen.statement(f'{a[0]}.assign_buffer({a[1]}, {a[2]}, {a[3]})')

  def x_c_allocate_buffers(s):
    buf_idx = 0
    for blk in s.processing_order:
      for p,out_pin in enumerate(blk.out_pins):
        n_channels = out_pin.wire_spec.n_chans
        for c in range(n_channels):
          s.code_gen.statement(f'add_buffer({out_pin.wire_spec.bufsiz})')
          s.code_gen.statement(f'{blk.name}.assign_buffer({buf_idx+c}, {p+len(blk.in_pins)}, {c})')
        for in_pin in out_pin.input_pins:
          in_blk = in_pin.block
          pin_idx = in_blk.in_pins.index(in_pin)
          blk_name = in_blk.name
          for c in range(n_channels):
            s.code_gen.statement(f'{blk_name}.assign_buffer({buf_idx+c}, {pin_idx}, {c})')
        buf_idx += n_channels

  def c_create_structs_h(s):
    # first create a list of used blocks
    used_classes = { blk.__class__ for blk in s.processing_order}
    # now generate struct defs
    gen = CppCodeGen()
    gen.write_ln('// Parameter Structure Definition for blocks')
    for c in used_classes:
      n = c.__name__
      if hasattr(c, "Params"): gen.struct_def(c.Params, f'{n}Params')
    print(gen.io.getvalue())

  def c_create_block_code(s):
    used_classes = { blk.__class__ for blk in s.processing_order}
    for c in used_classes:
      name = c.__name__
      s.code_gen.write_ln(f'// ------ {name} ------')
      s.code_gen.write_ln()
      s.code_gen.struct_def(c.Params, f'{name}Params')
      s.code_gen.write_ln()
      c.c_create_block_code(s.code_gen)


  def c_create_src(s):
    s.code_gen.write_ln('// Block and Param Definitions')
    s.code_gen.write_ln()
    s.c_create_block_code()
    s.code_gen.write_ln("// Allocate buffers")
    s.c_allocate_buffers()
    s.code_gen.ensure_blank_line()
    s.code_gen.write_ln("// Allocate Blocks")
    s.c_allocate_blocks()
    s.code_gen.write_ln()
    s.code_gen.open_block("void graph_init()")
    s.code_gen.ensure_blank_line()
    s.code_gen.write_ln("// Setup Pins")
    s.c_setup_pins()
    s.code_gen.ensure_blank_line()
    s.assign_buffers()
    s.code_gen.ensure_blank_line()
    s.code_gen.write_ln("// Call init functions")
    for blk in s.processing_order:
      s.code_gen.statement(f'{blk.name}.init()')
    s.code_gen.close_block()
    s.code_gen.write_ln()
    s.code_gen.open_block("void graph_proc()")
    for blk in s.processing_order:
      s.code_gen.statement(f'{blk.name}.proc()')
    s.code_gen.close_block()
    fp = open("../Daisy/TryStreaming/py_gen.cpp", "w")
    fp.write(s.code_gen.io.getvalue())
    fp.close()

    pass



if __name__ == '__main__':
  src = SineBlock(1000)
  src.shared_wire_spec = WireSpec(44100, 128, 2)
  graph = Graph()
  gain1 = GainBlock(2)
  gain2 = GainBlock(.5)
  plot_buf = AccumulateData(n_buffers=4)
  graph.connect(src, gain1)
  graph.connect(gain1, gain2)
  graph.connect(gain2, plot_buf)
  graph.determine_proc_order()
  graph.propagate_wire_specs()
  graph.update_params()
  graph.allocate_buffers()
  graph.c_create_src()
  graph.init_blocks()
  for i in range(3):
   graph.run_graph()
  plt.figure()
  plt.plot(plot_buf.data[0])
  #plot_buf.plot()

  # import pybind_streaming as pbs
  #
  # pbs_src = pbs.SineBlock(1000)

  graph = Graph()
  src = FileInput("../Audio Files/Stereo.wav", 128)
  dst = PlotBuffer()
  graph.connect(src, dst)
  graph.determine_proc_order()
  graph.propagate_wire_specs()
  graph.c_allocate_blocks()
  graph.allocate_buffers()
  graph.init_blocks()
  while src.eof() is not True:
   graph.run_graph()
  dst.plot()
  pass
