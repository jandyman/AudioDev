"""
End-to-end pitch shift test with attack detection and crossfade.

Chains three Faust modules:
  1. attack_detector: detects note attacks
  2. crossfade_control: manages ping-pong delay taps with crossfading
  3. dual_tap_delay: shared delay buffer with two read taps

The crossfade control resets the inactive tap on each attack and
crossfades to it, keeping latency bounded while preserving transients.

Output is mixed in Python: output = tap1 * gain1 + tap2 * gain2
"""
import sys
import os
import time
import numpy as np
import scipy.io.wavfile as wav
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build'))

from build.pybind_faust_attack_detector import FaustAttackDetector
from build.pybind_faust_crossfade_control import FaustCrossfadeControl
from build.pybind_faust_dual_tap_delay import FaustDualTapDelay
from python import CppProcessor


def run_crossfade_pitch_shift():
    print("Crossfade Pitch Shift — End-to-End Test")
    print("=" * 60)

    PITCH_RATIO = 0.5  # Octave down

    # Load input audio
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
    print(f"  Duration: {duration:.2f} seconds")
    print(f"  Samples: {num_samples}")
    print(f"  Pitch ratio: {PITCH_RATIO} (octave down)")

    # === Stage 1: Attack Detection ===
    print("\n--- Stage 1: Attack Detection ---")
    det = CppProcessor(FaustAttackDetector())
    det.init(sample_rate)

    t0 = time.perf_counter()
    det_outputs = det.process([audio_in])
    t1 = time.perf_counter()
    print(f"  Processed in {(t1-t0)*1000:.1f} ms")

    trigger = det_outputs[0]
    threshold = det_outputs[1]
    fast_env = det_outputs[2]
    slow_env = det_outputs[3]
    note_ended = det_outputs[4]
    med_env = det_outputs[5]

    trigger_indices = np.where(trigger > 0.5)[0]

    # Classify triggers as normal or retrigger
    inhibit_ms = 50
    retrigger_flags = []
    for i, idx in enumerate(trigger_indices):
        if i > 0:
            gap_ms = (idx - trigger_indices[i - 1]) / sample_rate * 1000
            retrigger_flags.append(gap_ms < inhibit_ms + 5)
        else:
            retrigger_flags.append(False)

    normal_idx = [idx for idx, rt in zip(trigger_indices, retrigger_flags) if not rt]
    retrig_idx = [idx for idx, rt in zip(trigger_indices, retrigger_flags) if rt]

    print(f"  Detected {len(trigger_indices)} triggers "
          f"({len(normal_idx)} normal, {len(retrig_idx)} retrigger)")
    for i, idx in enumerate(trigger_indices):
        gap = (idx - trigger_indices[i - 1]) / sample_rate * 1000 if i > 0 else 999
        kind = "RETRIG" if retrigger_flags[i] else "normal"
        print(f"    {i + 1:2d}. t={idx / sample_rate:.3f}s  {kind:7s}  "
              f"fast={fast_env[idx]:.4f}  med={med_env[idx]:.4f}  "
              f"gap={gap:.0f}ms")

    # === Stage 2: Crossfade Control ===
    print("\n--- Stage 2: Crossfade Control ---")
    ctrl = CppProcessor(FaustCrossfadeControl())
    ctrl.init(sample_rate)

    pitch_ratio_signal = np.full(num_samples, PITCH_RATIO)

    t0 = time.perf_counter()
    ctrl_outputs = ctrl.process([trigger, pitch_ratio_signal])
    t1 = time.perf_counter()
    print(f"  Processed in {(t1-t0)*1000:.1f} ms")

    delay1_ms = ctrl_outputs[0]
    delay2_ms = ctrl_outputs[1]
    gain1 = ctrl_outputs[2]
    gain2 = ctrl_outputs[3]

    # === Stage 3: Dual Tap Delay ===
    print("\n--- Stage 3: Dual Tap Delay ---")
    delay = CppProcessor(FaustDualTapDelay())
    delay.init(sample_rate)

    t0 = time.perf_counter()
    delay_outputs = delay.process([audio_in, delay1_ms, delay2_ms])
    t1 = time.perf_counter()
    print(f"  Processed in {(t1-t0)*1000:.1f} ms")

    tap1 = delay_outputs[0]
    tap2 = delay_outputs[1]

    # === Mix ===
    output = tap1 * gain1 + tap2 * gain2
    print(f"\n  Output range: [{np.min(output):.4f}, {np.max(output):.4f}]")

    # === Save output ===
    output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'test_audio_out')
    os.makedirs(output_dir, exist_ok=True)

    out_int16 = np.clip(output * 32767, -32768, 32767).astype(np.int16)
    out_path = os.path.join(output_dir, 'pitch_shift_crossfade_octave_down.wav')
    wav.write(out_path, sample_rate, out_int16)
    print(f"\n  Output saved: {out_path}")

    # === Plot ===
    t = np.arange(num_samples) / sample_rate
    retrigger_ratio = 1.4  # must match attack_detector.dsp

    fig, axes = plt.subplots(5, 1, figsize=(16, 14))
    fig.suptitle(f"Crossfade Pitch Shift — ratio {PITCH_RATIO} (octave down)", fontsize=14)

    # Panel 1: Input waveform with attack triggers
    axes[0].plot(t, audio_in, 'b-', linewidth=0.3, alpha=0.7)
    for idx in normal_idx:
        axes[0].axvline(t[idx], color='red', linewidth=1.5, alpha=0.8)
    for idx in retrig_idx:
        axes[0].axvline(t[idx], color='orange', linewidth=1.5, alpha=0.8, linestyle='--')
    axes[0].set_ylabel('Amplitude')
    axes[0].set_title(f'Input — {len(normal_idx)} triggers (red), '
                      f'{len(retrig_idx)} retriggers (orange dashed)')
    axes[0].grid(True, alpha=0.3)
    axes[0].set_xlim(0, t[-1])

    # Panel 2: Three envelopes + retrigger threshold
    axes[1].plot(t, fast_env, 'r-', linewidth=0.8, label='fast (1ms/10ms)')
    axes[1].plot(t, med_env, 'g-', linewidth=0.8, label='med (5ms/50ms)')
    axes[1].plot(t, slow_env, 'b-', linewidth=0.8, label='slow (50ms/200ms)')
    axes[1].plot(t, med_env * retrigger_ratio, 'g--', linewidth=0.5, alpha=0.6,
                 label=f'med × {retrigger_ratio} (retrigger)')
    # Shade note_ended regions
    ne_diff = np.diff(note_ended.astype(int), prepend=0)
    ne_on = np.where(ne_diff > 0)[0]
    ne_off = np.where(ne_diff < 0)[0]
    if len(ne_off) < len(ne_on):
        ne_off = np.append(ne_off, num_samples - 1)
    for on, off in zip(ne_on, ne_off):
        axes[1].axvspan(t[on], t[min(off, num_samples - 1)], color='yellow', alpha=0.12)
    for idx in normal_idx:
        axes[1].axvline(t[idx], color='red', linewidth=0.5, alpha=0.4)
    for idx in retrig_idx:
        axes[1].axvline(t[idx], color='orange', linewidth=0.5, alpha=0.4)
    axes[1].set_ylabel('Level')
    axes[1].set_title('Envelopes — yellow shading = note_ended (armed)')
    axes[1].legend(loc='upper right', fontsize=8)
    axes[1].grid(True, alpha=0.3)
    axes[1].set_xlim(0, t[-1])

    # Panel 3: Output waveform
    axes[2].plot(t, output, 'b-', linewidth=0.3, alpha=0.7)
    for idx in normal_idx:
        axes[2].axvline(t[idx], color='red', linewidth=0.5, alpha=0.5)
    for idx in retrig_idx:
        axes[2].axvline(t[idx], color='orange', linewidth=0.5, alpha=0.5, linestyle='--')
    axes[2].set_ylabel('Amplitude')
    axes[2].set_title('Output — pitch shifted with crossfade')
    axes[2].grid(True, alpha=0.3)
    axes[2].set_xlim(0, t[-1])

    # Helper for zoomed envelope panels
    def plot_zoom(ax, zoom_s, zoom_e, title):
        zs, ze = int(zoom_s * sample_rate), int(zoom_e * sample_rate)
        tz = t[zs:ze]
        ax.plot(tz, fast_env[zs:ze], 'r-', linewidth=1, label='fast')
        ax.plot(tz, med_env[zs:ze], 'g-', linewidth=1, label='med')
        ax.plot(tz, slow_env[zs:ze], 'b-', linewidth=1, label='slow')
        ax.plot(tz, med_env[zs:ze] * retrigger_ratio, 'g--', linewidth=0.8, alpha=0.6,
                label=f'med × {retrigger_ratio}')
        ax.plot(tz, np.abs(audio_in[zs:ze]) * 0.5, 'k-', linewidth=0.2, alpha=0.2,
                label='|audio| (scaled)')
        for on, off in zip(ne_on, ne_off):
            if t[min(off, num_samples - 1)] > zoom_s and t[on] < zoom_e:
                ax.axvspan(max(t[on], zoom_s), min(t[min(off, num_samples - 1)], zoom_e),
                           color='yellow', alpha=0.12)
        for idx in trigger_indices:
            if zs <= idx < ze:
                is_rt = idx in retrig_idx
                color = 'orange' if is_rt else 'red'
                style = '--' if is_rt else '-'
                ax.axvline(t[idx], color=color, linewidth=1.5, alpha=0.8, linestyle=style)
        ax.set_ylabel('Level')
        ax.set_title(title)
        ax.legend(loc='upper right', fontsize=8)
        ax.grid(True, alpha=0.3)

    # Panel 4: Zoomed around 2.1-2.9s (false trigger + retrigger)
    plot_zoom(axes[3], 2.1, 2.9, 'Zoomed 2.1–2.9s — false trigger with retrigger')

    # Panel 5: Zoomed around 3.5-4.1s (false trigger without retrigger)
    plot_zoom(axes[4], 3.5, 4.1, 'Zoomed 3.5–4.1s — false trigger without retrigger')
    axes[4].set_xlabel('Time (s)')

    plt.tight_layout(rect=[0, 0.02, 1, 0.97])
    plt.subplots_adjust(hspace=0.45)

    plot_path = os.path.join(os.path.dirname(__file__), 'crossfade_pitch_shift_test.png')
    plt.savefig(plot_path, dpi=150)
    print(f"  Plot saved: {plot_path}")
    plt.show()

    print("\n" + "=" * 60)
    print("Crossfade Pitch Shift Test Complete")


if __name__ == "__main__":
    run_crossfade_pitch_shift()
