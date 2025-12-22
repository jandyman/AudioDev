#!/usr/bin/env python3
"""
List all available audio devices on the system.
Helps identify BlackHole device indices for audio capture.
"""

import sounddevice as sd

print("Available Audio Devices:")
print("=" * 80)
print(sd.query_devices())
print("\n" + "=" * 80)

# Find BlackHole devices specifically
devices = sd.query_devices()
blackhole_devices = []

for i, device in enumerate(devices):
  if 'BlackHole' in device['name']:
    blackhole_devices.append((i, device))

if blackhole_devices:
  print("\nBlackHole Devices Found:")
  for idx, device in blackhole_devices:
    print(f"  Index {idx}: {device['name']}")
    print(f"    Max Input Channels: {device['max_input_channels']}")
    print(f"    Max Output Channels: {device['max_output_channels']}")
    print(f"    Default Sample Rate: {device['default_samplerate']}")
else:
  print("\nNo BlackHole devices found!")
  print("Make sure BlackHole is installed: https://existential.audio/blackhole/")
