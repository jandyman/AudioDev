#!/usr/bin/env python3
"""
Real-time audio capture from BlackHole.
Captures audio output from Max for analysis/testing.

Usage:
  python capture_from_blackhole.py --device <index> --duration <seconds>

Example:
  python capture_from_blackhole.py --device 2 --duration 5.0
"""

import argparse
import numpy as np
import sounddevice as sd
from scipy.io import wavfile
from datetime import datetime

def capture_audio(device_index, duration, sample_rate=48000, channels=2):
  """
  Capture audio from BlackHole device.

  Args:
    device_index: Index of BlackHole device (use list_audio_devices.py to find)
    duration: Recording duration in seconds
    sample_rate: Sample rate in Hz (default 48000)
    channels: Number of channels (default 2 for stereo)

  Returns:
    Numpy array of captured audio
  """
  print(f"Recording from device {device_index} for {duration} seconds...")
  print(f"Sample rate: {sample_rate} Hz, Channels: {channels}")
  print("Recording...")

  # Record audio
  recording = sd.rec(
    int(duration * sample_rate),
    samplerate=sample_rate,
    channels=channels,
    device=device_index,
    dtype='float32'
  )
  sd.wait()  # Wait until recording is finished

  print("Recording complete!")
  return recording

def analyze_audio(audio, sample_rate):
  """
  Print basic audio statistics.

  Args:
    audio: Numpy array of audio samples
    sample_rate: Sample rate in Hz
  """
  print("\nAudio Analysis:")
  print(f"  Duration: {len(audio) / sample_rate:.2f} seconds")
  print(f"  Shape: {audio.shape}")
  print(f"  Peak amplitude: {np.max(np.abs(audio)):.4f}")
  print(f"  RMS level: {np.sqrt(np.mean(audio**2)):.4f}")
  print(f"  DC offset: {np.mean(audio):.6f}")

  # Check if signal is present
  if np.max(np.abs(audio)) < 0.001:
    print("\n⚠️  WARNING: Very low signal level detected!")
    print("   Make sure Max is outputting to BlackHole")

def save_audio(audio, sample_rate, filename=None):
  """
  Save audio to WAV file.

  Args:
    audio: Numpy array of audio samples
    sample_rate: Sample rate in Hz
    filename: Output filename (auto-generated if None)
  """
  if filename is None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"capture_{timestamp}.wav"

  # Convert float32 to int16 for WAV file
  audio_int16 = np.int16(audio * 32767)
  wavfile.write(filename, sample_rate, audio_int16)
  print(f"\nSaved to: {filename}")

def main():
  parser = argparse.ArgumentParser(description='Capture audio from BlackHole')
  parser.add_argument('--device', type=int, required=True,
                      help='BlackHole device index (use list_audio_devices.py)')
  parser.add_argument('--duration', type=float, default=5.0,
                      help='Recording duration in seconds (default: 5.0)')
  parser.add_argument('--rate', type=int, default=48000,
                      help='Sample rate in Hz (default: 48000)')
  parser.add_argument('--channels', type=int, default=2,
                      help='Number of channels (default: 2)')
  parser.add_argument('--save', action='store_true',
                      help='Save recording to WAV file')
  parser.add_argument('--output', type=str, default=None,
                      help='Output filename (auto-generated if not specified)')

  args = parser.parse_args()

  # Capture audio
  audio = capture_audio(
    args.device,
    args.duration,
    sample_rate=args.rate,
    channels=args.channels
  )

  # Analyze
  analyze_audio(audio, args.rate)

  # Save if requested
  if args.save:
    save_audio(audio, args.rate, args.output)

if __name__ == '__main__':
  main()
