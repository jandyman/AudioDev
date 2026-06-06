"""
rtt_verify.py — RTT audio block verification for pitch_shifter firmware.

Sends the first N_VERIFY_SECONDS of test audio to the STM32 via RTT one
48-frame chunk at a time, collects the output, runs the same audio through
the pybind11 reference build, and compares.

Run from PyCharm.  Edit the configuration variables at the bottom.

Requires: pylink-square (pip install pylink-square)
J-Link connected via SWD.  Firmware must be running (not halted in debugger).
"""

import os
import sys
import time
import numpy as np
import scipy.io.wavfile as wavfile
from scipy.signal import resample_poly

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'tools'))
from rtt_common import connect, disconnect, rtt_read_exact, rtt_write, RESP_ACK

# ---- protocol constants ----
CMD_AUDIO_INIT  = 0x10
CMD_AUDIO_BLOCK = 0x11
CMD_AUDIO_END   = 0x12
BLOCK_N         = 48
BLOCK_BYTES     = BLOCK_N * 4

def send_cmd(jlink, cmd, seq, payload=b""):
  rtt_write(jlink, bytes([cmd, seq & 0xFF]) + payload)

# ---- STM32 block transfer ----

def audio_init(jlink, seq):
  send_cmd(jlink, CMD_AUDIO_INIT, seq)
  resp = rtt_read_exact(jlink, 2, timeout_s=2.0)
  if resp is None or resp[0] != RESP_ACK or resp[1] != (seq & 0xFF):
    raise RuntimeError(f"AUDIO_INIT failed: {resp!r}")

def audio_block(jlink, seq, block_in):
  """Send one 48-sample block, receive interleaved L/R back. Returns (L, R) arrays."""
  payload = block_in.astype(np.float32).tobytes()  # little-endian float32, native on ARM
  send_cmd(jlink, CMD_AUDIO_BLOCK, seq, payload)
  resp = rtt_read_exact(jlink, 2 + 2 * BLOCK_BYTES, timeout_s=2.0)
  if resp is None or resp[0] != RESP_ACK or resp[1] != (seq & 0xFF):
    raise RuntimeError(f"AUDIO_BLOCK seq={seq} failed: {resp[:4] if resp else None!r}")
  interleaved = np.frombuffer(resp[2:], dtype=np.float32)
  return interleaved[0::2].copy(), interleaved[1::2].copy()

def audio_end(jlink, seq):
  send_cmd(jlink, CMD_AUDIO_END, seq)
  resp = rtt_read_exact(jlink, 2, timeout_s=2.0)
  if resp is None or resp[0] != RESP_ACK or resp[1] != (seq & 0xFF):
    raise RuntimeError(f"AUDIO_END failed: {resp!r}")

def run_stm32(jlink, audio_in, start_seq=0):
  n_blocks = len(audio_in) // BLOCK_N
  stm32_l = np.zeros(n_blocks * BLOCK_N, dtype=np.float32)
  stm32_r = np.zeros(n_blocks * BLOCK_N, dtype=np.float32)
  seq = start_seq
  audio_init(jlink, seq)
  seq = (seq + 1) & 0xFF

  t0 = time.monotonic()
  for i in range(n_blocks):
    blk_in = audio_in[i * BLOCK_N : (i + 1) * BLOCK_N]
    blk_l, blk_r = audio_block(jlink, seq, blk_in)
    stm32_l[i * BLOCK_N : (i + 1) * BLOCK_N] = blk_l
    stm32_r[i * BLOCK_N : (i + 1) * BLOCK_N] = blk_r
    seq = (seq + 1) & 0xFF
    if (i + 1) % 100 == 0:
      elapsed = time.monotonic() - t0
      print(f"  {i+1}/{n_blocks} blocks  ({elapsed:.1f}s elapsed, "
            f"{(i+1)*BLOCK_N/48000:.2f}s of audio)")

  audio_end(jlink, seq)
  return stm32_l, stm32_r

# ---- pybind11 reference ----

def run_pybind(audio_in, python_dir, sample_rate, pitch_ratio, lpf_fc):
  sys.path.insert(0, python_dir)
  from build.pybind_pitch_shifter import pitch_shifter as PitchShifter
  ps = PitchShifter()
  ps.init(sample_rate)
  ps.set_param("lpf.fc", lpf_fc)
  ps.set_param("lc.pitch_ratio", pitch_ratio)

  n_blocks = len(audio_in) // BLOCK_N
  ref_l = np.zeros(n_blocks * BLOCK_N, dtype=np.float32)
  ref_r = np.zeros(n_blocks * BLOCK_N, dtype=np.float32)
  for i in range(n_blocks):
    blk_in = audio_in[i * BLOCK_N : (i + 1) * BLOCK_N]
    blk_out = ps.process_chunk(blk_in)   # shape (BLOCK_N, 2)
    ref_l[i * BLOCK_N : (i + 1) * BLOCK_N] = blk_out[:, 0]
    ref_r[i * BLOCK_N : (i + 1) * BLOCK_N] = blk_out[:, 1]
  return ref_l, ref_r

# ---- main ----

