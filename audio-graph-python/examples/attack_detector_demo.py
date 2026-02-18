"""
Attack detector test on bass guitar audio.

Loads Bass Notes No Gap.wav, runs through the attack detector, and visualizes:
- Input waveform with trigger markers
- Fast and slow envelopes with note-ended regions highlighted
- Fast envelope derivative vs adaptive threshold
- Zoomed view around a detected attack
"""
import sys
import os
import numpy as np
import scipy.io.wavfile as wav
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build'))

from python import FaustProcessor


def rms_env_py(x, window_s, sr):
    """Replicate the Faust RMS envelope: one-pole lowpass on squared signal, then sqrt."""
    coeff = np.exp(-1.0 / (window_s * sr))
    squared = x * x
    filtered = np.zeros(len(x))
    prev = 0.0
    for i in range(len(x)):
        prev = coeff * prev + (1.0 - coeff) * squared[i]
        filtered[i] = prev
    return np.sqrt(filtered)


def env_follower_py(x, att_s, rel_s, sr):
    """Replicate the Faust asymmetric envelope follower."""
    att_c = np.exp(-1.0 / (att_s * sr))
    rel_c = np.exp(-1.0 / (rel_s * sr))
    env = np.zeros(len(x))
    prev = 0.0
    for i in range(len(x)):
        if x[i] > prev:
            prev = att_c * prev + (1.0 - att_c) * x[i]
        else:
            prev = rel_c * prev
        env[i] = prev
    return env


def run_attack_detector_test():
    print("Attack Detector Test")
    print("=" * 60)

    # Parameters (must match the Faust module)
    rms_window = 0.008
    fast_attack = 0.001
    fast_release = 0.010
    slow_attack = 0.050
    slow_release = 0.200
    end_ratio = 0.5
    armed_thresh = 0.0002
    active_thresh = 0.02

    # Load input audio
    input_path = os.path.join(os.path.dirname(__file__), '..', 'test_audio', 'Bass Notes No Gap.wav')
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

    # Process: 1 input -> 2 outputs (trigger, threshold)
    print("Processing...")
    outputs = processor.process([audio_in])

    trigger_signal = outputs[0]
    threshold_signal = outputs[1]

    # Find trigger points
    trigger_indices = np.where(trigger_signal > 0.5)[0]
    trigger_times_ms = trigger_indices / sample_rate * 1000.0

    print(f"\nDetected {len(trigger_indices)} attack(s):")
    for i, (idx, t_ms) in enumerate(zip(trigger_indices, trigger_times_ms)):
        print(f"  Attack {i+1}: sample {idx} ({t_ms:.1f} ms / {t_ms/1000:.3f} s)")

    # Recompute envelopes in Python for visualization
    print("\nComputing envelopes for visualization...")
    rms = rms_env_py(audio_in, rms_window, sample_rate)
    fast_env = env_follower_py(rms, fast_attack, fast_release, sample_rate)
    slow_env = env_follower_py(rms, slow_attack, slow_release, sample_rate)
    fast_deriv = np.diff(fast_env, prepend=0.0)

    # Note-ended signal
    epsilon = 0.0001
    note_ended = fast_env < (slow_env * end_ratio + epsilon)

    # Adaptive threshold
    adaptive_thresh = np.where(note_ended, armed_thresh, active_thresh)

    # Time axis
    t = np.arange(num_samples) / sample_rate

    # Plot
    fig, axes = plt.subplots(5, 1, figsize=(16, 14), sharex=False)
    fig.suptitle("Attack Detector Test: Bass Notes No Gap.wav", fontsize=14)

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
    axes[1].plot(t, slow_env * end_ratio, 'm--', linewidth=0.5, alpha=0.5,
                 label=f'Slow x {end_ratio} (arm threshold)')
    # Shade note-ended regions
    axes[1].fill_between(t, 0, axes[1].get_ylim()[1] if axes[1].get_ylim()[1] > 0 else 0.2,
                         where=note_ended, alpha=0.1, color='red', label='Note ended (armed)')
    for idx in trigger_indices:
        axes[1].axvline(t[idx], color='red', linewidth=1, alpha=0.5)
    axes[1].set_ylabel('Level')
    axes[1].set_title('Fast vs slow envelope — shaded regions = note ended (trigger armed)')
    axes[1].legend(loc='upper right', fontsize=8)
    axes[1].grid(True, alpha=0.3)
    axes[1].set_xlim(0, t[-1])

    # Panel 3: Fast/slow ratio
    ratio = fast_env / (slow_env + epsilon)
    axes[2].plot(t, ratio, 'b-', linewidth=0.5)
    axes[2].axhline(end_ratio, color='r', linewidth=1, linestyle='--', label=f'End ratio = {end_ratio}')
    axes[2].fill_between(t, 0, 1.5, where=note_ended, alpha=0.1, color='red')
    for idx in trigger_indices:
        axes[2].axvline(t[idx], color='red', linewidth=1, alpha=0.5)
    axes[2].set_ylabel('Fast / Slow')
    axes[2].set_title('Envelope ratio (fast/slow) — below red line = note ended')
    axes[2].legend(loc='upper right', fontsize=8)
    axes[2].grid(True, alpha=0.3)
    axes[2].set_xlim(0, t[-1])
    axes[2].set_ylim(0, 1.5)

    # Panel 4: Fast derivative vs threshold
    axes[3].plot(t, fast_deriv, 'b-', linewidth=0.3, alpha=0.7, label='Fast env derivative')
    axes[3].plot(t, adaptive_thresh, 'r-', linewidth=1.0, label='Adaptive threshold')
    axes[3].plot(t, threshold_signal, 'r--', linewidth=1.0, alpha=0.5, label='Threshold (Faust probe)')
    for idx in trigger_indices:
        axes[3].axvline(t[idx], color='green', linewidth=1, alpha=0.5)
    axes[3].set_ylabel('Derivative')
    axes[3].set_title('Fast envelope derivative vs adaptive threshold')
    axes[3].legend(loc='upper right', fontsize=8)
    axes[3].grid(True, alpha=0.3)
    axes[3].set_xlim(0, t[-1])

    # Panel 5: Zoomed view around first attack (or second if available)
    zoom_idx = 1 if len(trigger_indices) > 1 else 0
    if len(trigger_indices) > zoom_idx:
        trig = trigger_indices[zoom_idx]
        # Show 50ms before and 100ms after
        zoom_start = max(0, trig - int(0.05 * sample_rate))
        zoom_end = min(num_samples, trig + int(0.1 * sample_rate))
        t_zoom = t[zoom_start:zoom_end] * 1000

        axes[4].plot(t_zoom, audio_in[zoom_start:zoom_end], 'b-', linewidth=0.5, alpha=0.7, label='Waveform')
        ax4b = axes[4].twinx()
        ax4b.plot(t_zoom, fast_env[zoom_start:zoom_end], 'g-', linewidth=1.0, label='Fast env')
        ax4b.plot(t_zoom, slow_env[zoom_start:zoom_end] * end_ratio, 'm--', linewidth=0.8, label=f'Slow x {end_ratio}')
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
    print("Attack Detector Test Complete")


if __name__ == "__main__":
    run_attack_detector_test()
