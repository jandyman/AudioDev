"""set_param.py — set a graph parameter on the running pitch_shifter firmware
over RTT, live, no reflash.

The path routes through the generated graph's set_param: "lc.pitch_ratio"
(0.1..0.99, clamped in firmware; 0.5 = one octave down), "lpf.fc", etc. The
firmware applies it with interrupts briefly disabled so the audio ISR can't read
a half-updated loop_controller.

The pitch shifter is output-side and DOWNWARD only (ratio < 1). In interval
terms ratio = 2**(semitones/12), so semitones must be <= 0. The block knows
nothing about the dry channel — only the shifted (right) output changes.

Run from PyCharm; set SEMITONES (or PARAM/VALUE directly) at the bottom.
"""

import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'tools'))
from rtt_common import connect, disconnect, rtt_write, rtt_read_exact, RESP_ACK

CMD_SET_PARAM = 0x22

def set_param(jlink, path, value, seq=0):
  """Send one SET_PARAM and wait for the ack.

  jlink   open J-Link handle from connect()
  path    graph parameter path, e.g. "lc.pitch_ratio"
  value   float value to set
  seq     1-byte sequence id echoed back in the ack
  """
  name = path.encode('ascii')
  if len(name) > 255:
    raise ValueError("param path too long (max 255 bytes)")
  pkt = bytes([CMD_SET_PARAM, seq & 0xFF, len(name)]) + name + struct.pack('<f', value)
  rtt_write(jlink, pkt)
  resp = rtt_read_exact(jlink, 2, timeout_s=1.0)
  if resp is None or resp[0] != RESP_ACK or resp[1] != (seq & 0xFF):
    raise RuntimeError(f"SET_PARAM {path}={value} failed: {resp!r}")
  print(f"set {path} = {value:.4f}")

def run(path, value):
  jlink = connect()
  try:
    set_param(jlink, path, value)
  finally:
    disconnect(jlink)

if __name__ == '__main__':
  # Interval to shift the right (processed) channel, in semitones DOWN.
  # 0 = unison (~0.99), -12 = octave down (0.5), -24 = two octaves (0.25).
  SEMITONES = -5
  ratio = 2.0 ** (SEMITONES / 12.0)   # firmware clamps to [0.1, 0.99]
  run('lc.pitch_ratio', ratio)
