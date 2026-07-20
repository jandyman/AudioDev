"""
Example: Cascading two audio processors programmatically.

This demonstrates connecting a C++ processor and a Faust processor in series:
  Input → C++ Gain (0.5) → Faust Gain (0.8) → Output

Expected result: Output = Input * 0.5 * 0.8 = Input * 0.4
"""
import sys
import os
import numpy as np
import matplotlib.pyplot as plt

# Add modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build'))

from python import CppProcessor, FaustProcessor, AudioGraph

try:
    from pybind_example_processor import ExampleProcessor
except ImportError:
    print("Error: C++ module not built.")
    print("Build with: cd build && make -f audio.make TARGET=example_processor")
    sys.exit(1)

# Path to Faust DSP file
FAUST_DSP_PATH = os.path.join(os.path.dirname(__file__), '..', '..',
                              'dsp_library', 'faust', 'gain.dsp')
if not os.path.exists(FAUST_DSP_PATH):
    print(f"Error: Faust DSP not found at {FAUST_DSP_PATH}")
    sys.exit(1)


def main():
    print("Cascading C++ and Faust Processors - Programmatic Example")
    print("=" * 60)

    # Create audio graph
    sample_rate = 44100
    graph = AudioGraph(sample_rate, capture_intermediates=True)

    # Create C++ gain processor
    cpp_gain_instance = ExampleProcessor()
    cpp_gain = CppProcessor(cpp_gain_instance)

    # Create Faust gain processor
    faust_gain = FaustProcessor(FAUST_DSP_PATH, name="faust_gain")

    # Add to graph (order matters - this defines the signal flow)
    graph.add_processor("cpp_gain", cpp_gain)
    graph.add_processor("faust_gain", faust_gain)

    # Set parameters using property interface
    graph.processors["cpp_gain"].gain = 0.5
    graph.processors["faust_gain"].gain = 0.8

    print(f"\nGraph Configuration:")
    print(f"  cpp_gain (C++): {graph.processors['cpp_gain'].gain}")
    print(f"  faust_gain (Faust): {graph.processors['faust_gain'].gain}")
    print(f"  Expected total gain: {0.5 * 0.8} (0.5 × 0.8)")

    # Generate test signal
    duration = 0.1  # 100ms
    t = np.linspace(0, duration, int(sample_rate * duration))
    test_signal = np.sin(2 * np.pi * 440 * t)  # 440 Hz sine wave

    print(f"\nTest Signal:")
    print(f"  Frequency: 440 Hz")
    print(f"  Duration: {duration * 1000:.1f} ms")
    print(f"  Samples: {len(test_signal)}")
    print(f"  Max amplitude: {np.max(np.abs(test_signal)):.4f}")

    # Process through cascaded blocks
    print(f"\nProcessing through cascade...")
    output = graph.process_serial(test_signal)

    # Verify result
    expected = test_signal * 0.4
    max_error = np.max(np.abs(output - expected))

    print(f"\nResults:")
    print(f"  Output max amplitude: {np.max(np.abs(output)):.4f}")
    print(f"  Expected max amplitude: {np.max(np.abs(expected)):.4f}")
    print(f"  Max error: {max_error:.2e}")

    if max_error < 1e-5:
        print(f"  ✅ Cascade working correctly!")
    else:
        print(f"  ❌ Unexpected error!")

    # Get intermediate signals
    cpp_gain_output = graph.get_captured_signal("cpp_gain", channel=0)
    faust_gain_output = graph.get_captured_signal("faust_gain", channel=0)

    print(f"\nIntermediate Signals:")
    print(f"  cpp_gain output max: {np.max(np.abs(cpp_gain_output)):.4f} (expected: 0.5)")
    print(f"  faust_gain output max: {np.max(np.abs(faust_gain_output)):.4f} (expected: 0.4)")

    # Visualize
    plot_samples = 200  # Plot first 200 samples
    fig, axes = plt.subplots(4, 1, figsize=(12, 8))
    fig.suptitle("Cascaded C++ and Faust Processors: Input → C++ Gain (0.5) → Faust Gain (0.8) → Output")

    # Input
    axes[0].plot(t[:plot_samples] * 1000, test_signal[:plot_samples], 'b-', linewidth=1.5)
    axes[0].set_ylabel('Input\nAmplitude')
    axes[0].grid(True, alpha=0.3)
    axes[0].set_ylim(-1.1, 1.1)
    axes[0].axhline(y=0, color='k', linewidth=0.5, alpha=0.3)

    # After C++ gain
    axes[1].plot(t[:plot_samples] * 1000, cpp_gain_output[:plot_samples], 'g-', linewidth=1.5)
    axes[1].set_ylabel('After C++ Gain\nAmplitude')
    axes[1].grid(True, alpha=0.3)
    axes[1].set_ylim(-1.1, 1.1)
    axes[1].axhline(y=0, color='k', linewidth=0.5, alpha=0.3)
    axes[1].text(0.02, 0.95, 'C++ gain = 0.5', transform=axes[1].transAxes,
                 verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))

    # After Faust gain
    axes[2].plot(t[:plot_samples] * 1000, faust_gain_output[:plot_samples], 'orange', linewidth=1.5)
    axes[2].set_ylabel('After Faust Gain\nAmplitude')
    axes[2].grid(True, alpha=0.3)
    axes[2].set_ylim(-1.1, 1.1)
    axes[2].axhline(y=0, color='k', linewidth=0.5, alpha=0.3)
    axes[2].text(0.02, 0.95, 'Faust gain = 0.8', transform=axes[2].transAxes,
                 verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.5))

    # Final output
    axes[3].plot(t[:plot_samples] * 1000, output[:plot_samples], 'r-', linewidth=1.5)
    axes[3].set_ylabel('Final Output\nAmplitude')
    axes[3].set_xlabel('Time (ms)')
    axes[3].grid(True, alpha=0.3)
    axes[3].set_ylim(-1.1, 1.1)
    axes[3].axhline(y=0, color='k', linewidth=0.5, alpha=0.3)
    axes[3].text(0.02, 0.95, 'total gain = 0.4', transform=axes[3].transAxes,
                 verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    output_path = 'cascade_example.png'
    plt.savefig(output_path, dpi=150)
    print(f"\n✅ Visualization saved to {output_path}")


if __name__ == "__main__":
    main()
    print("\n" + "=" * 60)
    print("Example complete!")
