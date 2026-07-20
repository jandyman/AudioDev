#!/usr/bin/env python3
"""
Automated test for andy.gain~ external.
Sends test signals and verifies gain behavior.

This demonstrates how to test DSP behavior:
1. Generate known test signal
2. Capture Max's output via BlackHole
3. Verify expected behavior

Usage:
  python test_dsp_gain.py --device <index>

Example:
  python test_dsp_gain.py --device 2
"""

import argparse
import time
import numpy as np
import sounddevice as sd
from pythonosc import udp_client

class GainTester:
  """Test andy.gain~ external via OSC and audio capture."""

  def __init__(self, blackhole_device, osc_host='127.0.0.1', osc_port=7400):
    self.blackhole_device = blackhole_device
    self.sample_rate = 48000
    self.osc_client = udp_client.SimpleUDPClient(osc_host, osc_port)

  def set_gain(self, gain_value):
    """Send gain value to Max via OSC."""
    print(f"Setting gain to {gain_value}")
    self.osc_client.send_message('/gain', gain_value)
    time.sleep(0.1)  # Allow Max to update

  def capture_audio(self, duration=1.0):
    """Capture audio from BlackHole."""
    print(f"Capturing {duration}s of audio...")
    recording = sd.rec(
      int(duration * self.sample_rate),
      samplerate=self.sample_rate,
      channels=2,
      device=self.blackhole_device,
      dtype='float32'
    )
    sd.wait()
    return recording

  def measure_rms(self, audio):
    """Calculate RMS level of audio signal."""
    return np.sqrt(np.mean(audio**2))

  def test_gain_scaling(self):
    """Test that gain scales signal correctly."""
    print("\n" + "="*60)
    print("TEST: Gain Scaling")
    print("="*60)

    # Test several gain values
    test_gains = [0.0, 0.25, 0.5, 0.75, 1.0]
    results = []

    print("\nMake sure Max is:")
    print("  1. Running andy.gain_osc.maxpat")
    print("  2. Audio is ON")
    print("  3. A test tone is playing through andy.gain~")
    print("  4. Max audio output is set to BlackHole")
    print("\nPress Enter to start test...")
    input()

    for gain in test_gains:
      self.set_gain(gain)
      audio = self.capture_audio(duration=0.5)
      rms = self.measure_rms(audio)
      results.append((gain, rms))
      print(f"  Gain: {gain:.2f} -> RMS: {rms:.4f}")

    # Analyze results
    print("\nAnalysis:")
    ratios = []
    for i in range(1, len(results)):
      gain_ratio = results[i][0] / results[i-1][0] if results[i-1][0] > 0 else None
      rms_ratio = results[i][1] / results[i-1][1] if results[i-1][1] > 0 else None
      if gain_ratio and rms_ratio:
        ratios.append((gain_ratio, rms_ratio))
        error = abs(gain_ratio - rms_ratio)
        print(f"  Gain ratio: {gain_ratio:.2f}, RMS ratio: {rms_ratio:.2f}, Error: {error:.4f}")

    # Check if gain is working correctly
    max_error = max([abs(gr - rr) for gr, rr in ratios]) if ratios else float('inf')
    if max_error < 0.1:
      print("\n✓ TEST PASSED: Gain scaling is correct")
    else:
      print("\n✗ TEST FAILED: Gain scaling is incorrect")
      print(f"  Max error: {max_error:.4f} (expected < 0.1)")

  def test_unity_gain(self):
    """Test that unity gain (1.0) passes signal unchanged."""
    print("\n" + "="*60)
    print("TEST: Unity Gain")
    print("="*60)

    self.set_gain(1.0)
    audio = self.capture_audio(duration=1.0)
    rms = self.measure_rms(audio)

    print(f"Unity gain RMS: {rms:.4f}")

    if rms > 0.01:  # Reasonable signal level
      print("✓ TEST PASSED: Signal passing through")
    else:
      print("✗ TEST FAILED: No signal detected")
      print("  Check that test tone is playing in Max")

  def test_mute(self):
    """Test that gain=0 mutes signal."""
    print("\n" + "="*60)
    print("TEST: Mute (Gain = 0)")
    print("="*60)

    self.set_gain(0.0)
    audio = self.capture_audio(duration=0.5)
    rms = self.measure_rms(audio)

    print(f"Muted RMS: {rms:.6f}")

    if rms < 0.0001:
      print("✓ TEST PASSED: Signal muted")
    else:
      print("✗ TEST FAILED: Signal not fully muted")
      print(f"  Expected RMS < 0.0001, got {rms:.6f}")

def main():
  parser = argparse.ArgumentParser(description='Test andy.gain~ via BlackHole')
  parser.add_argument('--device', type=int, required=True,
                      help='BlackHole device index')
  parser.add_argument('--host', type=str, default='127.0.0.1',
                      help='OSC host (default: 127.0.0.1)')
  parser.add_argument('--port', type=int, default=7400,
                      help='OSC port (default: 7400)')

  args = parser.parse_args()

  tester = GainTester(args.device, args.host, args.port)

  # Run tests
  tester.test_unity_gain()
  tester.test_mute()
  tester.test_gain_scaling()

  print("\n" + "="*60)
  print("All tests complete!")
  print("="*60)

if __name__ == '__main__':
  main()
