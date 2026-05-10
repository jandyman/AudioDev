"""
Pitch Shifter demo — full pipeline end-to-end.

Pipeline (all DSP in Faust/C++, Python is test harness):

  Audio → ZC Detector (Faust)     → zc_impulse     ┐
  Audio → Attack Detector (Faust) → attack_impulse  ┤→ Loop Controller (C++)
                                                     ↓
                              tap1_delay_ms, tap2_delay_ms, gain1, gain2
                                                     ↓
  Audio → Dual Tap Delay (Faust) ──────────────────→ tap1, tap2
                                                     ↓
                              output = tap1 * gain1 + tap2 * gain2

The loop controller and dual tap delay are processed in lockstep chunks
so the delay control signals are applied sample-accurately.
"""
import sys
import os
import numpy as np
import scipy.io.wavfile as wav
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build'))

from build.pybind_faust_zero_crossing_detector import FaustZeroCrossingDetector
from build.pybind_faust_attack_detector import FaustAttackDetector
from build.pybind_loop_controller import LoopController
from build.pybind_faust_dual_tap_delay import FaustDualTapDelay


def run_pitch_shifter_demo(pitch_ratio=0.5):
    print("Pitch Shifter Demo")
    print("=" * 60)
    print(f"Pitch ratio: {pitch_ratio}  ({pitch_ratio_label(pitch_ratio)})")

    input_path = os.path.join(os.path.dirname(__file__), '..', '..', 'test_audio', 'Bass Notes No Gap.wav')
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
    print(f"  Sample rate: {sample_rate} Hz,  Duration: {duration:.2f} s")

    # ---------------------------------------------------------------
    # Stage 1: ZC Detector — full file, no state dependency on pitch
    # ---------------------------------------------------------------
    zc_det = FaustZeroCrossingDetector()
    zc_det.init(sample_rate)
    zc_impulse = zc_det.process([audio_in])[0]
    print(f"\nZC Detector:    {int(np.sum(zc_impulse > 0.5))} qualified zero crossings")

    # ---------------------------------------------------------------
    # Stage 2: Attack Detector — full file
    # ---------------------------------------------------------------
    atk_det = FaustAttackDetector()
    atk_det.init(sample_rate)
    attack_impulse = atk_det.process([audio_in])[0]
    print(f"Attack Det:     {int(np.sum(attack_impulse > 0.5))} attacks detected")

    # ---------------------------------------------------------------
    # Stages 3+4: Loop Controller + Dual Tap Delay — chunked lockstep
    # The delay control signals must be applied sample-accurately to
    # the delay line, so both modules advance together each chunk.
    # ---------------------------------------------------------------
    lc = LoopController()
    lc.init(sample_rate)
    lc.set_param("pitch_ratio", pitch_ratio)

    dtd = FaustDualTapDelay()
    dtd.init(sample_rate)

    chunk = 512
    audio_out    = np.zeros(num_samples)
    latency      = np.zeros(num_samples)
    loop_evts    = np.zeros(num_samples)
    bailout_evts = np.zeros(num_samples)

    print("\nProcessing...")
    for i in range(0, num_samples, chunk):
        end = min(i + chunk, num_samples)

        # Loop Controller: ZC + attack → delay times and gains
        lc_outs = lc.process([
            zc_impulse[i:end].astype(np.float32),
            attack_impulse[i:end].astype(np.float32),
        ])
        tap1_delay_ms = lc_outs[0]
        tap2_delay_ms = lc_outs[1]
        gain1         = lc_outs[2]
        gain2         = lc_outs[3]

        latency[i:end]      = lc_outs[4]
        loop_evts[i:end]    = lc_outs[5]
        bailout_evts[i:end] = lc_outs[7]

        # Dual Tap Delay: audio + delay times → two taps
        dtd_outs = dtd.process([
            audio_in[i:end],
            tap1_delay_ms.astype(np.float64),
            tap2_delay_ms.astype(np.float64),
        ])
        tap1 = dtd_outs[0]
        tap2 = dtd_outs[1]

        # Crossfade mix
        audio_out[i:end] = tap1 * gain1 + tap2 * gain2

    loop_count    = int(np.sum(loop_evts > 0.5))
    bailout_count = int(np.sum(bailout_evts > 0.5))
    print(f"  Loop transitions: {loop_count}")
    print(f"  Bailout events:   {bailout_count}")
    print(f"  Max latency:      {latency.max():.1f} ms")

    # ---------------------------------------------------------------
    # Save output
    # ---------------------------------------------------------------
    output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'test_audio_out')
    os.makedirs(output_dir, exist_ok=True)

    ratio_str = f"{int(round(pitch_ratio * 100))}pct"
    out_name  = f"pitch_shifted_{ratio_str}.wav"
    out_path  = os.path.join(output_dir, out_name)

    peak = np.max(np.abs(audio_out))
    if peak > 0:
        audio_out /= peak * 1.05   # leave a little headroom
    out_int16 = np.clip(audio_out * 32767, -32768, 32767).astype(np.int16)
    wav.write(out_path, sample_rate, out_int16)
    print(f"\nOutput saved: {out_path}")

    # ---------------------------------------------------------------
    # Plot
    # ---------------------------------------------------------------
    t = np.arange(num_samples) / sample_rate
    attack_indices = np.where(attack_impulse > 0.5)[0]
    loop_indices   = np.where(loop_evts > 0.5)[0]

    fig, axes = plt.subplots(3, 1, figsize=(16, 10), sharex=True)
    fig.suptitle(f"Pitch Shifter — {pitch_ratio_label(pitch_ratio)}  ({os.path.basename(input_path)})", fontsize=14)

    # Panel 1: Input vs output waveforms
    axes[0].plot(t, audio_in,  'b-', linewidth=0.3, alpha=0.6, label='Input')
    axes[0].plot(t, audio_out, 'g-', linewidth=0.3, alpha=0.6, label='Output (pitch shifted)')
    axes[0].set_ylabel('Amplitude')
    axes[0].set_title('Input (blue) vs pitch-shifted output (green)')
    axes[0].legend(loc='upper right', fontsize=8)
    axes[0].grid(True, alpha=0.3)
    axes[0].set_xlim(0, t[-1])

    # Panel 2: Latency with events
    axes[1].plot(t, latency, 'b-', linewidth=0.6, label='Latency (active tap)')
    axes[1].axhline(100.0, color='green', linewidth=1.0, linestyle='--', label='Lower threshold (100 ms)')
    axes[1].axhline(200.0, color='red',   linewidth=1.0, linestyle='--', label='Upper threshold (200 ms)')
    for idx in attack_indices:
        axes[1].axvline(t[idx], color='red', linewidth=0.8, alpha=0.4)
    for idx in loop_indices:
        axes[1].axvline(t[idx], color='green', linewidth=0.8, alpha=0.4)
    axes[1].set_ylabel('Delay (ms)')
    axes[1].set_title('Active tap latency — attacks (red), loop transitions (green)')
    axes[1].legend(loc='upper right', fontsize=8)
    axes[1].grid(True, alpha=0.3)

    # Panel 3: Output waveform zoomed to first note
    zoom_end_s = min(duration, 0.5)
    zoom_sl = slice(0, int(zoom_end_s * sample_rate))
    t_zoom_ms = t[zoom_sl] * 1000
    axes[2].plot(t_zoom_ms, audio_in[zoom_sl],  'b-', linewidth=0.8, alpha=0.7, label='Input')
    axes[2].plot(t_zoom_ms, audio_out[zoom_sl], 'g-', linewidth=0.8, alpha=0.7, label='Output')
    for idx in attack_indices:
        if t[idx] < zoom_end_s:
            axes[2].axvline(t[idx] * 1000, color='red', linewidth=1.0, alpha=0.6)
    for idx in loop_indices:
        if t[idx] < zoom_end_s:
            axes[2].axvline(t[idx] * 1000, color='green', linewidth=1.0, alpha=0.6)
    axes[2].set_xlabel('Time (ms)')
    axes[2].set_ylabel('Amplitude')
    axes[2].set_title(f'Zoomed: first {zoom_end_s*1000:.0f} ms')
    axes[2].legend(loc='upper right', fontsize=8)
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.subplots_adjust(hspace=0.35)

    plot_path = os.path.join(output_dir, f"pitch_shifter_{ratio_str}.png")
    plt.savefig(plot_path, dpi=150)
    print(f"Plot saved:    {plot_path}")
    plt.show()

    print("\n" + "=" * 60)
    print("Pitch Shifter Demo Complete")


def pitch_ratio_label(ratio):
    """Human-readable label for common pitch ratios."""
    labels = {
        0.5:   "octave down",
        0.75:  "fourth down",
        0.667: "fifth down",
        0.794: "major third down",
    }
    return labels.get(round(ratio, 3), f"ratio {ratio:.3f}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Pitch Shifter Demo")
    parser.add_argument("--ratio", type=float, default=0.5,
                        help="Pitch ratio (0 < ratio < 1, default 0.5 = octave down)")
    args = parser.parse_args()
    run_pitch_shifter_demo(pitch_ratio=args.ratio)
