"""
Test capture mode and chunked processing.

Demonstrates:
- Intermediate signal capture
- Chunked processing for state management testing
- Visualization of signal flow through graph
"""
import sys
import os
import numpy as np
import matplotlib.pyplot as plt

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../build'))

from python import AudioGraph, CppProcessor


def test_capture_mode():
    """Test that capture mode records all intermediate signals."""
    print("\n=== Testing Capture Mode ===")

    try:
        from pybind_example_processor import ExampleProcessor

        # Create graph WITH capture enabled
        sample_rate = 44100
        graph = AudioGraph(sample_rate, capture_intermediates=True)

        # Add three gain processors in series
        gain1 = CppProcessor(ExampleProcessor())
        gain2 = CppProcessor(ExampleProcessor())
        gain3 = CppProcessor(ExampleProcessor())

        graph.add_processor("gain1", gain1)
        graph.add_processor("gain2", gain2)
        graph.add_processor("gain3", gain3)

        # Set gains
        graph.processors["gain1"].set_param("gain", 0.5)
        graph.processors["gain2"].set_param("gain", 0.8)
        graph.processors["gain3"].set_param("gain", 0.9)

        print(f"Graph created with 3 processors:")
        print(f"  gain1: 0.5")
        print(f"  gain2: 0.8")
        print(f"  gain3: 0.9")
        print(f"  Expected final gain: {0.5 * 0.8 * 0.9}")

        # Generate test signal
        duration = 0.1
        t = np.linspace(0, duration, int(sample_rate * duration))
        test_signal = np.sin(2 * np.pi * 440 * t)

        # Process
        output = graph.process_serial(test_signal)

        # Get all intermediate signals
        all_signals = graph.get_all_captured_signals()

        print(f"\nCaptured {len(all_signals)} intermediate signals:")
        for name, channels in all_signals.items():
            print(f"  {name}: {len(channels)} channel(s), "
                  f"{len(channels[0])} samples")

        # Verify each stage
        gain1_out = graph.get_captured_signal("gain1", 0)
        gain2_out = graph.get_captured_signal("gain2", 0)
        gain3_out = graph.get_captured_signal("gain3", 0)

        np.testing.assert_allclose(gain1_out, test_signal * 0.5, rtol=1e-5)
        np.testing.assert_allclose(gain2_out, test_signal * 0.5 * 0.8, rtol=1e-5)
        np.testing.assert_allclose(gain3_out, test_signal * 0.5 * 0.8 * 0.9, rtol=1e-5)

        print("  ✓ All intermediate signals match expected values")

    except ImportError as e:
        print(f"  ⚠ C++ module not built: {e}")


def test_chunked_processing():
    """Test that chunked processing produces same results as full-buffer."""
    print("\n=== Testing Chunked Processing ===")

    try:
        from pybind_example_processor import ExampleProcessor

        sample_rate = 44100
        duration = 1.0  # Longer signal to test multiple chunks

        # Generate test signal
        t = np.linspace(0, duration, int(sample_rate * duration))
        test_signal = np.sin(2 * np.pi * 440 * t) + 0.5 * np.sin(2 * np.pi * 880 * t)

        # Create two identical graphs
        graph_full = AudioGraph(sample_rate, capture_intermediates=False)
        graph_chunked = AudioGraph(sample_rate, capture_intermediates=False)

        # Add same processors to both
        for graph in [graph_full, graph_chunked]:
            proc1 = CppProcessor(ExampleProcessor())
            proc2 = CppProcessor(ExampleProcessor())
            graph.add_processor("gain1", proc1)
            graph.add_processor("gain2", proc2)
            graph.processors["gain1"].set_param("gain", 0.6)
            graph.processors["gain2"].set_param("gain", 0.75)

        print(f"Testing with {len(test_signal)} samples")
        print(f"  Full buffer: process all at once")
        print(f"  Chunked: process in 512-sample chunks")

        # Process both ways
        output_full = graph_full.process_serial(test_signal)
        output_chunked = graph_chunked.process_serial(test_signal, chunk_size=512)

        # Verify they match
        np.testing.assert_allclose(output_chunked, output_full, rtol=1e-6)

        print(f"  ✓ Chunked output matches full-buffer output")
        print(f"  ✓ State management working correctly")

        # Try different chunk sizes
        chunk_sizes = [128, 256, 1024, 2048]
        for chunk_size in chunk_sizes:
            graph_test = AudioGraph(sample_rate, capture_intermediates=False)
            proc1 = CppProcessor(ExampleProcessor())
            proc2 = CppProcessor(ExampleProcessor())
            graph_test.add_processor("gain1", proc1)
            graph_test.add_processor("gain2", proc2)
            graph_test.processors["gain1"].set_param("gain", 0.6)
            graph_test.processors["gain2"].set_param("gain", 0.75)

            output_test = graph_test.process_serial(test_signal, chunk_size=chunk_size)
            np.testing.assert_allclose(output_test, output_full, rtol=1e-6)

        print(f"  ✓ Verified with chunk sizes: {chunk_sizes}")

    except ImportError as e:
        print(f"  ⚠ C++ module not built: {e}")


