"""
Compare Max/MSP and Python attack detector outputs.

Loads the 5 probe output wav files exported from the Max test patcher
and compares them against Python-generated outputs from the compiled
Faust module. Reports max error per channel and plots differences.

Usage:
  python compare_max_python.py [path_to_max_outputs]

If no path given, defaults to the Max application support default
write location. You may need to specify the folder where Max saved
the wav files.
"""
import sys
import os
import numpy as np
import scipy.io.wavfile as wav
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build'))

from build.pybind_faust_attack_detector import FaustAttackDetector
from python import CppProcessor

OUTPUT_NAMES = ['trigger', 'threshold', 'fast_env', 'slow_env', 'note_ended']
MAX_FILE_PREFIX = 'attack_det_'


def find_max_outputs(search_dir):
    """Look for Max-exported wav files in the given directory."""
    files = {}
    for name in OUTPUT_NAMES:
        fname = f"{MAX_FILE_PREFIX}{name}.wav"
        path = os.path.join(search_dir, fname)
        if os.path.exists(path):
            files[name] = path
    return files


def run_python_reference(input_path):
    """Run the compiled Faust attack detector on the input file."""
    sample_rate, audio_data = wav.read(input_path)

    if audio_data.dtype == np.int16:
        audio_in = audio_data.astype(np.float64) / 32768.0
    elif audio_data.dtype == np.int32:
        audio_in = audio_data.astype(np.float64) / 2147483648.0
    else:
        audio_in = audio_data.astype(np.float64)

    if audio_in.ndim > 1:
        audio_in = audio_in[:, 0]

    processor = CppProcessor(FaustAttackDetector())
    processor.init(sample_rate)
    outputs = processor.process([audio_in])

    return sample_rate, audio_in, outputs


def load_max_wav(path):
    """Load a Max-exported wav file and normalize to float64."""
    sample_rate, data = wav.read(path)

    if data.dtype == np.int16:
        return data.astype(np.float64) / 32768.0
    elif data.dtype == np.int32:
        return data.astype(np.float64) / 2147483648.0
    elif data.dtype == np.float32:
        return data.astype(np.float64)
    else:
        return data.astype(np.float64)


def run_comparison():
    # Determine Max output directory
    if len(sys.argv) > 1:
        max_dir = sys.argv[1]
    else:
        # Search project test_audio_out first, then common Max write locations
        project_root = os.path.join(os.path.dirname(__file__), '..', '..')
        candidates = [
            os.path.join(project_root, 'test_audio_out'),
            os.path.expanduser('~/Documents'),
            os.path.expanduser('~/Desktop'),
        ]
        max_dir = None
        for d in candidates:
            files = find_max_outputs(d)
            if len(files) == len(OUTPUT_NAMES):
                max_dir = d
                break

        if max_dir is None:
            print("Could not find Max output files automatically.")
            print(f"Looking for: {MAX_FILE_PREFIX}trigger.wav, etc.")
            print(f"\nSearched: {candidates}")
            print("\nUsage: python compare_max_python.py /path/to/max/outputs/")
            return

    print("Attack Detector: Max vs Python Comparison")
    print("=" * 60)

    # Find Max files
    max_files = find_max_outputs(max_dir)
    print(f"\nMax output directory: {max_dir}")
    print(f"Found {len(max_files)}/{len(OUTPUT_NAMES)} output files:")
    for name, path in max_files.items():
        print(f"  {name}: {os.path.basename(path)}")

    missing = set(OUTPUT_NAMES) - set(max_files.keys())
    if missing:
        print(f"\nMissing files: {missing}")
        print("Cannot compare — need all 5 outputs.")
        return

    # Run Python reference
    input_path = os.path.join(os.path.dirname(__file__), '..', '..', 'test_audio', 'Bass Notes No Gap.wav')
    print(f"\nRunning Python reference on: {os.path.basename(input_path)}")
    sample_rate, audio_in, py_outputs = run_python_reference(input_path)
    num_samples = len(audio_in)
    print(f"  Sample rate: {sample_rate} Hz, {num_samples} samples")

    # Load Max outputs and compare
    print(f"\nComparison results:")
    print(f"{'Output':<15} {'Max samples':<15} {'Py samples':<15} {'Max error':<15} {'Status'}")
    print("-" * 70)

    max_data = {}
    all_match = True

    for i, name in enumerate(OUTPUT_NAMES):
        max_signal = load_max_wav(max_files[name])
        if max_signal.ndim > 1:
            max_signal = max_signal[:, 0]

        max_data[name] = max_signal
        py_signal = py_outputs[i]

        # Compare — may need to trim to shorter length
        min_len = min(len(max_signal), len(py_signal))
        max_err = np.max(np.abs(max_signal[:min_len] - py_signal[:min_len]))
        len_diff = abs(len(max_signal) - len(py_signal))

        status = "MATCH" if max_err < 1e-4 and len_diff == 0 else "DIFF"
        if max_err >= 1e-4 or len_diff > 0:
            all_match = False

        print(f"{name:<15} {len(max_signal):<15} {len(py_signal):<15} {max_err:<15.6e} {status}")

        if len_diff > 0:
            print(f"  WARNING: length mismatch by {len_diff} samples")

    # Plot comparison
    t = np.arange(num_samples) / sample_rate

    fig, axes = plt.subplots(len(OUTPUT_NAMES), 1, figsize=(16, 14), sharex=True)
    fig.suptitle("Attack Detector: Max (orange) vs Python (blue)", fontsize=14)

    for i, name in enumerate(OUTPUT_NAMES):
        py_signal = py_outputs[i]
        max_signal = max_data[name]
        min_len = min(len(max_signal), len(py_signal))

        t_plot = np.arange(min_len) / sample_rate
        axes[i].plot(t_plot, py_signal[:min_len], 'b-', linewidth=0.5, alpha=0.7, label='Python')
        axes[i].plot(t_plot, max_signal[:min_len], color='orange', linewidth=0.5, alpha=0.7, label='Max')
        axes[i].set_ylabel(name)
        axes[i].legend(loc='upper right', fontsize=8)
        axes[i].grid(True, alpha=0.3)

        # Show error in title
        max_err = np.max(np.abs(max_signal[:min_len] - py_signal[:min_len]))
        axes[i].set_title(f"{name} — max error: {max_err:.6e}", fontsize=10)

    axes[-1].set_xlabel('Time (s)')
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.subplots_adjust(hspace=0.4)

    output_path = os.path.join(os.path.dirname(__file__), 'compare_max_python.png')
    plt.savefig(output_path, dpi=150)
    print(f"\nPlot saved to {output_path}")
    plt.show()

    print("\n" + "=" * 60)
    if all_match:
        print("All outputs MATCH (max error < 1e-4)")
    else:
        print("Some outputs DIFFER — check plot for details")


if __name__ == "__main__":
    run_comparison()
