# rtt_testbench.py — Process audio through STM32 DSP via RTT binary protocol.
#
# Requires: numpy, scipy, matplotlib (conda scipy environment)
# PyCharm interpreter: set to the miniforge3/envs/scipy Python interpreter

import socket, struct, time
import numpy as np
import scipy.io.wavfile as wavfile
import matplotlib.pyplot as plt

# Must match AUDIO_BLOCK_FRAMES in firmware audio.h
BLOCK_FRAMES  = 48
BLOCK_SAMPLES = BLOCK_FRAMES * 2   # stereo interleaved
BLOCK_BYTES   = BLOCK_SAMPLES * 4  # int32_t per sample

# RTT command / response IDs (mirrors rtt_protocol.h)
CMD_PING           = 0x01
CMD_SET_PARAM      = 0x02
CMD_GET_PARAM      = 0x03
CMD_GET_BLOCK_SIZE = 0x04
CMD_SET_BLOCK_SIZE = 0x05
CMD_AUDIO_BLOCK    = 0x06
RESP_ACK           = 0x01
RESP_NAK           = 0x02


class RTTTestbench:

  def __init__(s, host='localhost', port=19021, timeout=5.0):
    s.host, s.port, s.timeout = host, port, timeout
    s._sock: socket.socket | None = None
    s._seq = 0

  def connect(s):
    s._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s._sock.settimeout(s.timeout)
    s._sock.connect((s.host, s.port))
    s._drain_banner()
    s._ping()
    n = s.get_block_size()
    if n != BLOCK_FRAMES:
      raise RuntimeError(f'firmware block size {n} != expected {BLOCK_FRAMES}')

  def disconnect(s):
    if s._sock:
      s._sock.close(); s._sock = None

  def get_block_size(s) -> int:
    seq = s._seq_next()
    s._send([CMD_GET_BLOCK_SIZE, seq])
    resp = s._recv(7)
    if resp[0] != RESP_ACK: raise RuntimeError('GET_BLOCK_SIZE NAK')
    return struct.unpack_from('<I', resp, 3)[0]

  def set_param(s, param_id: int, value: float):
    seq = s._seq_next()
    bits = struct.pack('<f', value)
    s._send(bytes([CMD_SET_PARAM, seq, param_id]) + bits)
    resp = s._recv(3)
    if resp[0] != RESP_ACK: raise RuntimeError(f'SET_PARAM NAK id={param_id}')

  def get_param(s, param_id: int) -> float:
    seq = s._seq_next()
    s._send([CMD_GET_PARAM, seq, param_id])
    resp = s._recv(7)
    if resp[0] != RESP_ACK: raise RuntimeError(f'GET_PARAM NAK id={param_id}')
    return struct.unpack_from('<f', resp, 3)[0]

  def process_block(s, pcm_in: np.ndarray) -> np.ndarray:
    """Send BLOCK_SAMPLES int32 samples, return processed BLOCK_SAMPLES int32."""
    seq = s._seq_next()
    s._send(bytes([CMD_AUDIO_BLOCK, seq]) + pcm_in.astype(np.int32).tobytes())
    resp = s._recv(3 + BLOCK_BYTES)
    if resp[0] != RESP_ACK: raise RuntimeError(f'AUDIO_BLOCK NAK reason={resp[2]:#04x}')
    return np.frombuffer(resp[3:], dtype=np.int32).copy()

  def process_audio(s, audio: np.ndarray) -> np.ndarray:
    """Process float32 stereo [N,2] block by block. Returns same shape."""
    n = len(audio)
    n_blocks = (n + BLOCK_FRAMES - 1) // BLOCK_FRAMES
    padded = np.zeros((n_blocks * BLOCK_FRAMES, 2), dtype=np.float32)
    padded[:n] = audio

    pcm_in  = _encode(padded)
    pcm_out = np.zeros_like(pcm_in)
    for i in range(n_blocks):
      sl = slice(i * BLOCK_SAMPLES, (i + 1) * BLOCK_SAMPLES)
      pcm_out[sl] = s.process_block(pcm_in[sl])
    return _decode(pcm_out)[:n]

  # ---- private ----

  def _drain_banner(s):
    s._sock.settimeout(0.2)
    buf = b''
    try:
      while len(buf) < 1024:
        buf += s._sock.recv(256)
    except (TimeoutError, OSError):
      pass
    s._sock.settimeout(s.timeout)
    print(f'[connect] {buf.decode(errors="replace").strip()}')

  def _ping(s):
    seq = s._seq_next()
    s._send([CMD_PING, seq])
    resp = s._recv(3)
    if resp[0] != RESP_ACK: raise RuntimeError('PING NAK')
    print(f'[connect] PING ok')

  def _seq_next(s) -> int:
    v = s._seq; s._seq = (s._seq + 1) & 0xFF; return v

  def _send(s, data):
    s._sock.sendall(bytes(data) if not isinstance(data, bytes) else data)

  def _recv(s, n: int) -> bytes:
    buf = b''
    while len(buf) < n:
      chunk = s._sock.recv(n - len(buf))
      if not chunk: raise RuntimeError('connection closed')
      buf += chunk
    return buf