def main(wav_in, python_dir, out_dir, n_verify_seconds, pitch_ratio, lpf_fc):
  os.makedirs(out_dir, exist_ok=True)

  sample_rate, raw = wavfile.read(wav_in)
  if raw.dtype == np.int16:
    audio_raw = raw.astype(np.float32) / 32768.0
  elif raw.dtype == np.int32:
    audio_raw = raw.astype(np.float32) / 2147483648.0
  else:
    audio_raw = raw.astype(np.float32)
  if audio_raw.ndim > 1:
    audio_raw = audio_raw[:, 0]

  # Firmware always runs at 48 kHz (SAI rate).  Resample so pybind and STM32
  # process identical samples at the rate the algorithm was tuned for.
  STM32_SR = 48000
  if sample_rate != STM32_SR:
    print(f"Resampling {sample_rate} Hz → {STM32_SR} Hz")
    audio_raw = resample_poly(audio_raw, STM32_SR, sample_rate).astype(np.float32)
    sample_rate = STM32_SR

  n_samples = int(n_verify_seconds * sample_rate)
  n_samples = (n_samples // BLOCK_N) * BLOCK_N   # align to block boundary
  audio_in = audio_raw[:n_samples]
  n_blocks = n_samples // BLOCK_N
  print(f"Verifying {n_samples} samples ({n_samples/sample_rate:.2f}s) → {n_blocks} blocks")

  print("\nRunning pybind11 reference...")
  ref_l, ref_r = run_pybind(audio_in, python_dir, sample_rate, pitch_ratio, lpf_fc)
  print(f"  done")

  print(f"\nConnecting to STM32 via RTT...")
  jlink = connect()
  try:
    # Sanity-check RTT comms before committing to the full block transfer.
    n = rtt_write(jlink, [0x10, 0x00])  # CMD_AUDIO_INIT, seq=0
    print(f"Wrote 2 bytes to down channel, J-Link accepted {n}")
    time.sleep(0.3)
    probe = rtt_read_exact(jlink, 2, timeout_s=0.5)
    if probe is None or list(probe) != [0x01, 0x00]:
      raise RuntimeError(f"RTT sanity check failed (got {probe!r}); "
                         "check LED blink rate — fast blink means firmware fault")
    print("RTT OK")
    # Re-init cleanly (seq=0 was already consumed above, start fresh from seq=1).
    stm32_l, stm32_r = run_stm32(jlink, audio_in, start_seq=1)
  finally:
    disconnect(jlink)

  def stats(name, x):
    print(f"  {name}: peak={np.abs(x).max():.4f}  rms={np.sqrt(np.mean(x**2)):.4f}  "
          f"nan={int(np.isnan(x).sum())}  silent_frac={float((np.abs(x) < 1e-6).mean()):.3f}")

  pass_all = True
  for chan, ref, stm32 in (('L (dry)', ref_l, stm32_l), ('R (shifted)', ref_r, stm32_r)):
    diff = np.abs(stm32 - ref)
    peak = float(diff.max())
    rms  = float(np.sqrt(np.mean(diff ** 2)))
    print(f"\n--- Channel {chan} ---")
    print(f"  Max diff = {peak:.3e}   RMS diff = {rms:.3e}")
    stats("STM32 ", stm32)
    stats("pybind", ref)
    first_div = int(np.argmax(diff > 0.01)) if (diff > 0.01).any() else -1
    if first_div >= 0:
      print(f"  First sample with diff > 0.01: index {first_div} "
            f"({first_div/sample_rate*1000:.2f} ms in)")
    if peak >= 1e-3:
      pass_all = False
      print(f"  FAIL — diff exceeds 1e-3")
    else:
      print(f"  PASS")

  stats("input ", audio_in)
  print("\n" + ("OVERALL: PASS" if pass_all else "OVERALL: FAIL"))

  # Write stereo WAVs: (N, 2) array with column 0 = L, column 1 = R.
  stm32_stereo = np.stack([stm32_l, stm32_r], axis=1)
  ref_stereo   = np.stack([ref_l,   ref_r],   axis=1)
  wavfile.write(os.path.join(out_dir, "rtt_stm32_out.wav"),  sample_rate,
                (stm32_stereo * 32767).clip(-32768, 32767).astype(np.int16))
  wavfile.write(os.path.join(out_dir, "rtt_pybind_ref.wav"), sample_rate,
                (ref_stereo   * 32767).clip(-32768, 32767).astype(np.int16))
  print(f"Saved stereo rtt_stm32_out.wav and rtt_pybind_ref.wav to {out_dir}/")


# ---- configuration ----
_here       = os.path.dirname(os.path.abspath(__file__))
wav_in      = os.path.join(_here, "..", "..", "..", "..", "test_audio", "Longer Bass Notes.wav")
python_dir  = os.path.join(_here, "..", "..", "..", "python")
out_dir     = os.path.join(_here, "..", "..", "..", "..", "test_audio_out")

n_verify_seconds = 1.0
pitch_ratio      = 0.5
lpf_fc           = 10000.0

main(wav_in, python_dir, out_dir, n_verify_seconds, pitch_ratio, lpf_fc)
