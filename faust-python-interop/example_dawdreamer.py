"""
Example: Using DawDreamer to compile and test Faust code

This script demonstrates:
1. Loading a Faust .dsp file with DawDreamer
2. Setting parameters
3. Processing audio
4. Analyzing the results
"""

import numpy as np
import matplotlib.pyplot as plt
import dawdreamer as daw


def demo_faust_gain():
    """Demo the simple_gain.dsp file with DawDreamer."""

    # Setup audio engine
    SAMPLE_RATE = 44100
    BUFFER_SIZE = 512
    DURATION = 1.0  # seconds

    print("Creating DawDreamer engine...")
    engine = daw.RenderEngine(SAMPLE_RATE, BUFFER_SIZE)

    # Load Faust DSP file
    print("Loading Faust DSP file: faust/simple_gain.dsp")
    with open("faust/simple_gain.dsp", "r") as f:
        dsp_code = f.read()

    # Create Faust processor
    faust_processor = engine.make_faust_processor("gain_test")
    faust_processor.set_dsp_string(dsp_code)

    # Check what parameters are available
    print(f"\nAvailable parameters: {faust_processor.get_parameters_description()}")

    # Generate test signal (sine wave at 440 Hz)
    num_samples = int(SAMPLE_RATE * DURATION)
    t = np.linspace(0, DURATION, num_samples)
    test_signal = np.sin(2 * np.pi * 440 * t).reshape(1, -1)  # Shape: (1, num_samples)

    # Create a playback processor to provide input
    playback = engine.make_playback_processor("input", test_signal)

    # Test with different gain values
    gain_values = [0.25, 0.5, 0.75, 1.0]

    fig, axes = plt.subplots(len(gain_values), 1, figsize=(10, 8))
    fig.suptitle("Faust Gain Processor Test")

    for idx, gain in enumerate(gain_values):
        print(f"\nTesting with gain = {gain}")

        # Set the gain parameter (use index 0 - more reliable than string path)
        faust_processor.set_parameter(0, gain)

        # Build the graph: playback -> faust_processor
        graph = [
            (playback, []),
            (faust_processor, ["input"])
        ]

        # Load and render
        engine.load_graph(graph)
        engine.render(DURATION)

        # Get output from the faust processor
        output = faust_processor.get_audio()[0]  # Get first channel

        # Verify gain is applied correctly
        expected_max = gain * np.max(np.abs(test_signal))
        actual_max = np.max(np.abs(output))
        print(f"  Expected max amplitude: {expected_max:.4f}")
        print(f"  Actual max amplitude: {actual_max:.4f}")
        print(f"  Difference: {abs(expected_max - actual_max):.6f}")

        # Plot results
        ax = axes[idx]
        time_plot = t[:1000]  # Plot first 1000 samples
        ax.plot(time_plot, test_signal[0, :1000], 'b-', alpha=0.5, label='Input')
        ax.plot(time_plot, output[:1000], 'r-', alpha=0.7, label=f'Output (gain={gain})')
        ax.set_ylabel('Amplitude')
        ax.legend()
        ax.grid(True, alpha=0.3)

        if idx == len(gain_values) - 1:
            ax.set_xlabel('Time (s)')

    plt.tight_layout()
    plt.savefig('faust_gain_test.png')
    print("\n✅ Test complete! Plot saved to faust_gain_test.png")
    plt.show()


def inspect_faust_code():
    """Inspect what Faust generates from the DSP code."""

    print("\n" + "="*60)
    print("FAUST CODE INSPECTION")
    print("="*60)

    # Show the Faust source
    print("\nFaust DSP Source (simple_gain.dsp):")
    print("-" * 40)
    with open("faust/simple_gain.dsp", "r") as f:
        print(f.read())

    # Create a processor to see what it generates
    engine = daw.RenderEngine(44100, 512)
    with open("faust/simple_gain.dsp", "r") as f:
        dsp_code = f.read()

    faust_processor = engine.make_faust_processor("inspector")
    faust_processor.set_dsp_string(dsp_code)

    print("\nGenerated Parameters:")
    print("-" * 40)
    params = faust_processor.get_parameters_description()
    for param in params:
        print(f"  {param}")

    print("\n" + "="*60)


if __name__ == "__main__":
    print("Faust-Python Interop Test")
    print("="*60)

    # First inspect the Faust code
    inspect_faust_code()

    # Then run the actual demo
    demo_faust_gain()

    print("\n✅ All tests complete!")
