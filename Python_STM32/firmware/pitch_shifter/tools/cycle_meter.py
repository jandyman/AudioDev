"""
cycle_meter.py — live DSP load readout for pitch_shifter firmware.

Polls the monitor registry for the DSP cycle cost of process_chunk: "dsp.cycles.last"
(most recent block) and "dsp.cycles.max" (worst case since the last poll — this
script resets it each poll for a windowed worst-case).  Prints cycles, us, and %
of the per-block budget (CORE_CLOCK_HZ * BLOCK_FRAMES / SAMPLE_RATE).

Works while live audio is running (no halt).  Run from PyCharm.

Requires: pylink-square.  J-Link connected, firmware running.
"""

import os
import struct
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'tools'))
from rtt_common import connect, disconnect
from mem import Mem, check_build_id

def bar(frac, width=30):
  frac = max(0.0, min(1.0, frac))
  n = int(round(frac * width))
  return '█' * n + ' ' * (width - n)

def format_line(label, cycles, budget_cycles, core_clock_hz):
  us = cycles / (core_clock_hz / 1e6)
  pct = cycles / budget_cycles
  flag = ' OVERRUN' if pct >= 1.0 else ''
  return f'{label}: [{bar(pct)}] {cycles:7d} cyc  {us:7.2f} us  {pct*100:5.1f}%{flag}'

def run(map_file, buildid_file, refresh_hz, core_clock_hz, sample_rate, block_frames):
  budget = core_clock_hz * block_frames / sample_rate
  jlink = connect()
  mem = Mem(jlink, map_file)
  check_build_id(mem, buildid_file)
  prof = mem.sym('audio_dsp_profile')              # {last_cycles, max_cycles, block_count}
  print()
  print(f'Per-block budget: {budget:.0f} cyc / {block_frames/sample_rate*1e6:.1f} us '
        f'({block_frames} frames @ {sample_rate} Hz, core {core_clock_hz/1e6:.0f} MHz)')
  print('Polling DSP cycles — Ctrl+C to stop')
  print()
  period = 1.0 / refresh_hz
  try:
    while True:
      t0 = time.monotonic()
      last, mx, _ = struct.unpack('<III', mem.read(prof, 12))
      mem.zero_u32(prof + 4)                        # zero max_cycles → windowed worst-case
      line_last = format_line('last', last, budget, core_clock_hz)
      line_max  = format_line('max ', mx,   budget, core_clock_hz)
      sys.stdout.write(f'\r\033[K{line_last}\n\r\033[K{line_max}\033[F')
      sys.stdout.flush()
      dt = time.monotonic() - t0
      if dt < period:
        time.sleep(period - dt)
  except KeyboardInterrupt:
    print('\n\nstopped.')
  finally:
    disconnect(jlink)

if __name__ == '__main__':
  _build       = os.path.join(os.path.dirname(__file__), '..', 'build')
  map_file     = os.path.join(_build, 'pitch_shifter.map')
  buildid_file = os.path.join(_build, 'pitch_shifter.buildid')
  REFRESH_HZ    = 10
  CORE_CLOCK_HZ = 480_000_000
  SAMPLE_RATE   = 48000
  BLOCK_FRAMES  = 48
  run(map_file, buildid_file, REFRESH_HZ, CORE_CLOCK_HZ, SAMPLE_RATE, BLOCK_FRAMES)
