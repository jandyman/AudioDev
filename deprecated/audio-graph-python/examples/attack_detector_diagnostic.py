"""
Attack Detector Diagnostic — shows all envelope signals and trigger decisions.

Plots 4 panels:
  1. Input waveform with trigger markers (red=normal, orange=retrigger)
  2. Absolute levels: fast_env, med_env, slow_env, and retrigger threshold (med*ratio)
  3. fast/med ratio with retrigger threshold line
  4. Zoomed view around the problematic ~2.45s region

Run interactively to inspect signals.
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


def run():
    input_path = os.path.join(os.path.dirname(__file__), '..', '..', 'test_audio', 'Bass Notes No Gap.wav')
    sample_rate, audio_data = wav.read(input_path)

    if audio_data.dtype == np.int16:
        audio_in = audio_data.astype(np.float64) / 32768.0
    else:
        audio_in = audio_data.astype(np.float64)
    if audio_in.ndim > 1:
        audio_in = audio_in[:, 0]

    num_samples = len(audio_in)
    t = np.arange(num_samples) / sample_rate

    # Run detector
    det = CppProcessor(FaustAttackDetector())
    det.init(sample_rate)
    outs = det.process([audio_in])
    trigger, threshold, fast_env, slow_env, note_ended, med_env = outs

    fast_deriv = np.diff(fast_env, prepend=fast_env[0])

    # Find triggers
    trigger_indices = np.where(trigger > 0.5)[0]

    # Classify: retrigger if gap to previous < inhibit_time
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

    print(f"Detected {len(trigger_indices)} triggers ({len(normal_idx)} normal, {len(retrig_idx)} retrigger)")
    for i, idx in enumerate(trigger_indices):
        gap = (idx - trigger_indices[i - 1]) / sample_rate * 1000 if i > 0 else 999
        kind = "RETRIG" if retrigger_flags[i] else "normal"
        fm_ratio = fast_env[idx] / (med_env[idx] + 1e-10)
        print(f"  {i + 1:2d}. t={idx / sample_rate:.3f}s  {kind:7s}  "
              f"fast={fast_env[idx]:.4f}  med={med_env[idx]:.4f}  "
              f"fast/med={fm_ratio:.2f}  gap={gap:.0f}ms")

    # Retrigger ratio from the DSP
    retrigger_ratio = 1.4

    # ---- Plot ----
    fig, axes = plt.subplots(4, 1, figsize=(16, 14))
    fig.suptitle("Attack Detector Diagnostic", fontsize=14)

    # Panel 1: Input waveform + triggers
    axes[0].plot(t, audio_in, 'b-', linewidth=0.3, alpha=0.5)
    for idx in normal_idx:
        axes[0].axvline(t[idx], color='red', linewidth=1.5, alpha=0.8)
    for idx in retrig_idx:
        axes[0].axvline(t[idx], color='orange', linewidth=1.5, alpha=0.8, linestyle='--')
    axes[0].set_ylabel('Amplitude')
    axes[0].set_title(f'Input waveform — {len(normal_idx)} triggers (red), '
                      f'{len(retrig_idx)} retriggers (orange dashed)')
    axes[0].grid(True, alpha=0.3)
    axes[0].set_xlim(0, t[-1])

    # Panel 2: Absolute levels
    axes[1].plot(t, fast_env, 'r-', linewidth=0.8, label='fast_env (1ms/10ms)')
    axes[1].plot(t, med_env, 'g-', linewidth=0.8, label='med_env (5ms/50ms)')
    axes[1].plot(t, slow_env, 'b-', linewidth=0.8, label='slow_env (50ms/200ms)')
    axes[1].plot(t, med_env * retrigger_ratio, 'g--', linewidth=0.5, alpha=0.7,
                 label=f'med_env × {retrigger_ratio} (retrigger thresh)')
    # Mark note_ended regions
    ne_changes = np.diff(note_ended.astype(int))
    ne_on = np.where(ne_changes > 0)[0]
    ne_off = np.where(ne_changes < 0)[0]
    for on in ne_on:
        axes[1].axvspan(t[on], t[min(on + 1, len(t) - 1)], color='yellow', alpha=0.15)
    for idx in normal_idx:
        axes[1].axvline(t[idx], color='red', linewidth=0.5, alpha=0.5)
    for idx in retrig_idx:
        axes[1].axvline(t[idx], color='orange', linewidth=0.5, alpha=0.5)
    axes[1].set_ylabel('Level')
    axes[1].set_title('Envelope levels — yellow = note_ended (armed)')
    axes[1].legend(loc='upper right', fontsize=8)
    axes[1].grid(True, alpha=0.3)
    axes[1].set_xlim(0, t[-1])

    # Panel 3: fast/med ratio
    fm_ratio_signal = fast_env / (med_env + 1e-10)
    axes[2].plot(t, fm_ratio_signal, 'b-', linewidth=0.5, alpha=0.7)
    axes[2].axhline(retrigger_ratio, color='red', linewidth=1, linestyle='--',
                     label=f'retrigger threshold ({retrigger_ratio})')
    axes[2].axhline(1.0, color='gray', linewidth=0.5, linestyle=':')
    for idx in normal_idx:
        axes[2].axvline(t[idx], color='red', linewidth=0.5, alpha=0.5)
    for idx in retrig_idx:
        axes[2].axvline(t[idx], color='orange', linewidth=0.5, alpha=0.5)
    axes[2].set_ylabel('fast / med')
    axes[2].set_title('fast_env / med_env ratio — retrigger fires when above red dashed')
    axes[2].legend(loc='upper right', fontsize=8)
    axes[2].grid(True, alpha=0.3)
    axes[2].set_ylim(0.4, 2.5)
    axes[2].set_xlim(0, t[-1])

    # Panel 4: Zoom around 2.1-2.9s (problematic region)
    zoom_s, zoom_e = 2.1, 2.9
    zs, ze = int(zoom_s * sample_rate), int(zoom_e * sample_rate)
    tz = t[zs:ze]

    ax4 = axes[3]
    ax4.plot(tz, fast_env[zs:ze], 'r-', linewidth=1, label='fast_env')
    ax4.plot(tz, med_env[zs:ze], 'g-', linewidth=1, label='med_env')
    ax4.plot(tz, slow_env[zs:ze], 'b-', linewidth=1, label='slow_env')
    ax4.plot(tz, med_env[zs:ze] * retrigger_ratio, 'g--', linewidth=0.8, alpha=0.7,
             label=f'med × {retrigger_ratio}')
    ax4.plot(tz, audio_in[zs:ze] * 0.3, 'k-', linewidth=0.2, alpha=0.3, label='audio (scaled)')
    for idx in trigger_indices:
        if zs <= idx < ze:
            is_rt = idx in retrig_idx
            color = 'orange' if is_rt else 'red'
            style = '--' if is_rt else '-'
            ax4.axvline(t[idx], color=color, linewidth=1.5, alpha=0.8, linestyle=style)
    ax4.set_xlabel('Time (s)')
    ax4.set_ylabel('Level')
    ax4.set_title('Zoomed: 2.1–2.9s — note tail with false trigger region')
    ax4.legend(loc='upper right', fontsize=8)
    ax4.grid(True, alpha=0.3)

    plt.tight_layout(rect=[0, 0.02, 1, 0.97])
    plt.subplots_adjust(hspace=0.4)

    plot_path = os.path.join(os.path.dirname(__file__), 'attack_detector_diagnostic.png')
    plt.savefig(plot_path, dpi=150)
    print(f"\nPlot saved: {plot_path}")
    plt.show()


if __name__ == "__main__":
    run()
