"""
Zero Crossing Detector demo — visualization of Faust module probe outputs.

All DSP is done in the Faust module. Python is purely test harness and visualization.

Faust outputs:
  0: zero crossing impulse (0 or 1)
  1: amplitude envelope (probe)
  2: raw positive-going zero crossing before gating (probe)
  3: derivative magnitude at each qualified crossing, 0 elsewhere (probe)
"""
import sys
import os
import numpy as np
import scipy.io.wavfile as wav
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build'))

from build.pybind_faust_zero_crossing_detector import FaustZeroCrossingDetector


def run_zero_crossing_detector_demo():
    print("Zero Crossing Detector Demo")
    print("=" * 60)

    # Load input audio
    input_path = os.path.join(os.path.dirname(__file__), '..', '..', 'test_audio', 'Bass Notes.wav')
    sample_rate, audio_data = wav.read(input_path)

    if audio_data.dtype == np.int16:
        audio_in = audio_data.astype(np.float64) / 32768.0
    elif audio_data.dtype == np.int32:
        audio_in = audio_data.astype(np.float64) / 2147483648.0
    else:
        audio_in = audio_data.astype(np.float64)

    if audio_in.ndim > 1:
        audio_in = audio_in[:, 0]

    num_samples = len(audio_in)
    duration = num_samples / sample_rate

    print(f"\nInput: {os.path.basename(input_path)}")
    print(f"  Sample rate: {sample_rate} Hz")
    print(f"  Duration: {duration:.2f} seconds")
    print(f"  Samples: {num_samples}")

    # Run Faust module
    detector = FaustZeroCrossingDetector()
    detector.init(sample_rate)
    print(f"\nModule: {detector.get_num_inputs()} input(s), {detector.get_num_outputs()} output(s)")

    outputs = detector.process([audio_in])

    zc_out   = outputs[0]
    amp_env  = outputs[1]
    raw_zc   = outputs[2]
    zc_deriv = outputs[3]

    # Statistics
    zc_indices     = np.where(zc_out > 0.5)[0]
    raw_zc_indices = np.where(raw_zc > 0.5)[0]

    print(f"\nRaw positive-going zero crossings: {len(raw_zc_indices)}")
    print(f"Qualified zero crossings:          {len(zc_indices)}")
    print(f"Rejected by gating:                {len(raw_zc_indices) - len(zc_indices)}")

    deriv_values = zc_deriv[zc_indices]  # derivative at each qualified crossing

    if len(zc_indices) > 1:
        spacings_ms = np.diff(zc_indices) / sample_rate * 1000
        print(f"\nQualified ZC spacing (ms):")
        print(f"  Min:    {spacings_ms.min():.2f} ms  ({1000/spacings_ms.min():.0f} Hz)")
        print(f"  Max:    {spacings_ms.max():.2f} ms  ({1000/spacings_ms.max():.0f} Hz)")
        print(f"  Median: {np.median(spacings_ms):.2f} ms  ({1000/np.median(spacings_ms):.0f} Hz)")

    print(f"\nDerivative at qualified crossings:")
    print(f"  Min:    {deriv_values.min():.5f}")
    print(f"  Max:    {deriv_values.max():.5f}")
    print(f"  Median: {np.median(deriv_values):.5f}")

    t = np.arange(num_samples) / sample_rate
    min_amplitude = 0.01  # matches Faust parameter

    fig, axes = plt.subplots(5, 1, figsize=(16, 15), sharex=True)
    fig.suptitle("Zero Crossing Detector: Bass Notes.wav", fontsize=14)

    # Panel 1: Waveform with qualified ZC markers
    axes[0].plot(t, audio_in, 'b-', linewidth=0.3, alpha=0.7)
    for idx in zc_indices:
        axes[0].axvline(t[idx], color='green', linewidth=0.8, alpha=0.6)
    axes[0].set_ylabel('Amplitude')
    axes[0].set_title(f'Input waveform with qualified zero crossings (green) — {len(zc_indices)} total')
    axes[0].grid(True, alpha=0.3)
    axes[0].set_xlim(0, t[-1])  # sharex propagates this to all panels

    # Panel 2: Amplitude envelope with threshold
    axes[1].plot(t, amp_env, 'orange', linewidth=0.8, label='Amplitude envelope')
    axes[1].axhline(min_amplitude, color='red', linewidth=1.0, linestyle='--',
                    label=f'min_amplitude = {min_amplitude}')
    for idx in zc_indices:
        axes[1].axvline(t[idx], color='green', linewidth=0.5, alpha=0.4)
    axes[1].set_ylabel('Level')
    axes[1].set_title('Amplitude envelope — crossings below threshold (red dashed) are rejected')
    axes[1].legend(loc='upper right', fontsize=8)
    axes[1].grid(True, alpha=0.3)


    # Panel 3: Raw vs qualified crossings (rolling count over 50ms windows)
    window = int(0.050 * sample_rate)
    raw_density    = np.convolve(raw_zc,  np.ones(window) / window * sample_rate, mode='same')
    qual_density   = np.convolve(zc_out,  np.ones(window) / window * sample_rate, mode='same')
    axes[2].plot(t, raw_density,  'r-', linewidth=0.8, alpha=0.7, label='Raw ZC rate (Hz)')
    axes[2].plot(t, qual_density, 'g-', linewidth=1.0, label='Qualified ZC rate (Hz)')
    axes[2].set_ylabel('Rate (Hz)')
    axes[2].set_title('Zero crossing rate: raw vs qualified (50ms window) — qualified should match note pitch')
    axes[2].legend(loc='upper right', fontsize=8)
    axes[2].grid(True, alpha=0.3)


    # Panel 4: Zoomed view on first note — individual ZC detections
    zoom_start_s = 0.0
    zoom_end_s   = min(duration, 0.15)  # first 150ms
    zoom_start   = int(zoom_start_s * sample_rate)
    zoom_end     = int(zoom_end_s   * sample_rate)
    t_zoom_ms    = t[zoom_start:zoom_end] * 1000

    axes[3].plot(t_zoom_ms, audio_in[zoom_start:zoom_end], 'b-', linewidth=0.8, alpha=0.8, label='Waveform')
    raw_in_zoom  = raw_zc_indices[(raw_zc_indices >= zoom_start) & (raw_zc_indices < zoom_end)]
    qual_in_zoom = zc_indices[(zc_indices >= zoom_start) & (zc_indices < zoom_end)]
    for idx in raw_in_zoom:
        axes[3].axvline(t[idx] * 1000, color='red', linewidth=0.8, alpha=0.4)
    for idx in qual_in_zoom:
        axes[3].axvline(t[idx] * 1000, color='green', linewidth=1.2, alpha=0.8)
    axes[3].set_xlabel('Time (ms)')
    axes[3].set_ylabel('Amplitude')
    axes[3].set_title(f'Zoomed: first {zoom_end_s*1000:.0f}ms — raw ZCs (red), qualified ZCs (green)')
    axes[3].grid(True, alpha=0.3)

    # Panel 5: Derivative magnitude as variable-height impulse stream
    axes[4].plot(t, zc_deriv, 'purple', linewidth=0.8)
    axes[4].set_xlabel('Time (s)')
    axes[4].set_ylabel('Derivative')
    axes[4].set_title('Derivative magnitude at each qualified crossing — larger = stronger fundamental crossing')
    axes[4].grid(True, alpha=0.3)


    plt.tight_layout(rect=[0, 0, 1, 0.97])

    output_path = os.path.join(os.path.dirname(__file__), '..', '..', 'test_audio_out',
                               'zero_crossing_detector_demo.png')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=150)
    print(f"\nPlot saved to {output_path}")
    plt.show()

    print("\n" + "=" * 60)
    print("Zero Crossing Detector Demo Complete")


if __name__ == "__main__":
    run_zero_crossing_detector_demo()
