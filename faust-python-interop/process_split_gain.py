"""
Process audio through Faust split_gain module using chunk-based spooling.

This script demonstrates:
1. Reading audio from file
2. Processing through Faust in chunks (general-purpose spooling)
3. Accumulating multiple outputs
4. Plotting results
"""

import numpy as np
import matplotlib.pyplot as plt
import dawdreamer as daw
import soundfile as sf


def process_faust_chunked(faust_dsp_path, input_audio, sample_rate, chunk_size=1024, num_outputs=2):
    """
    Process audio through a Faust module in explicit chunks.

    This processes the audio chunk-by-chunk in Python, which is essential for:
    - Debugging state continuity across chunk boundaries
    - Matching the pattern needed for custom C++ blocks
    - Simulating real-time buffer processing

    Note: With Faust/DawDreamer, state is preserved within the processor between chunks.

    Args:
        faust_dsp_path: Path to .dsp file
        input_audio: Input audio as numpy array (mono or first channel)
        sample_rate: Sample rate in Hz
        chunk_size: Number of samples per chunk
        num_outputs: Number of output channels expected from Faust module

    Returns:
        List of numpy arrays, one per output channel
    """
    # Setup engine - buffer size matches chunk size
    engine = daw.RenderEngine(sample_rate, chunk_size)

    # Load Faust DSP
    print(f"Loading Faust DSP: {faust_dsp_path}")
    with open(faust_dsp_path, "r") as f:
        dsp_code = f.read()

    # Create Faust processor once (state persists across chunks)
    faust_proc = engine.make_faust_processor("faust_module")
    faust_proc.set_dsp_string(dsp_code)

    # Initialize output buffers
    output_buffers = [[] for _ in range(num_outputs)]

    # Process in chunks
    num_samples = len(input_audio)
    num_chunks = int(np.ceil(num_samples / chunk_size))
    duration = num_samples / sample_rate

    print(f"Processing {num_samples} samples ({duration:.2f}s) in {num_chunks} chunks of {chunk_size}...")

    for chunk_idx in range(num_chunks):
        # Extract chunk from input
        start_idx = chunk_idx * chunk_size
        end_idx = min(start_idx + chunk_size, num_samples)
        chunk = input_audio[start_idx:end_idx]
        actual_chunk_size = len(chunk)

        # Pad last chunk if necessary
        if len(chunk) < chunk_size:
            chunk = np.pad(chunk, (0, chunk_size - len(chunk)), mode='constant')

        # Reshape for dawdreamer: (channels, samples)
        chunk_input = chunk.reshape(1, -1)

        # Create playback processor for this chunk
        playback = engine.make_playback_processor(f"input_{chunk_idx}", chunk_input)

        # Build graph: playback -> faust_proc
        # Note: faust_proc maintains state across chunks
        graph = [
            (playback, []),
            (faust_proc, [f"input_{chunk_idx}"])
        ]

        # Render this chunk
        engine.load_graph(graph)
        chunk_duration = chunk_size / sample_rate
        engine.render(chunk_duration)

        # Get outputs for this chunk
        faust_output = faust_proc.get_audio()  # Shape: (num_outputs, chunk_size)

        # Accumulate outputs (excluding padding)
        for out_idx in range(num_outputs):
            output_buffers[out_idx].append(faust_output[out_idx, :actual_chunk_size])

        if (chunk_idx + 1) % 50 == 0 or (chunk_idx + 1) == num_chunks:
            print(f"  Processed chunk {chunk_idx + 1}/{num_chunks}")

    # Concatenate all chunks
    output_arrays = [np.concatenate(buf) for buf in output_buffers]

    print(f"✅ Processing complete. Output shapes: {[arr.shape for arr in output_arrays]}")

    return output_arrays


def main():
    """Process bass guitar audio through split_gain module."""

    # Read audio file
    audio_path = "../Bass Guitar Test Files/Bass Notes.wav"
    print(f"Reading audio file: {audio_path}")
    audio_data, sample_rate = sf.read(audio_path)

    # Use first channel if stereo
    if audio_data.ndim > 1:
        audio_data = audio_data[:, 0]

    print(f"  Sample rate: {sample_rate} Hz")
    print(f"  Duration: {len(audio_data) / sample_rate:.2f} seconds")
    print(f"  Samples: {len(audio_data)}")

    # Process through Faust module
    faust_dsp = "faust/split_gain.dsp"
    outputs = process_faust_chunked(
        faust_dsp_path=faust_dsp,
        input_audio=audio_data,
        sample_rate=sample_rate,
        chunk_size=1024,
        num_outputs=2
    )

    output1, output2 = outputs

    # Verify outputs
    print(f"\nOutput verification:")
    print(f"  Output 1 (pass-through) max: {np.max(np.abs(output1)):.4f}")
    print(f"  Output 2 (0.5 gain) max: {np.max(np.abs(output2)):.4f}")
    print(f"  Input max: {np.max(np.abs(audio_data)):.4f}")
    print(f"  Output2/Output1 ratio: {np.max(np.abs(output2)) / np.max(np.abs(output1)):.4f} (should be ~0.5)")

    # Plot results
    fig, axes = plt.subplots(3, 1, figsize=(14, 8))
    fig.suptitle("Faust split_gain Module - Chunked Processing")

    time = np.arange(len(audio_data)) / sample_rate
    plot_samples = len(audio_data)  # Plot entire file

    # Plot input
    axes[0].plot(time[:plot_samples], audio_data[:plot_samples], 'b-', alpha=0.7)
    axes[0].set_ylabel('Input\nAmplitude')
    axes[0].grid(True, alpha=0.3)
    axes[0].set_title('Input Signal')

    # Plot output 1 (pass-through)
    axes[1].plot(time[:plot_samples], output1[:plot_samples], 'g-', alpha=0.7)
    axes[1].set_ylabel('Output 1\nAmplitude')
    axes[1].grid(True, alpha=0.3)
    axes[1].set_title('Output 1: Pass-through (identity)')

    # Plot output 2 (0.5 gain)
    axes[2].plot(time[:plot_samples], output2[:plot_samples], 'r-', alpha=0.7)
    axes[2].set_ylabel('Output 2\nAmplitude')
    axes[2].set_xlabel('Time (s)')
    axes[2].grid(True, alpha=0.3)
    axes[2].set_title('Output 2: 0.5 gain')

    plt.tight_layout()
    output_path = 'split_gain_test.png'
    plt.savefig(output_path)
    print(f"\n✅ Plot saved to {output_path}")
    # plt.show()  # Commented out for non-interactive use


if __name__ == "__main__":
    print("Faust split_gain Chunked Processing Test")
    print("=" * 60)
    main()
    print("\n✅ All processing complete!")
