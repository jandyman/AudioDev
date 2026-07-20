#!/usr/bin/env python3
"""
Real-time audio monitoring with FFT visualization.
Monitors Max's audio output via BlackHole with live spectrum display.

Usage:
  python monitor_audio_fft.py --device <index>

Example:
  python monitor_audio_fft.py --device 2

Requirements:
  pip install sounddevice numpy matplotlib scipy
"""

import argparse
import numpy as np
import sounddevice as sd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

class AudioMonitor:
  """Real-time audio monitor with FFT display."""

  def __init__(self, device_index, sample_rate=48000, block_size=2048):
    self.device_index = device_index
    self.sample_rate = sample_rate
    self.block_size = block_size
    self.audio_buffer = np.zeros(block_size)

    # FFT setup
    self.fft_freqs = np.fft.rfftfreq(block_size, 1/sample_rate)

    # Setup plot
    self.fig, (self.ax_time, self.ax_freq) = plt.subplots(2, 1, figsize=(10, 8))

    # Time domain plot
    self.line_time, = self.ax_time.plot(np.zeros(block_size))
    self.ax_time.set_ylim(-1, 1)
    self.ax_time.set_xlabel('Sample')
    self.ax_time.set_ylabel('Amplitude')
    self.ax_time.set_title('Time Domain')
    self.ax_time.grid(True)

    # Frequency domain plot
    self.line_freq, = self.ax_freq.semilogx(self.fft_freqs[1:], np.zeros(len(self.fft_freqs)-1))
    self.ax_freq.set_ylim(-120, 0)
    self.ax_freq.set_xlim(20, sample_rate/2)
    self.ax_freq.set_xlabel('Frequency (Hz)')
    self.ax_freq.set_ylabel('Magnitude (dB)')
    self.ax_freq.set_title('Frequency Spectrum')
    self.ax_freq.grid(True, which='both', alpha=0.3)

    plt.tight_layout()

  def audio_callback(self, indata, frames, time, status):
    """Called by sounddevice for each audio block."""
    if status:
      print(status)
    # Store mono downmix
    self.audio_buffer = np.mean(indata, axis=1) if indata.ndim > 1 else indata[:, 0]

  def update_plot(self, frame):
    """Update matplotlib plots."""
    # Update time domain
    self.line_time.set_ydata(self.audio_buffer)

    # Update frequency domain
    windowed = self.audio_buffer * np.hanning(self.block_size)
    fft = np.fft.rfft(windowed)
    magnitude_db = 20 * np.log10(np.abs(fft[1:]) + 1e-10)  # Avoid log(0)
    self.line_freq.set_ydata(magnitude_db)

    return self.line_time, self.line_freq

  def run(self):
    """Start audio monitoring with live display."""
    print(f"Monitoring audio from device {self.device_index}")
    print(f"Sample rate: {self.sample_rate} Hz")
    print(f"Block size: {self.block_size} samples")
    print("\nClose the plot window to stop monitoring...")

    with sd.InputStream(
      device=self.device_index,
      channels=2,
      samplerate=self.sample_rate,
      blocksize=self.block_size,
      callback=self.audio_callback
    ):
      ani = FuncAnimation(
        self.fig,
        self.update_plot,
        interval=50,  # Update every 50ms
        blit=True
      )
      plt.show()

def main():
  parser = argparse.ArgumentParser(description='Monitor audio from BlackHole with FFT')
  parser.add_argument('--device', type=int, required=True,
                      help='BlackHole device index (use list_audio_devices.py)')
  parser.add_argument('--rate', type=int, default=48000,
                      help='Sample rate in Hz (default: 48000)')
  parser.add_argument('--block', type=int, default=2048,
                      help='Block size for FFT (default: 2048)')

  args = parser.parse_args()

  monitor = AudioMonitor(args.device, args.rate, args.block)
  monitor.run()

if __name__ == '__main__':
  main()
