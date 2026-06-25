"""
cycle_timeseries.py — per-block DSP cost time-series for pitch_shifter firmware.

Reads the firmware's rolling ring of the last 128 block costs from the monitor
registry (gauge "dsp.cycles.ring") and plots cycles-per-block against the 1 ms /
480k-cycle deadline.  This is the diagnostic for bursty load: a hard real-time
block has no amortization, so the SHAPE matters — a flat baseline with tall
periodic spikes means one block (the YIN search) dominates the budget while its
neighbours idle.

YIN is the only block whose per-block cost varies, so it is read off directly:
  baseline   = median block cost (non-search blocks)
  YIN search = peak - baseline
  period     = blocks between spikes

Play a sustained low bass note into the board, then run this to capture the most
recent 128 ms.  Run from PyCharm.

Requires: pylink-square, numpy, matplotlib.  J-Link connected, firmware running.
"""

import os
import struct
import sys
import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'tools'))
from rtt_common import connect, disconnect
from mem import Mem, check_build_id

RING_LEN = 128   # AUDIO_PROFILE_RING

def analyze_and_plot(ring, mx, block_count, core_clock_hz, sample_rate, block_frames):
  budget = core_clock_hz * block_frames / sample_rate    # cycles/block deadline
  to_us  = 1e6 / core_clock_hz
  to_pct = 100.0 / budget

  baseline = float(np.median(ring))
  spike_thresh = baseline + 0.25 * (ring.max() - baseline)
  spikes = np.where(ring > spike_thresh)[0]
  yin_cost = ring.max() - baseline
  period = float(np.mean(np.diff(spikes))) if len(spikes) >= 2 else float('nan')

  print(f"blocks seen total : {block_count}")
  print(f"budget            : {budget:.0f} cyc / {budget*to_us:.0f} us per block")
  print(f"baseline (median) : {baseline:8.0f} cyc  {baseline*to_us:6.1f} us  {baseline*to_pct:4.1f}%")
  print(f"max (worst block) : {mx:8d} cyc  {mx*to_us:6.1f} us  {mx*to_pct:4.1f}%")
  print(f"YIN search (peak-baseline): {yin_cost:.0f} cyc  {yin_cost*to_us:.1f} us  {yin_cost*to_pct:.1f}%")
  print(f"spike period      : {period:.1f} blocks ({period*block_frames/sample_rate*1e3:.1f} ms)"
        if period == period else "spike period      : (n/a — <2 spikes in window)")

  t_ms = np.arange(RING_LEN) * block_frames / sample_rate * 1e3
  fig, ax = plt.subplots(figsize=(12, 5))
  ax.plot(t_ms, ring * to_pct, drawstyle='steps-mid', lw=1.2, color='#1f77b4', label='per-block cost')
  ax.axhline(100.0, color='red', lw=1.5, ls='--', label='deadline (100%)')
  ax.axhline(baseline * to_pct, color='green', lw=1.0, ls=':', label=f'baseline {baseline*to_pct:.1f}%')
  ax.plot(t_ms[spikes], ring[spikes] * to_pct, 'v', color='darkorange', ms=9, label='YIN search blocks')
  ax.set_xlabel('time (ms, most recent 128 blocks)')
  ax.set_ylabel('% of per-block deadline')
  ax.set_title(f'Pitch shifter DSP load per block — peak {mx*to_pct:.1f}%, '
               f'YIN burst {yin_cost*to_pct:.1f}%')
  ax.set_ylim(0, max(110, ring.max() * to_pct * 1.1))
  ax.grid(alpha=0.3)
  ax.legend(loc='upper right')
  plt.tight_layout()
  plt.show()

def main(map_file, buildid_file, core_clock_hz, sample_rate, block_frames):
  jlink = connect()
  try:
    mem = Mem(jlink, map_file)
    check_build_id(mem, buildid_file)
    last, mx, block_count = struct.unpack('<III', mem.read(mem.sym('audio_dsp_profile'), 12))
    words = mem.read_u32_array(mem.sym('audio_dsp_cycle_ring'), RING_LEN)
  finally:
    disconnect(jlink)
  # Unwrap oldest->newest: the next write slot (block_count % RING) is the oldest.
  ring = np.array([words[(block_count + i) % RING_LEN] for i in range(RING_LEN)], dtype=np.float64)
  analyze_and_plot(ring, mx, block_count, core_clock_hz, sample_rate, block_frames)

if __name__ == '__main__':
  _build       = os.path.join(os.path.dirname(__file__), '..', 'build')
  map_file     = os.path.join(_build, 'pitch_shifter.map')
  buildid_file = os.path.join(_build, 'pitch_shifter.buildid')
  CORE_CLOCK_HZ = 480_000_000   # H750 SYSCLK (clock.cpp: PLL1 → 480 MHz)
  SAMPLE_RATE   = 48000
  BLOCK_FRAMES  = 48
  main(map_file, buildid_file, CORE_CLOCK_HZ, SAMPLE_RATE, BLOCK_FRAMES)