# ---- PCM format helpers ----
# Firmware format: 24-bit sample in low 24 bits of int32 (s242f / f2s24 in audio.cpp)

def _encode(audio: np.ndarray) -> np.ndarray:
  """Float32 stereo [N,2] → interleaved int32 with s24 in low 24 bits."""
  flat = np.clip(audio.flatten().astype(np.float32), -0.999985, 0.999985)
  return (flat * 8388608.0).astype(np.int32)

def _decode(samples: np.ndarray) -> np.ndarray:
  """Interleaved int32 (s24, sign-extended by f2s24) → float32 stereo [N,2]."""
  return (samples.astype(np.float32) / 8388608.0).reshape(-1, 2)


# ---- WAV helpers ----

def _load_wav(path: str) -> tuple[np.ndarray, int]:
  """Load WAV → float32 stereo [N,2], sample_rate."""
  rate, data = wavfile.read(path)
  if   data.dtype == np.int16:   f = data.astype(np.float32) / 32768.0
  elif data.dtype == np.int32:   f = data.astype(np.float32) / 2147483648.0
  elif data.dtype == np.float32: f = data
  else: raise ValueError(f'unsupported WAV dtype {data.dtype}')
  if f.ndim == 1: f = np.column_stack([f, f])  # mono → stereo dup
  return f[:, :2].astype(np.float32), rate

def _save_wav(path: str, audio: np.ndarray, rate: int):
  wavfile.write(path, rate, audio.astype(np.float32))


# ---- Test functions ----

def run_file_test(tb: RTTTestbench, in_path: str, out_path: str):
  audio, rate = _load_wav(in_path)
  print(f'processing {len(audio)/rate:.2f}s @ {rate} Hz ...')
  t0 = time.perf_counter()
  out = tb.process_audio(audio)
  dt = time.perf_counter() - t0
  audio_dur = len(audio) / rate
  print(f'done: {dt:.2f}s wall for {audio_dur:.2f}s audio  ({audio_dur/dt:.1f}x realtime)')
  _save_wav(out_path, out, rate)
  print(f'saved → {out_path}')

def run_freq_response(tb: RTTTestbench, sample_rate=48000,
                      f_lo=50, f_hi=18000, n_freqs=80,
                      n_settle_blocks=4, n_meas_blocks=8):
  freqs = np.logspace(np.log10(f_lo), np.log10(f_hi), n_freqs)
  gains_db = []
  print(f'measuring {n_freqs} frequencies {f_lo}–{f_hi} Hz ...')
  for f in freqs:
    # Settle filter state (discard output)
    t = np.arange(n_settle_blocks * BLOCK_FRAMES) / sample_rate
    sine = np.column_stack([np.sin(2*np.pi*f*t)] * 2).astype(np.float32)
    tb.process_audio(sine)

    # Measure
    t = np.arange(n_meas_blocks * BLOCK_FRAMES) / sample_rate
    sine = np.column_stack([np.sin(2*np.pi*f*t)] * 2).astype(np.float32)
    out = tb.process_audio(sine)

    in_rms  = np.sqrt(np.mean(sine[:, 0]**2))
    out_rms = np.sqrt(np.mean(out[:, 0]**2))
    gain_db = 20 * np.log10(max(out_rms / in_rms, 1e-10))
    gains_db.append(gain_db)

  gains_db = np.array(gains_db)
  plt.figure(figsize=(10, 5))
  plt.semilogx(freqs, gains_db)
  plt.xlabel('Frequency (Hz)'); plt.ylabel('Gain (dB)')
  plt.title('STM32 EQ Frequency Response (RTT testbench)')
  plt.grid(True, which='both', alpha=0.3)
  plt.axhline(0, color='k', linewidth=0.5)
  plt.tight_layout(); plt.show()
  return freqs, gains_db


# =============================================================================
# Test configuration — edit here, run from PyCharm
# =============================================================================
if __name__ == '__main__':
  host    = 'localhost'
  port    = 19021
  timeout = 5.0   # seconds — socket timeout waiting for firmware response

  # 'freq_response' — sweep frequencies, plot EQ gain curve
  # 'file'          — process a WAV file through the STM32 DSP
  test_mode = 'freq_response'

  wav_in  = '/path/to/input.wav'
  wav_out = '/tmp/stm32_out.wav'

  tb = RTTTestbench(host, port, timeout)
  tb.connect()
  try:
    if   test_mode == 'freq_response': run_freq_response(tb)
    elif test_mode == 'file':          run_file_test(tb, wav_in, wav_out)
    else: print(f'unknown test_mode: {test_mode}')
  finally:
    tb.disconnect()
