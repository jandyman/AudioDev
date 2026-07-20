"""
Example test demonstrating the audio graph system with both Faust and C++ processors.
"""
import sys
import os
import numpy as np
import matplotlib.pyplot as plt

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../build'))

from python import AudioGraph, FaustProcessor, CppProcessor


def test_faust_processor():
    """Test Faust gain processor."""
    print("\n=== Testing Faust Processor ===")

    # Create Faust processor
    faust_gain = FaustProcessor("../faust_modules/gain.dsp", "gain_test")

    # Initialize
    sample_rate = 44100
    faust_gain.init(sample_rate)

    print(f"Faust processor initialized")
    print(f"  Inputs: {faust_gain.get_num_inputs()}")
    print(f"  Outputs: {faust_gain.get_num_outputs()}")

    # Generate test signal
    duration = 0.1  # seconds
    t = np.linspace(0, duration, int(sample_rate * duration))
    test_signal = np.sin(2 * np.pi * 440 * t)  # 440 Hz sine wave

    # Set gain parameter
    faust_gain.set_param("gain", 0.5)
    print(f"  Gain set to: 0.5")

    # Process
    output = faust_gain.process([test_signal])

    # Verify
    expected = test_signal * 0.5
    np.testing.assert_allclose(output[0], expected, rtol=1e-5)
    print("  ✓ Output matches expected (gain applied correctly)")


def test_cpp_processor():
    """Test C++ example processor."""
    print("\n=== Testing C++ Processor ===")

    try:
        # Import the compiled C++ module
        from pybind_example_processor import ExampleProcessor

        # Wrap in our CppProcessor interface
        cpp_module = ExampleProcessor()
        cpp_gain = CppProcessor(cpp_module)

        # Initialize
        sample_rate = 44100
        cpp_gain.init(sample_rate)

        print(f"C++ processor initialized")
        print(f"  Inputs: {cpp_gain.get_num_inputs()}")
        print(f"  Outputs: {cpp_gain.get_num_outputs()}")
        print(f"  Parameters: {cpp_module.get_param_names()}")

        # Generate test signal
        duration = 0.1
        t = np.linspace(0, duration, int(sample_rate * duration))
        test_signal = np.sin(2 * np.pi * 440 * t)

        # Set gain
        cpp_gain.set_param("gain", 0.75)
        print(f"  Gain set to: {cpp_gain.get_param('gain')}")

        # Process
        output = cpp_gain.process([test_signal])

        # Verify
        expected = test_signal * 0.75
        np.testing.assert_allclose(output[0], expected, rtol=1e-5)
        print("  ✓ Output matches expected (gain applied correctly)")

    except ImportError as e:
        print(f"  ⚠ C++ module not built yet: {e}")
        print("  To build: cd build && make -f audio.make TARGET=example_processor")


def test_graph_serial():
    """Test serial processing through a graph."""
    print("\n=== Testing Serial Graph ===")

    try:
        from pybind_example_processor import ExampleProcessor

        # Create graph
        sample_rate = 44100
        graph = AudioGraph(sample_rate)

        # Add two C++ gain processors in series with names
        cpp1 = CppProcessor(ExampleProcessor())
        cpp2 = CppProcessor(ExampleProcessor())

        graph.add_processor("gain1", cpp1)
        graph.add_processor("gain2", cpp2)

        # Set gains using named access
        graph.processors["gain1"].set_param("gain", 0.5)
        graph.processors["gain2"].set_param("gain", 0.8)

        print(f"Graph created with 2 processors")
        print(f"  gain1: 0.5")
        print(f"  gain2: 0.8")
        print(f"  Expected total gain: 0.4")

        # Generate test signal
        duration = 0.1
        t = np.linspace(0, duration, int(sample_rate * duration))
        test_signal = np.sin(2 * np.pi * 440 * t)

        # Process through graph
        output = graph.process_serial(test_signal)

        # Verify (0.5 * 0.8 = 0.4)
        expected = test_signal * 0.4
        np.testing.assert_allclose(output, expected, rtol=1e-5)
        print("  ✓ Serial processing correct (0.5 × 0.8 = 0.4)")

    except ImportError:
        print("  ⚠ C++ module not built - skipping graph test")


def visualize_example():
    """Visualize signal processing."""
    print("\n=== Visualization Example ===")

    try:
        from pybind_example_processor import ExampleProcessor

        # Create graph with capture mode for visualization
        sample_rate = 44100
        graph = AudioGraph(sample_rate, capture_intermediates=True)

        # Add multiple gain stages
        gains = [0.9, 0.7, 0.5, 0.3]
        for i, gain in enumerate(gains):
            proc = CppProcessor(ExampleProcessor())
            graph.add_processor(f"gain{i+1}", proc)
            graph.processors[f"gain{i+1}"].set_param("gain", gain)

        # Generate test signal with some complexity
        duration = 0.01
        t = np.linspace(0, duration, int(sample_rate * duration))
        test_signal = (
            np.sin(2 * np.pi * 440 * t) +
            0.5 * np.sin(2 * np.pi * 880 * t) +
            0.1 * np.random.randn(len(t))
        )

        # Process through graph
        output = graph.process_serial(test_signal)

        # Get all intermediate signals
        all_signals = graph.get_all_captured_signals()

        # Plot
        num_plots = len(all_signals) + 2  # +2 for input and output
        fig, axes = plt.subplots(num_plots, 1, figsize=(10, 2 * num_plots))

        # Input signal
        axes[0].plot(t * 1000, test_signal, 'b-', linewidth=0.5)
        axes[0].set_title('Input Signal')
        axes[0].set_ylabel('Amplitude')
        axes[0].grid(True, alpha=0.3)

        # Intermediate signals
        for i, (name, channels) in enumerate(all_signals.items(), start=1):
            gain_val = graph.processors[name].get_param("gain")
            axes[i].plot(t * 1000, channels[0], 'g-', linewidth=0.5)
            axes[i].set_title(f'{name} (gain = {gain_val})')
            axes[i].set_ylabel('Amplitude')
            axes[i].grid(True, alpha=0.3)

        # Final output
        axes[-1].plot(t * 1000, output, 'r-', linewidth=0.5)
        axes[-1].set_title('Final Output')
        axes[-1].set_xlabel('Time (ms)')
        axes[-1].set_ylabel('Amplitude')
        axes[-1].grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig('test_output.png', dpi=150)
        print("  ✓ Visualization saved to test_output.png")
        print(f"  ✓ Captured {len(all_signals)} intermediate signals")

    except ImportError:
        print("  ⚠ C++ module not built - skipping visualization")


if __name__ == "__main__":
    print("Audio Graph Python - Example Tests")
    print("=" * 50)

    test_faust_processor()
    test_cpp_processor()
    test_graph_serial()
    visualize_example()

    print("\n" + "=" * 50)
    print("All tests completed!")
