# rtt_wire_test.py — verify CMD_AUDIO_BLOCK round-trip with firmware in wire mode.
# Sends random int32 blocks, checks returned data is bit-identical.
# No DSP involved — this is a pure RTT transport test.

import socket
import time
import numpy as np

BLOCK_FRAMES  = 48
BLOCK_SAMPLES = BLOCK_FRAMES * 2   # stereo interleaved
BLOCK_BYTES   = BLOCK_SAMPLES * 4  # int32_t per sample


def recv_exactly(sock: socket.socket, n: int) -> bytes:
  buf = b''
  while len(buf) < n:
    chunk = sock.recv(n - len(buf))
    if not chunk: raise RuntimeError('connection closed')
    buf += chunk
  return buf

def drain_banner(sock: socket.socket, main_timeout: float):
  # Read until no more data arrives — banner can be multiple lines and may
  # trickle in as separate TCP segments, so a simple "stop at first \n" races.
  sock.settimeout(0.2)
  buf = b''
  try:
    while len(buf) < 1024:
      buf += sock.recv(256)
  except (TimeoutError, OSError):
    pass
  sock.settimeout(main_timeout)
  print(f'[connect] {buf.decode(errors="replace").strip()}')

def ping(sock: socket.socket, seq: int, retries: int = 3) -> int:
  for attempt in range(retries):
    try:
      sock.sendall(bytes([0x01, seq & 0xFF]))
      resp = recv_exactly(sock, 3)
      assert resp[0] == 0x01, f'PING NAK: {resp[2]:#04x}'
      print(f'[connect] PING ok (attempt {attempt + 1})')
      return (seq + 1) & 0xFF
    except (TimeoutError, AssertionError) as e:
      print(f'[connect] PING attempt {attempt + 1} failed: {e}')
      if attempt == retries - 1: raise
  raise RuntimeError('unreachable')

def get_block_size(sock: socket.socket, seq: int) -> tuple[int, int]:
  import struct
  sock.sendall(bytes([0x04, seq & 0xFF]))
  resp = recv_exactly(sock, 7)
  assert resp[0] == 0x01, 'GET_BLOCK_SIZE NAK'
  n = struct.unpack_from('<I', resp, 3)[0]
  print(f'[connect] block size = {n} frames')
  return n, (seq + 1) & 0xFF

def send_audio_block(sock: socket.socket, seq: int, data: np.ndarray) -> np.ndarray:
  sock.sendall(bytes([0x06, seq & 0xFF]) + data.tobytes())
  resp = recv_exactly(sock, 3 + BLOCK_BYTES)
  assert resp[0] == 0x01, f'AUDIO_BLOCK NAK: {resp[2]:#04x}'
  return np.frombuffer(resp[3:], dtype=np.int32).copy()


# =============================================================================
if __name__ == '__main__':
  host      = 'localhost'
  port      = 19021
  timeout   = 5.0
  n_blocks  = 200
  seed      = 42     # random seed for reproducibility; None = random each run
  # =============================================================================

  rng = np.random.default_rng(seed)

  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  sock.settimeout(timeout)
  sock.connect((host, port))

  drain_banner(sock, timeout)
  seq = 0
  seq = ping(sock, seq)
  block_size, seq = get_block_size(sock, seq)
  assert block_size == BLOCK_FRAMES, f'firmware block size {block_size} != {BLOCK_FRAMES}'

  print(f'\nsending {n_blocks} random blocks ...')
  passed = failed = 0
  block_duration_ms = BLOCK_FRAMES / 48000 * 1000  # real-time budget per block

  t0 = time.perf_counter()
  for i in range(n_blocks):
    data = rng.integers(-8388608, 8388607, BLOCK_SAMPLES, dtype=np.int32)
    out  = send_audio_block(sock, seq, data)
    seq  = (seq + 1) & 0xFF

    if np.array_equal(data, out):
      passed += 1
    else:
      failed += 1
      bad = np.where(data != out)[0]
      print(f'  block {i:3d}: MISMATCH — {len(bad)} samples differ, '
            f'first at [{bad[0]}]: sent {data[bad[0]]:#010x}  got {out[bad[0]]:#010x}')
  elapsed = time.perf_counter() - t0

  sock.close()

  ms_per_block = elapsed / n_blocks * 1000
  status = 'PASS' if failed == 0 else 'FAIL'
  print(f'\n{status}  {passed}/{n_blocks} blocks correct')
  print(f'timing  {elapsed*1000:.1f} ms total  |  {ms_per_block:.2f} ms/block'
        f'  ({ms_per_block / block_duration_ms:.1f}x real-time budget of {block_duration_ms:.1f} ms)')
