"""
peak_meter.py — live peak/clip readout for pitch_shifter firmware.

Polls the monitor registry for the input and output absolute peaks
("audio.peak.in" / "audio.peak.out"), resetting them each poll for a windowed
"peak since last read", and prints them as dBFS with a small ASCII bar.

Works while live audio is running (no halt).  Run from PyCharm.

Requires: pylink-square.  J-Link connected, firmware running.
"""

import math
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'tools'))
from rtt_common import connect, disconnect
from mem import Mem, check_image_crc

def dbfs(x):
  return 20.0 * math.log10(x) if x > 0.0 else float('-inf')

def bar(db, db_min=-60.0, width=30):
  if db == float('-inf'): return ' ' * width
  frac = max(0.0, min(1.0, (db - db_min) / (-db_min)))
  n = int(round(frac * width))
  return '█' * n + ' ' * (width - n)

def format_line(label, peak, clip_threshold=0.99):
  db = dbfs(peak)
  db_str = '   -inf' if db == float('-inf') else f'{db:+7.1f}'
  clip = ' CLIP' if peak >= clip_threshold else '     '
  return f'{label}: [{bar(db)}] {db_str} dBFS{clip}'

def run(map_file, bin_file, refresh_hz):
  jlink = connect()
  mem = Mem(jlink, map_file)
  check_image_crc(mem, bin_file)
  in_addr  = mem.sym('audio_in_peak')
  out_addr = mem.sym('audio_out_peak')
  print()
  print('Polling peaks — Ctrl+C to stop')
  print()
  period = 1.0 / refresh_hz
  try:
    while True:
      t0 = time.monotonic()
      in_peak  = mem.read_f32(in_addr)
      out_peak = mem.read_f32(out_addr)
      mem.zero_u32(in_addr)                          # windowed: peak since last poll
      mem.zero_u32(out_addr)
      line_in  = format_line('IN ', in_peak)
      line_out = format_line('OUT', out_peak)
      sys.stdout.write(f'\r\033[K{line_in}\n\r\033[K{line_out}\033[F')
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
  bin_file     = os.path.join(_build, 'pitch_shifter.bin')
  REFRESH_HZ = 10
  run(map_file, bin_file, REFRESH_HZ)
