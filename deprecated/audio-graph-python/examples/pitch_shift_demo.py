"""
Test pitch shifting using dual tap delay with ramping delays.

Pitch shifting by reading from a delay line at a different rate than writing:
- For pitch ratio R (where R < 1 = lower pitch):
- Read speed relative to write = R
- Delay increment per sample = (1 - R)

Tap 1: Down a fourth (ratio 3/4 = 0.75) -> delay increment = 0.25 samples/sample
Tap 2: Down an octave (ratio 1/2 = 0.5) -> delay increment = 0.5 samples/sample
"""
import sys
import os
import numpy as np
import scipy.io.wavfile as wav

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build'))

from python import FaustProcessor


def test_pitch_shift():
    print("Pitch Shift Test using Dual Tap Delay")
    print("=" * 60)

    # Load input audio
    input_path = os.path.join(os.path.dirname(__file__), '..', '..', 'test_audio', 'Bass Notes.wav')
    sample_rate, audio_data = wav.read(input_path)

    # Convert to float [-1, 1]
    if audio_data.dtype == np.int16:
        audio_in = audio_data.astype(np.float64) / 32768.0
    elif audio_data.dtype == np.int32:
        audio_in = audio_data.astype(np.float64) / 2147483648.0
    else:
        audio_in = audio_data.astype(np.float64)

    num_samples = len(audio_in)
    duration = num_samples / sample_rate

    print(f"\nInput: {os.path.basename(input_path)}")
    print(f"  Sample rate: {sample_rate} Hz")
    print(f"  Duration: {duration:.2f} seconds")
    print(f"  Samples: {num_samples}")

    # Create ramping delay signals
    # Tap 1: Down a fourth (ratio 0.75) -> delay increment = 0.25 samples/sample
    # Tap 2: Down an octave (ratio 0.5) -> delay increment = 0.5 samples/sample

    pitch_ratio_1 = 0.75  # Down a fourth
    pitch_ratio_2 = 0.5   # Down an octave

    delay_increment_1 = 1.0 - pitch_ratio_1  # 0.25 samples/sample
    delay_increment_2 = 1.0 - pitch_ratio_2  # 0.5 samples/sample

    # Build delay ramps (in samples, then convert to ms)
    sample_indices = np.arange(num_samples, dtype=np.float64)
    delay1_samples = sample_indices * delay_increment_1
    delay2_samples = sample_indices * delay_increment_2

    # Convert to milliseconds
    delay1_ms = delay1_samples * 1000.0 / sample_rate
    delay2_ms = delay2_samples * 1000.0 / sample_rate

    print(f"\nPitch shift settings:")
    print(f"  Tap 1: Down a fourth (ratio {pitch_ratio_1})")
    print(f"    Delay increment: {delay_increment_1} samples/sample")
    print(f"    Max delay: {delay1_samples[-1]:.0f} samples ({delay1_ms[-1]:.2f} ms)")
    print(f"  Tap 2: Down an octave (ratio {pitch_ratio_2})")
    print(f"    Delay increment: {delay_increment_2} samples/sample")
    print(f"    Max delay: {delay2_samples[-1]:.0f} samples ({delay2_ms[-1]:.2f} ms)")

    # Create Faust processor
    dsp_path = os.path.join(os.path.dirname(__file__), '..', '..', 'dsp_library', 'faust', 'dual_tap_delay.dsp')
    processor = FaustProcessor(dsp_path, name="dual_tap_delay")
    processor.init(sample_rate)

    print(f"\nProcessing...")
    print(f"  Inputs: {processor.get_num_inputs()}, Outputs: {processor.get_num_outputs()}")

    # Process: 3 inputs (audio, delay1_ms, delay2_ms) -> 2 outputs (tap1, tap2)
    inputs = [audio_in, delay1_ms, delay2_ms]
    outputs = processor.process(inputs)

    tap1_output = outputs[0]
    tap2_output = outputs[1]

    print(f"  Tap 1 output range: [{np.min(tap1_output):.4f}, {np.max(tap1_output):.4f}]")
    print(f"  Tap 2 output range: [{np.min(tap2_output):.4f}, {np.max(tap2_output):.4f}]")

    # Create output directory
    output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'test_audio_out')
    os.makedirs(output_dir, exist_ok=True)

    # Save outputs as WAV files
    def save_wav(filename, data, sr):
        # Convert to int16
        data_int16 = np.clip(data * 32767, -32768, 32767).astype(np.int16)
        filepath = os.path.join(output_dir, filename)
        wav.write(filepath, sr, data_int16)
        return filepath

    out1_path = save_wav('pitch_shift_fourth_down.wav', tap1_output, sample_rate)
    out2_path = save_wav('pitch_shift_octave_down.wav', tap2_output, sample_rate)

    print(f"\nOutputs saved:")
    print(f"  {out1_path}")
    print(f"  {out2_path}")

    print("\n" + "=" * 60)
    print("Pitch Shift Test Complete")
    print("\nNote: This is raw pitch shifting without loop crossfading.")
    print("Latency will grow as the delay ramp increases until the buffer limit is reached.")


if __name__ == "__main__":
    test_pitch_shift()
