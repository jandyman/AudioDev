"""
Loop Controller demo — validates loop point detection and crossfade management.

Pipeline (all DSP in Faust/C++, Python is test harness and visualization):
  Audio → ZC Detector (Faust) → zc_impulse  ┐
  Audio → Attack Detector (Faust) → attack   ┤→ Loop Controller (C++) → probe outputs
                                              ┘

Loop Controller outputs:
  0: tap1_delay_ms
  1: tap2_delay_ms
  2: gain1
  3: gain2
  4: latency_ms      (probe: active tap delay)
  5: loop_event      (probe: impulse when loop transition fires)
  6: active_tap      (probe: 0 or 1)
  7: bailout_event   (probe: impulse when bailout fires)
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


def run_loop_controller_demo():
    print("Loop Controller Demo")
    print("=" * 60)

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
    print(f"  Sample rate: {sample_rate} Hz")
    print(f"  Duration:    {duration:.2f} s  ({num_samples} samples)")

    # ---------------------------------------------------------------
    # Stage 1: ZC Detector
    # ---------------------------------------------------------------
    zc_det = FaustZeroCrossingDetector()
    zc_det.init(sample_rate)
    zc_outs = zc_det.process([audio_in])
    zc_impulse = zc_outs[0]

    zc_count = int(np.sum(zc_impulse > 0.5))
    print(f"\nZC Detector:  {zc_count} qualified zero crossings")

    # ---------------------------------------------------------------
    # Stage 2: Attack Detector
    # ---------------------------------------------------------------
    atk_det = FaustAttackDetector()
    atk_det.init(sample_rate)
    atk_outs = atk_det.process([audio_in])
    attack_impulse = atk_outs[0]

    atk_count = int(np.sum(attack_impulse > 0.5))
    print(f"Attack Det:   {atk_count} attacks detected")

    # ---------------------------------------------------------------
    # Stage 3: Loop Controller (chunked to match real-time operation)
    # ---------------------------------------------------------------
    lc = LoopController()
    lc.init(sample_rate)

    chunk = 512
    tap1_delay = np.zeros(num_samples)
    tap2_delay = np.zeros(num_samples)
    gain1      = np.zeros(num_samples)
    gain2      = np.zeros(num_samples)
    latency    = np.zeros(num_samples)
    loop_evts  = np.zeros(num_samples)
    active_tap = np.zeros(num_samples)
    bailout_evts = np.zeros(num_samples)

    for i in range(0, num_samples, chunk):
        end = min(i + chunk, num_samples)
        outs = lc.process([
            zc_impulse[i:end].astype(np.float32),
            attack_impulse[i:end].astype(np.float32),
        ])
        tap1_delay[i:end]   = outs[0]
        tap2_delay[i:end]   = outs[1]
        gain1[i:end]        = outs[2]
        gain2[i:end]        = outs[3]
        latency[i:end]      = outs[4]
        loop_evts[i:end]    = outs[5]
        active_tap[i:end]   = outs[6]
        bailout_evts[i:end] = outs[7]

    loop_indices    = np.where(loop_evts > 0.5)[0]
    bailout_indices = np.where(bailout_evts > 0.5)[0]
    attack_indices  = np.where(attack_impulse > 0.5)[0]

    print(f"\nLoop Controller results:")
    print(f"  Loop transitions:  {len(loop_indices)}")
    print(f"  Bailout events:    {len(bailout_indices)}")
    print(f"  Max latency:       {latency.max():.1f} ms")
    print(f"  Final latency:     {latency[-1]:.1f} ms")

    # ---------------------------------------------------------------
    # Plot
    # ---------------------------------------------------------------
    t = np.arange(num_samples) / sample_rate

    fig, axes = plt.subplots(4, 1, figsize=(16, 14), sharex=True)
    fig.suptitle(f"Loop Controller — {os.path.basename(input_path)}", fontsize=14)

    # Panel 1: Waveform with attack and loop event markers
    axes[0].plot(t, audio_in, 'b-', linewidth=0.3, alpha=0.7)
    for idx in attack_indices:
        axes[0].axvline(t[idx], color='red', linewidth=1.2, alpha=0.8, label='Attack' if idx == attack_indices[0] else '')
    for idx in loop_indices:
        axes[0].axvline(t[idx], color='green', linewidth=0.8, alpha=0.5, label='Loop event' if idx == loop_indices[0] else '')
    for idx in bailout_indices:
        axes[0].axvline(t[idx], color='orange', linewidth=1.2, alpha=0.8, label='Bailout' if idx == bailout_indices[0] else '')
    axes[0].set_ylabel('Amplitude')
    axes[0].set_title(f'Waveform — attacks (red), loop transitions (green), bailouts (orange)')
    axes[0].legend(loc='upper right', fontsize=8)
    axes[0].grid(True, alpha=0.3)
    axes[0].set_xlim(0, t[-1])

    # Panel 2: Latency over time with threshold lines
    LOWER_THRESHOLD_MS = 100.0
    UPPER_THRESHOLD_MS = 200.0
    axes[1].plot(t, latency, 'b-', linewidth=0.6, label='Latency (active tap)')
    axes[1].axhline(LOWER_THRESHOLD_MS, color='green', linewidth=1.0, linestyle='--',
                    label=f'Lower threshold ({LOWER_THRESHOLD_MS:.0f} ms)')
    axes[1].axhline(UPPER_THRESHOLD_MS, color='red', linewidth=1.0, linestyle='--',
                    label=f'Upper threshold / bailout ({UPPER_THRESHOLD_MS:.0f} ms)')
    for idx in attack_indices:
        axes[1].axvline(t[idx], color='red', linewidth=0.8, alpha=0.4)
    for idx in loop_indices:
        axes[1].axvline(t[idx], color='green', linewidth=0.8, alpha=0.4)
    axes[1].set_ylabel('Delay (ms)')
    axes[1].set_title('Active tap latency — loop transitions keep it below the upper threshold')
    axes[1].legend(loc='upper right', fontsize=8)
    axes[1].grid(True, alpha=0.3)

    # Panel 3: Tap delays and active tap indicator
    axes[2].plot(t, tap1_delay, color='steelblue', linewidth=0.5, alpha=0.8, label='Tap 1 delay')
    axes[2].plot(t, tap2_delay, color='darkorange', linewidth=0.5, alpha=0.8, label='Tap 2 delay')
    # Shade active tap regions
    tap1_active = active_tap < 0.5
    tap2_active = active_tap >= 0.5
    ymax = max(tap1_delay.max(), tap2_delay.max()) * 1.05
    axes[2].fill_between(t, 0, ymax, where=tap1_active, alpha=0.08, color='steelblue', label='Tap 1 active')
    axes[2].fill_between(t, 0, ymax, where=tap2_active, alpha=0.08, color='darkorange', label='Tap 2 active')
    axes[2].set_ylabel('Delay (ms)')
    axes[2].set_title('Both tap delays ramping — shading shows which tap is active')
    axes[2].legend(loc='upper right', fontsize=8)
    axes[2].grid(True, alpha=0.3)
    axes[2].set_ylim(0, ymax)

    # Panel 4: Crossfade gains
    axes[3].plot(t, gain1, color='steelblue', linewidth=0.6, label='Gain 1')
    axes[3].plot(t, gain2, color='darkorange', linewidth=0.6, label='Gain 2')
    for idx in loop_indices:
        axes[3].axvline(t[idx], color='green', linewidth=0.8, alpha=0.4)
    for idx in attack_indices:
        axes[3].axvline(t[idx], color='red', linewidth=0.8, alpha=0.4)
    axes[3].set_xlabel('Time (s)')
    axes[3].set_ylabel('Gain')
    axes[3].set_title('Crossfade gains — transitions show the ping-pong handoffs')
    axes[3].legend(loc='upper right', fontsize=8)
    axes[3].grid(True, alpha=0.3)
    axes[3].set_ylim(-0.05, 1.05)

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.subplots_adjust(hspace=0.35)

    output_path = os.path.join(os.path.dirname(__file__), '..', '..', 'test_audio_out',
                               'loop_controller_demo.png')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=150)
    print(f"\nPlot saved to {output_path}")
    plt.show()

    print("\n" + "=" * 60)
    print("Loop Controller Demo Complete")


if __name__ == "__main__":
    run_loop_controller_demo()
