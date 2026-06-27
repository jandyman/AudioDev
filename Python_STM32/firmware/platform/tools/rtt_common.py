"""
rtt_common.py — shared RTT helpers for all firmware tools.

Provides connect/disconnect and the core read primitive used by every
project-specific RTT tool.  Protocol-level commands (ping, set_param,
audio_block, etc.) live in the per-project scripts.

Requires: pip install pylink-square
"""

import sys
import time

try:
  import pylink
except ImportError:
  sys.exit("pylink-square not installed — run: pip install pylink-square")

RTT_CHANNEL   = 0         # all firmware tools use channel 0
RESP_ACK      = 0x01
RESP_NAK      = 0x02
POLL_INTERVAL = 0.005     # 5 ms between read attempts


_STM32H7_RTT_SEARCH = (
  "SetRTTSearchRanges "
  "0x20000000 0x20000, "   # DTCMRAM         (128 KB) — SimpleEQ lives here
  "0x24000000 0x80000, "   # AXI SRAM / D1   (512 KB) — pitch_shifter lives here
  "0x30000000 0x48000, "   # SRAM1/2/3 (D2)
  "0x38000000 0x10000"     # SRAM4 (D3)
)

def connect(device="STM32H750IB", rtt_search_timeout_s=5.0):
  """Open J-Link SWD connection and start RTT, with diagnostics.

  Polls until the RTT control block is located instead of using a fixed sleep —
  on a cold J-Link USB session the scan across all four STM32H7 search ranges
  can take several seconds, while a warm session resolves in milliseconds.
  """
  jlink = pylink.JLink()
  jlink.open()
  print(f"J-Link opened: {jlink.product_name}  firmware: {jlink.firmware_version}")
  jlink.set_tif(pylink.enums.JLinkInterfaces.SWD)
  jlink.connect(device)
  print(f"Target connected: core_id=0x{jlink.core_id():08X}  halted={jlink.halted()}")
  jlink.exec_command(_STM32H7_RTT_SEARCH)
  jlink.rtt_start()
  deadline = time.monotonic() + rtt_search_timeout_s
  scan_start = time.monotonic()
  n_up = 0
  while True:
    try:
      n_up = jlink.rtt_get_num_up_buffers()
      if n_up > 0:
        break
    except pylink.errors.JLinkRTTException:
      pass
    if time.monotonic() > deadline:
      raise RuntimeError(
        f"RTT control block not found within {rtt_search_timeout_s:.1f}s — "
        "check firmware is running and SetRTTSearchRanges covers .bss placement"
      )
    time.sleep(0.05)
  print(f"RTT control block found in {time.monotonic()-scan_start:.2f}s "
        f"(up buffers: {n_up})")
  banner = jlink.rtt_read(RTT_CHANNEL, 256)
  if banner:
    print(f"RTT banner ({len(banner)} bytes): {bytes(banner)!r}")
  n = jlink.rtt_write(RTT_CHANNEL, [])
  print(f"RTT down channel write probe returned {n}")
  return jlink


def disconnect(jlink):
  """Stop RTT and close J-Link."""
  jlink.rtt_stop()
  jlink.close()


def rtt_read_exact(jlink, n, timeout_s=1.0):
  """Read exactly n bytes from RTT up channel 0.

  Returns bytes on success, None on timeout.
  """
  buf = []
  deadline = time.monotonic() + timeout_s
  while len(buf) < n:
    chunk = jlink.rtt_read(RTT_CHANNEL, n - len(buf))
    buf.extend(chunk)
    if len(buf) < n:
      if time.monotonic() > deadline:
        return None
      time.sleep(POLL_INTERVAL)
  return bytes(buf)


def rtt_write(jlink, data):
  """Write bytes (or list of ints) to RTT down channel 0.

  Returns number of bytes actually accepted by J-Link.  A return value
  less than len(data) means the RTT down buffer is full or not found.
  """
  return jlink.rtt_write(RTT_CHANNEL, list(data))
