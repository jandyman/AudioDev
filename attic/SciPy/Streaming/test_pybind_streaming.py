from old_block_streaming import WireSpec

def setup_pin(block, idx, ws: WireSpec):
  pin = block.pins[idx]
  pin.n_chans = ws.n_chans
  pin.fs = ws.fs
  pin.bufsiz = ws.bufsiz


if __name__ == '__main__':
  import pybind_streaming as pbs
  bufsiz = 64
  pin = pbs.Pin()
  pin.fs = 44100

  # First, we need to know all the wire_spes and processing order
  # Instantiate:
  ws = WireSpec(44100, 128, 2)
  sine_block = pbs.SineBlock(2, 1000)
  setup_pin(sine_block, 0, ws)  # output pin
  sine_block.bufsiz = bufsiz
  gain_block = pbs.GainBlock(2, .75)
  setup_pin(gain_block, 0, ws)  # input pin
  setup_pin(gain_block, 1, ws)  # output pin
  gain_block.bufsiz = bufsiz

  # Allocate Buffers
  pbs.add_buffer(bufsiz)
  pbs.add_buffer(bufsiz)
  pbs.add_buffer(bufsiz)
  pbs.add_buffer(bufsiz)

  # connect buffers (buf #, pin #, chan #)
  sine_block.assign_buffer(0,0,0)
  sine_block.assign_buffer(1,0,1)
  gain_block.assign_buffer(0,0,0)
  gain_block.assign_buffer(1,0,1)
  gain_block.assign_buffer(2,1,0)
  gain_block.assign_buffer(3,1,1)

  sine_block.init()
  gain_block.init()
  for i in range(4):
    sine_block.proc()
    gain_block.proc()
  x = pbs.get_buffer(2)


  pass