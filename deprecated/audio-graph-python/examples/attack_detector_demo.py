"""
Attack detector demo — visualization of Faust module probe outputs.

All DSP is done in the Faust module. Python is purely test harness and visualization.
The Faust module outputs probe signals for its internal state, which we plot directly.

Faust outputs:
  0: attack impulse (0 or 1)
  1: adaptive threshold
  2: fast envelope
  3: slow envelope
  4: note-ended flag (1 = armed, 0 = sustaining)
"""
import sys
import os
import numpy as np
import scipy.io.wavfile as wav
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build'))

from python import FaustProcessor


def run_attack_detector_demo():
    print("Attack Detector Demo")
    print("=" * 60)

    # Load input audio
    input_path = os.path.join(os.path.dirname(__file__), '..', '..', 'test_audio', 'Bass Notes No Gap.wav')
    sample_rate, audio_data = wav.read(input_path)

    # Convert to float [-1, 1]
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

    # Create Faust processor
    dsp_path = os.path.join(os.path.dirname(__file__), '..', '..', 'dsp_library', 'faust', 'attack_detector.dsp')
    processor = FaustProcessor(dsp_path, name="attack_detector")
    processor.init(sample_rate)

    print(f"\nProcessor: {processor.get_num_inputs()} input(s), {processor.get_num_outputs()} output(s)")

    # Process: 1 input -> 5 outputs
    print("Processing...")
    outputs = processor.process([audio_in])

    trigger = outputs[0]
    threshold = outputs[1]
    fast_env = outputs[2]
    slow_env = outputs[3]
    note_ended = outputs[4]

    # Find trigger points
    trigger_indices = np.where(trigger > 0.5)[0]
    trigger_times_ms = trigger_indices / sample_rate * 1000.0

    print(f"\nDetected {len(trigger_indices)} attack(s):")
    for i, (idx, t_ms) in enumerate(zip(trigger_indices, trigger_times_ms)):
        print(f"  Attack {i+1}: sample {idx} ({t_ms:.1f} ms / {t_ms/1000:.3f} s)")

    # Derived signals for plotting
    fast_deriv = np.diff(fast_env, prepend=0.0)
    epsilon = 0.0001
    ratio = fast_env / (slow_env + epsilon)

    # Time axis
    t = np.arange(num_samples) / sample_rate

    # Plot
    fig, axes = plt.subplots(5, 1, figsize=(16, 14))
    fig.suptitle("Attack Detector: Bass Notes No Gap.wav", fontsize=14)

    # Panel 1: Waveform with triggers
    axes[0].plot(t, audio_in, 'b-', linewidth=0.3, alpha=0.7)
    for idx in trigger_indices:
        axes[0].axvline(t[idx], color='red', linewidth=1.5, alpha=0.8)
    axes[0].set_ylabel('Amplitude')
    axes[0].set_title('Input waveform with detected attacks (red lines)')
    axes[0].grid(True, alpha=0.3)
    axes[0].set_xlim(0, t[-1])

    # Panel 2: Fast and slow envelopes with note-ended regions
    axes[1].plot(t, fast_env, 'g-', linewidth=0.8, label='Fast env')
    axes[1].plot(t, slow_env, 'm-', linewidth=0.8, label='Slow env')
    axes[1].fill_between(t, 0, axes[1].get_ylim()[1] if axes[1].get_ylim()[1] > 0 else 0.2,
                         where=note_ended > 0.5, alpha=0.1, color='red', label='Note ended (armed)')
    for idx in trigger_indices:
        axes[1].axvline(t[idx], color='red', linewidth=1, alpha=0.5)
    axes[1].set_ylabel('Level')
    axes[1].set_title('Fast vs slow envelope (from Faust probes) — shaded = note ended')
    axes[1].legend(loc='upper right', fontsize=8)
    axes[1].grid(True, alpha=0.3)
    axes[1].set_xlim(0, t[-1])

    # Panel 3: Envelope ratio
    axes[2].plot(t, ratio, 'b-', linewidth=0.5)
    axes[2].axhline(0.75, color='r', linewidth=1, linestyle='--', label='End ratio = 0.75')
    axes[2].fill_between(t, 0, 1.5, where=note_ended > 0.5, alpha=0.1, color='red')
    for idx in trigger_indices:
        axes[2].axvline(t[idx], color='red', linewidth=1, alpha=0.5)
    axes[2].set_ylabel('Fast / Slow')
    axes[2].set_title('Envelope ratio — below red line = note ended')
    axes[2].legend(loc='upper right', fontsize=8)
    axes[2].grid(True, alpha=0.3)
    axes[2].set_xlim(0, t[-1])
    axes[2].set_ylim(0, 1.5)

    # Panel 4: Fast derivative vs threshold
    axes[3].plot(t, fast_deriv, 'b-', linewidth=0.3, alpha=0.7, label='Fast env derivative')
    axes[3].plot(t, threshold, 'r-', linewidth=1.0, label='Adaptive threshold (Faust)')
    for idx in trigger_indices:
        axes[3].axvline(t[idx], color='green', linewidth=1, alpha=0.5)
    axes[3].set_ylabel('Derivative')
    axes[3].set_title('Fast envelope derivative vs adaptive threshold')
    axes[3].legend(loc='upper right', fontsize=8)
    axes[3].grid(True, alpha=0.3)
    axes[3].set_xlim(0, t[-1])

    # Panel 5: Zoomed view around a detected attack
    zoom_idx = 1 if len(trigger_indices) > 1 else 0
    if len(trigger_indices) > zoom_idx:
        trig = trigger_indices[zoom_idx]
        zoom_start = max(0, trig - int(0.05 * sample_rate))
        zoom_end = min(num_samples, trig + int(0.1 * sample_rate))
        t_zoom = t[zoom_start:zoom_end] * 1000

        axes[4].plot(t_zoom, audio_in[zoom_start:zoom_end], 'b-', linewidth=0.5, alpha=0.7, label='Waveform')
        ax4b = axes[4].twinx()
        ax4b.plot(t_zoom, fast_env[zoom_start:zoom_end], 'g-', linewidth=1.0, label='Fast env')
        ax4b.plot(t_zoom, slow_env[zoom_start:zoom_end] * 0.75, 'm--', linewidth=0.8, label='Slow x 0.75')
        ax4b.set_ylabel('Envelope level', color='g')
        axes[4].axvline(t[trig] * 1000, color='red', linewidth=2, alpha=0.8)
        axes[4].set_xlabel('Time (ms)')
        axes[4].set_ylabel('Amplitude')
        axes[4].set_title(f'Zoomed: attack #{zoom_idx+1} at {t[trig]*1000:.1f} ms')
        axes[4].grid(True, alpha=0.3)
        lines1, labels1 = axes[4].get_legend_handles_labels()
        lines2, labels2 = ax4b.get_legend_handles_labels()
        ax4b.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=8)
    else:
        axes[4].text(0.5, 0.5, 'No attacks detected', transform=axes[4].transAxes,
                     ha='center', va='center', fontsize=14)
        axes[4].set_title('Zoomed view (no attacks to show)')

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.subplots_adjust(hspace=0.45)
    output_path = os.path.join(os.path.dirname(__file__), 'attack_detector_test.png')
    plt.savefig(output_path, dpi=150)
    print(f"\nPlot saved to {output_path}")
    plt.show()

    print("\n" + "=" * 60)
    print("Attack Detector Demo Complete")


if __name__ == "__main__":
    run_attack_detector_demo()
