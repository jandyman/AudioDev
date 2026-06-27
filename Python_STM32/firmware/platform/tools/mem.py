"""
mem.py — host side of the RTT generic memory read/write commands.

Resolves symbol addresses from the firmware .map, then reads/writes target memory
by asking the CPU to do it (RTT CMD_READ_MEM / CMD_WRITE_MEM).  Because the CPU
performs the access, reads of cacheable RAM are D-cache coherent — unlike a
debugger reading SRAM directly.  An image-CRC handshake (audio_image_crc, which
the firmware computes over its own flash image at boot, vs a CRC of the local
pitch_shifter.bin) ensures the running binary IS the one whose .map we resolve
against — catching any source, flag, opt-level, or toolchain difference.

See docs/telemetry.md.  Requires: pylink-square.  J-Link connected, firmware running.
"""

import os
import re
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(__file__))
from rtt_common import rtt_write, rtt_read_exact, RESP_ACK

CMD_READ_MEM  = 0x20
CMD_WRITE_MEM = 0x21


def find_symbol(map_file, symbol):
  with open(map_file) as f:
    content = f.read()
  m = re.search(rf"0x([0-9a-fA-F]+)\s+{re.escape(symbol)}\b", content)
  if not m:
    raise ValueError(f"{symbol} not found in {map_file}")
  return int(m.group(1), 16)


def image_crc(bin_file):
  """CRC-32/ISO-HDLC of the firmware .bin — must match the firmware's self-CRC.
  zlib.crc32 uses the same polynomial/reflection/xorout as crc32_iso_hdlc() in
  the firmware's main.cpp, so the two agree over identical bytes."""
  with open(bin_file, 'rb') as f:
    return zlib.crc32(f.read()) & 0xFFFFFFFF


class Mem:
  """Symbol resolution (from the .map) + CPU-mediated memory read/write over RTT."""

  def __init__(s, jlink, map_file):
    s.jlink = jlink
    s.map_file = map_file
    s.seq = 0

  def _next_seq(s):
    q = s.seq
    s.seq = (s.seq + 1) & 0xFF
    return q

  def sym(s, name):
    return find_symbol(s.map_file, name)

  def read(s, addr, n):
    seq = s._next_seq()
    rtt_write(s.jlink, struct.pack('<BBIH', CMD_READ_MEM, seq, addr, n))
    resp = rtt_read_exact(s.jlink, 2 + n, timeout_s=1.0)
    if resp is None or resp[0] != RESP_ACK or resp[1] != seq:
      raise RuntimeError(f"READ_MEM @0x{addr:08x} len {n} failed: "
                         f"{resp[:4] if resp else None!r}")
    return resp[2:]

  def write(s, addr, data):
    seq = s._next_seq()
    rtt_write(s.jlink, struct.pack('<BBIH', CMD_WRITE_MEM, seq, addr, len(data)) + bytes(data))
    resp = rtt_read_exact(s.jlink, 2, timeout_s=1.0)
    if resp is None or resp[0] != RESP_ACK or resp[1] != seq:
      raise RuntimeError(f"WRITE_MEM @0x{addr:08x} failed: {resp!r}")

  # typed convenience helpers
  def read_u32(s, addr):        return struct.unpack('<I', s.read(addr, 4))[0]
  def read_f32(s, addr):        return struct.unpack('<f', s.read(addr, 4))[0]
  def read_u32_array(s, addr, n): return list(struct.unpack(f'<{n}I', s.read(addr, 4 * n)))
  def zero_u32(s, addr):        s.write(addr, b'\x00\x00\x00\x00')


def check_image_crc(mem, bin_file):
  """Abort unless the running firmware's self-CRC matches a CRC of the local .bin."""
  expected = image_crc(bin_file)
  target = mem.read_u32(mem.sym('audio_image_crc'))
  if target == 0:
    raise RuntimeError("audio_image_crc == 0 — firmware not booted past init / not running")
  if target != expected:
    raise RuntimeError(
      f"image-CRC mismatch: target 0x{target:08x} != {os.path.basename(bin_file)} 0x{expected:08x}\n"
      "  → flashed firmware ≠ this build; reflash the firmware or rebuild it")