def test_capture_with_chunking():
    """Test that capture mode works correctly with chunked processing."""
    print("\n=== Testing Capture + Chunking ===")

    try:
        from pybind_example_processor import ExampleProcessor

        sample_rate = 44100
        duration = 0.5

        # Generate test signal
        t = np.linspace(0, duration, int(sample_rate * duration))
        test_signal = np.sin(2 * np.pi * 440 * t)

        # Create graph with capture + chunking
        graph = AudioGraph(sample_rate, capture_intermediates=True)
        proc1 = CppProcessor(ExampleProcessor())
        proc2 = CppProcessor(ExampleProcessor())
        graph.add_processor("gain1", proc1)
        graph.add_processor("gain2", proc2)
        graph.processors["gain1"].set_param("gain", 0.7)
        graph.processors["gain2"].set_param("gain", 0.85)

        # Process in chunks
        chunk_size = 1024
        output = graph.process_serial(test_signal, chunk_size=chunk_size)

        print(f"Processed {len(test_signal)} samples in {chunk_size}-sample chunks")

        # Get captured signals (should be concatenated across chunks)
        gain1_out = graph.get_captured_signal("gain1", 0)
        gain2_out = graph.get_captured_signal("gain2", 0)

        # Verify lengths match
        assert len(gain1_out) == len(test_signal)
        assert len(gain2_out) == len(test_signal)
        assert len(output) == len(test_signal)

        print(f"  ✓ Captured signals have correct length: {len(gain1_out)}")

        # Verify values
        np.testing.assert_allclose(gain1_out, test_signal * 0.7, rtol=1e-5)
        np.testing.assert_allclose(gain2_out, test_signal * 0.7 * 0.85, rtol=1e-5)

        print(f"  ✓ Captured signals match expected values")

    except ImportError as e:
        print(f"  ⚠ C++ module not built: {e}")


def visualize_signal_flow():
    """Visualize signal flow through graph with captured intermediates."""
    print("\n=== Visualization: Signal Flow ===")

    try:
        from pybind_example_processor import ExampleProcessor

        # Create graph with capture
        sample_rate = 44100
        graph = AudioGraph(sample_rate, capture_intermediates=True)

        # Add processors with different gains
        for i, gain_val in enumerate([0.8, 0.6, 0.4, 0.2], start=1):
            proc = CppProcessor(ExampleProcessor())
            graph.add_processor(f"gain{i}", proc)
            graph.processors[f"gain{i}"].set_param("gain", gain_val)

        # Generate complex test signal
        duration = 0.02  # Short for visualization
        t = np.linspace(0, duration, int(sample_rate * duration))
        test_signal = (
            np.sin(2 * np.pi * 440 * t) +
            0.5 * np.sin(2 * np.pi * 880 * t) +
            0.3 * np.sin(2 * np.pi * 1320 * t)
        )

        # Process
        output = graph.process_serial(test_signal)

        # Get all signals
        all_signals = graph.get_all_captured_signals()

        # Plot
        num_plots = len(all_signals) + 2  # +2 for input and output
        fig, axes = plt.subplots(num_plots, 1, figsize=(12, 2 * num_plots))

        time_ms = t * 1000

        # Input
        axes[0].plot(time_ms, test_signal, 'b-', linewidth=0.8)
        axes[0].set_title('Input Signal', fontweight='bold')
        axes[0].set_ylabel('Amplitude')
        axes[0].grid(True, alpha=0.3)
        axes[0].set_xlim([0, time_ms[-1]])

        # Intermediate signals
        for i, (name, channels) in enumerate(all_signals.items(), start=1):
            gain_val = graph.processors[name].get_param("gain")
            axes[i].plot(time_ms, channels[0], 'g-', linewidth=0.8)
            axes[i].set_title(f'{name} (gain={gain_val:.1f})', fontweight='bold')
            axes[i].set_ylabel('Amplitude')
            axes[i].grid(True, alpha=0.3)
            axes[i].set_xlim([0, time_ms[-1]])

        # Output
        axes[-1].plot(time_ms, output, 'r-', linewidth=0.8)
        axes[-1].set_title('Final Output', fontweight='bold')
        axes[-1].set_xlabel('Time (ms)')
        axes[-1].set_ylabel('Amplitude')
        axes[-1].grid(True, alpha=0.3)
        axes[-1].set_xlim([0, time_ms[-1]])

        plt.tight_layout()
        plt.savefig('signal_flow.png', dpi=150, bbox_inches='tight')
        print("  ✓ Visualization saved to signal_flow.png")

        plt.close()

    except ImportError as e:
        print(f"  ⚠ C++ module not built: {e}")


def test_named_processor_access():
    """Test that we can access processors by name."""
    print("\n=== Testing Named Processor Access ===")

    try:
        from pybind_example_processor import ExampleProcessor

        sample_rate = 44100
        graph = AudioGraph(sample_rate)

        # Add processors
        graph.add_processor("input_gain", CppProcessor(ExampleProcessor()))
        graph.add_processor("compressor", CppProcessor(ExampleProcessor()))
        graph.add_processor("output_gain", CppProcessor(ExampleProcessor()))

        print(f"Added processors: {list(graph.processors.keys())}")

        # Access by name
        graph.processors["input_gain"].set_param("gain", 0.5)
        graph.processors["compressor"].set_param("gain", 0.8)
        graph.processors["output_gain"].set_param("gain", 1.2)

        # Read back
        input_gain = graph.processors["input_gain"].get_param("gain")
        comp_gain = graph.processors["compressor"].get_param("gain")
        output_gain = graph.processors["output_gain"].get_param("gain")

        print(f"  input_gain: {input_gain}")
        print(f"  compressor: {comp_gain}")
        print(f"  output_gain: {output_gain}")

        assert input_gain == 0.5
        assert comp_gain == 0.8
        assert output_gain == 1.2

        print("  ✓ Named processor access working correctly")

    except ImportError as e:
        print(f"  ⚠ C++ module not built: {e}")


if __name__ == "__main__":
    print("Audio Graph Python - Capture Mode Tests")
    print("=" * 60)

    test_capture_mode()
    test_chunked_processing()
    test_capture_with_chunking()
    test_named_processor_access()
    visualize_signal_flow()

    print("\n" + "=" * 60)
    print("All capture tests completed!")
