"""
peak_meter.py — live peak/clip readout for pitch_shifter firmware.

Polls the running STM32 via RTT for the input and output absolute peaks
since the last read, prints them as dBFS with a small ASCII bar.

Works while live audio is running (no need to suspend the DMA path).

Run from PyCharm.  Edit the configuration variables at the bottom.

Requires: pylink-square (pip install pylink-square)
J-Link connected via SWD.  Firmware must be running.
"""

import os
import struct
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'tools'))
from rtt_common import connect, disconnect, rtt_read_exact, rtt_write, RESP_ACK

CMD_PEAK_READ = 0x20

def read_peaks(jlink, seq):
  rtt_write(jlink, bytes([CMD_PEAK_READ, seq & 0xFF]))
  resp = rtt_read_exact(jlink, 2 + 8, timeout_s=1.0)
  if resp is None or resp[0] != RESP_ACK or resp[1] != (seq & 0xFF):
    raise RuntimeError(f"PEAK_READ failed: {resp!r}")
  in_peak, out_peak = struct.unpack('<ff', resp[2:])
  return in_peak, out_peak

def dbfs(x):
  if x <= 0.0: return float('-inf')
  import math
  return 20.0 * math.log10(x)

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

def run(refresh_hz):
  jlink = connect()
  print()
  print('Polling peaks — Ctrl+C to stop')
  print()
  period = 1.0 / refresh_hz
  seq = 0
  try:
    while True:
      t0 = time.monotonic()
      in_peak, out_peak = read_peaks(jlink, seq)
      seq = (seq + 1) & 0xFF
      line_in  = format_line('IN ', in_peak)
      line_out = format_line('OUT', out_peak)
      # Two-line refresh: \033[F moves cursor up one line, \r returns to col 0.
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
  REFRESH_HZ = 10
  run(REFRESH_HZ)
