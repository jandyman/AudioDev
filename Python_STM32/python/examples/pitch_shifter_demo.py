"""
Pitch Shifter demo — full pipeline end-to-end.

Pipeline (all DSP in Faust/C++, Python is test harness):

  Audio → Input LPF (Faust, ~10 kHz) → audio_lpf ─┐
                                                   ├→ ZC Detector → zc_impulse ───┐
                                                   ├→ Attack Detector → (bypassed)│
                                                   │                              ├→ Loop Controller (C++)
                                                   │       attack_impulse = 0 ────┘
                                                   │                              ↓
                                                   │       tap1_delay_ms, tap2_delay_ms, gain1, gain2
                                                   │                              ↓
                                                   └→ Dual Tap Delay ──────────→ tap1, tap2
                                                                                  ↓
                                                                output = tap1 * gain1 + tap2 * gain2

Loop-first development: the attack detector is wired but its output is forced
to zero, so the loop controller sees a sustain-only signal. Flip BYPASS_ATTACK
at the bottom of the file to re-enable it.

The loop controller and dual tap delay are processed in lockstep chunks so the
delay control signals are applied sample-accurately.
"""
import sys
import os
import numpy as np
import scipy.io.wavfile as wav
import matplotlib
matplotlib.use('macosx')   # native macOS backend — delivers trackpad scroll events reliably
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build'))

from build.pybind_faust_input_lpf import FaustInputLpf
from build.pybind_faust_zero_crossing_detector import FaustZeroCrossingDetector
from build.pybind_faust_attack_detector import FaustAttackDetector
from build.pybind_harmonic_rejector import HarmonicRejector
from build.pybind_loop_controller import LoopController
from build.pybind_faust_dual_tap_delay import FaustDualTapDelay
from build.pybind_mixer2 import Mixer2


def run_pitch_shifter_demo(pitch_ratio=0.5, lpf_fc_hz=10000.0, bypass_attack=True):
    print("Pitch Shifter Demo")
    print("=" * 60)
    print(f"Pitch ratio: {pitch_ratio}  ({pitch_ratio_label(pitch_ratio)})")
    print(f"Input LPF:   {lpf_fc_hz:.0f} Hz (2nd-order Butterworth)")
    print(f"Attack det:  {'BYPASSED (forced to zero)' if bypass_attack else 'enabled'}")

    input_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'test_audio', 'Longer Bass Notes.wav')
    sample_rate, audio_data = wav.read(input_path)

    if audio_data.dtype == np.int16:
        audio_raw = audio_data.astype(np.float64) / 32768.0
    elif audio_data.dtype == np.int32:
        audio_raw = audio_data.astype(np.float64) / 2147483648.0
    else:
        audio_raw = audio_data.astype(np.float64)

    if audio_raw.ndim > 1:
        audio_raw = audio_raw[:, 0]

    num_samples = len(audio_raw)
    duration = num_samples / sample_rate

    print(f"\nInput: {os.path.basename(input_path)}")
    print(f"  Sample rate: {sample_rate} Hz,  Duration: {duration:.2f} s")

    # ---------------------------------------------------------------
    # Stage 0: Input LPF — preprocess raw file signal
    # All downstream stages consume audio_in (the post-LPF signal),
    # which is also what gets plotted as "Input".
    # ---------------------------------------------------------------
    lpf = FaustInputLpf()
    lpf.init(sample_rate)
    lpf.set_param("fc", lpf_fc_hz)
    audio_in = lpf.process([audio_raw])[0]

    # ---------------------------------------------------------------
    # Stage 1: ZC Detector — full file, no state dependency on pitch
    # ---------------------------------------------------------------
    zc_det = FaustZeroCrossingDetector()
    zc_det.init(sample_rate)
    zc_impulse = zc_det.process([audio_in])[0]
    print(f"\nZC Detector:    {int(np.sum(zc_impulse > 0.5))} qualified zero crossings")

    # ---------------------------------------------------------------
    # Stage 2: Attack Detector — full file
    # Detector is kept wired so we can re-enable it with one flag,
    # but its output is zeroed when bypass_attack is True (loop-first dev).
    # ---------------------------------------------------------------
    atk_det = FaustAttackDetector()
    atk_det.init(sample_rate)
    attack_impulse = atk_det.process([audio_in])[0]
    raw_attack_count = int(np.sum(attack_impulse > 0.5))
    if bypass_attack:
        attack_impulse = np.zeros_like(attack_impulse)
        print(f"Attack Det:     {raw_attack_count} detected, bypassed → loop controller sees 0")
    else:
        print(f"Attack Det:     {raw_attack_count} attacks detected")

    # ---------------------------------------------------------------
    # Stage 2.5: Harmonic Rejector — multi-LPF bank + cleanness selector
    # Produces a per-sample period estimate P (samples) plus sigma and a
    # qualified flag, which the LoopController uses to gate candidate ZCs
    # to integer multiples of P. Falls back to the legacy newest-valid pick
    # when qualified == 0 (during the bank's EMA warm-up, silence, etc.).
    # Full-buffer call here; outputs are sliced per chunk into the LC loop.
    # ---------------------------------------------------------------
    hr = HarmonicRejector()
    hr.init(sample_rate)
    hr_outs = hr.process([audio_in.astype(np.float32)])
    N_HR = HarmonicRejector.NUM_FILTERS
    selected_filter = hr_outs[7 * N_HR + 0]
    P_samples       = hr_outs[7 * N_HR + 1]
    sigma_samples   = hr_outs[7 * N_HR + 2]
    qualified       = hr_outs[7 * N_HR + 3]
    qual_count = int(np.sum(qualified > 0.5))
    print(f"Harmonic Rej:   qualified {qual_count}/{num_samples} samples "
          f"({100.0*qual_count/num_samples:.0f}%); "
          f"per-filter selected counts: " +
          ", ".join(f"f{fi}={int(np.sum(selected_filter == fi))}" for fi in range(N_HR)))

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

    mixer = Mixer2()
    mixer.init(sample_rate)

    chunk = 512
    audio_out    = np.zeros(num_samples)
    tap1_del     = np.zeros(num_samples)
    tap2_del     = np.zeros(num_samples)
    gain1_arr    = np.zeros(num_samples)
    gain2_arr    = np.zeros(num_samples)
    loop_evts    = np.zeros(num_samples)
    bailout_evts = np.zeros(num_samples)
    gated_evts   = np.zeros(num_samples)

    print("\nProcessing...")
    for i in range(0, num_samples, chunk):
        end = min(i + chunk, num_samples)

        # Loop Controller: ZC + attack + (P, sigma, qualified) → delays and gains
        lc_outs = lc.process([
            zc_impulse[i:end].astype(np.float32),
            attack_impulse[i:end].astype(np.float32),
            P_samples[i:end].astype(np.float32),
            sigma_samples[i:end].astype(np.float32),
            qualified[i:end].astype(np.float32),
        ])
        tap1_delay_ms = lc_outs[0]
        tap2_delay_ms = lc_outs[1]
        gain1         = lc_outs[2]
        gain2         = lc_outs[3]

        tap1_del[i:end]     = lc_outs[0]
        tap2_del[i:end]     = lc_outs[1]
        gain1_arr[i:end]    = lc_outs[2]
        gain2_arr[i:end]    = lc_outs[3]
        loop_evts[i:end]    = lc_outs[5]
        bailout_evts[i:end] = lc_outs[7]
        gated_evts[i:end]   = lc_outs[8]

        # Dual Tap Delay: audio + delay times → two taps
        dtd_outs = dtd.process([
            audio_in[i:end],
            tap1_delay_ms,
            tap2_delay_ms,
        ])
        tap1 = dtd_outs[0]
        tap2 = dtd_outs[1]

        # Crossfade mix (C++ Mixer2)
        mix_outs = mixer.process([
            tap1.astype(np.float32),
            tap2.astype(np.float32),
            gain1,
            gain2,
        ])
        audio_out[i:end] = mix_outs[0]

    loop_count    = int(np.sum(loop_evts > 0.5))
    bailout_count = int(np.sum(bailout_evts > 0.5))
    gated_count   = int(np.sum(gated_evts > 0.5))
    print(f"  Loop transitions: {loop_count}  (of which gate-redirected: {gated_count})")
    print(f"  Bailout events:   {bailout_count}")
    print(f"  Max tap1 delay:   {tap1_del.max():.1f} ms")
    print(f"  Max tap2 delay:   {tap2_del.max():.1f} ms")

    # ---------------------------------------------------------------
    # Save output
    # ---------------------------------------------------------------
    output_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'test_audio_out')
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

    fig, axes = plt.subplots(4, 1, figsize=(16, 12), sharex=True,
                             gridspec_kw={'height_ratios': [2, 3, 1, 2]})
    attack_state = "attack bypassed" if bypass_attack else "attack on"
    fig.suptitle(f"Pitch Shifter — {pitch_ratio_label(pitch_ratio)}  ({os.path.basename(input_path)}, LPF {lpf_fc_hz:.0f} Hz, {attack_state})", fontsize=14)
    fig.text(0.5, 0.955, "scroll = zoom x  •  toolbar Home resets",
             ha='center', fontsize=9, style='italic', color='#555')

    # Panel 1: Input (post-LPF) with event markers
    axes[0].plot(t, audio_in, 'b-', linewidth=0.3, alpha=0.7, label=f'Input (post-LPF {lpf_fc_hz:.0f} Hz)')
    for idx in loop_indices:
        axes[0].axvline(t[idx], color='green', linewidth=0.8, alpha=0.3)
    for idx in attack_indices:
        axes[0].axvline(t[idx], color='red', linewidth=0.8, alpha=0.3)
    axes[0].set_ylabel('Amplitude')
    axes[0].set_title('Input post-LPF')
    axes[0].legend(loc='upper right', fontsize=8)
    axes[0].grid(True, alpha=0.3)
    axes[0].set_xlim(0, t[-1])

    # Panel 2: tap delays (left) + output audio (right, independent scale)
    ax_out = axes[1].twinx()

    axes[1].plot(t, tap1_del, 'b-',  linewidth=0.7, alpha=0.9, label='Tap 1 delay (ms)')
    axes[1].plot(t, tap2_del, 'C1-', linewidth=0.7, alpha=0.9, label='Tap 2 delay (ms)')
    axes[1].axhline(60.0,  color='green', linewidth=1.0, linestyle='--', label='Lower threshold (60 ms)')
    axes[1].axhline(200.0, color='red',   linewidth=1.0, linestyle='--', label='Upper threshold (200 ms)')
    for idx in attack_indices:
        axes[1].axvline(t[idx], color='red',   linewidth=0.8, alpha=0.4)
    for idx in loop_indices:
        axes[1].axvline(t[idx], color='green', linewidth=0.8, alpha=0.4)
    axes[1].set_ylabel('Delay (ms)', color='#222')
    axes[1].grid(True, alpha=0.3)

    ax_out.plot(t, audio_out, color='#999', linewidth=0.3, alpha=0.8, label='Output audio')
    ax_out.set_ylabel('Output amplitude', color='#555')
    ax_out.tick_params(axis='y', labelcolor='#555')

    lines1, labels1 = axes[1].get_legend_handles_labels()
    lines2, labels2 = ax_out.get_legend_handles_labels()
    axes[1].legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=8)
    axes[1].set_title('Tap delays (blue/orange, left) + output audio (grey/right) — loop (green), attacks (red)')

    # Panel 3: Crossfade gains (0–1 scale)
    axes[2].plot(t, gain1_arr, 'b-',  linewidth=0.8, alpha=0.9, label='Gain 1')
    axes[2].plot(t, gain2_arr, 'C1-', linewidth=0.8, alpha=0.9, label='Gain 2')
    for idx in attack_indices:
        axes[2].axvline(t[idx], color='red',   linewidth=0.8, alpha=0.4)
    for idx in loop_indices:
        axes[2].axvline(t[idx], color='green', linewidth=0.8, alpha=0.4)
    axes[2].set_ylabel('Gain')
    axes[2].set_ylim(-0.05, 1.1)
    axes[2].legend(loc='upper right', fontsize=8)
    axes[2].grid(True, alpha=0.3)

    # Panel 4: Harmonic Rejector selector state
    # - background tinted by selected filter (green/orange/purple = filter 0/1/2)
    # - black line = P (period estimate, ms); NaN where not qualified
    # - blue ▼ markers = transitions where the integer-multiple gate redirected
    #   the candidate pick away from newest-DT-valid
    filter_colors = ['green', 'C1', 'purple']
    sel = selected_filter.astype(int)
    # Coalesce runs of equal selected-filter index so we draw one axvspan per run
    boundaries = np.concatenate(([0], np.where(np.diff(sel) != 0)[0] + 1, [len(sel)]))
    for s, e in zip(boundaries[:-1], boundaries[1:]):
        fi = sel[s]
        if 0 <= fi < N_HR:
            axes[3].axvspan(t[s], t[e - 1], color=filter_colors[fi], alpha=0.15, lw=0)
    P_ms = P_samples / sample_rate * 1000.0
    P_ms_plot = np.where(qualified > 0.5, P_ms, np.nan)
    axes[3].plot(t, P_ms_plot, 'k-', linewidth=0.6, alpha=0.85, label='P (ms)')
    gated_indices = np.where(gated_evts > 0.5)[0]
    if len(gated_indices):
        axes[3].plot(t[gated_indices], np.full(len(gated_indices), 48.0),
                     'bv', ms=6, alpha=0.7, label='gate-redirected loop')
    axes[3].set_xlabel('Time (s)')
    axes[3].set_ylabel('P (ms)')
    axes[3].set_ylim(0, 50)
    axes[3].legend(loc='upper right', fontsize=8)
    axes[3].grid(True, alpha=0.3)
    axes[3].set_title('Selector state — tint: filter 0 (green) / 1 (orange) / 2 (purple); black = P; blue ▼ = gate-redirected loop')

    # Scroll-wheel zoom: horizontal-only, anchored at cursor x. With sharex=True
    # on the subplots, changing one xlim propagates to all panels.
    # (Matplotlib's built-in pan tool can also constrain to x: hold 'x' while panning.)
    _install_x_zoom(fig, x_min=0.0, x_max=t[-1])

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


def _install_x_zoom(fig, x_min, x_max, base_scale=1.3):
    """Scroll wheel -> horizontal-only zoom anchored at cursor x.

    With sharex=True on the figure's axes, changing one xlim propagates.
    Toolbar Home button resets to the original full range (we seed the
    toolbar's navigation stack on first draw so Home has a view to return to;
    scroll-wheel zoom otherwise leaves the stack empty).
    """
    def on_scroll(event):
        ax = event.inaxes
        if ax is None or event.xdata is None:
            return
        factor = (1.0 / base_scale) if event.step > 0 else base_scale
        x = event.xdata
        x0, x1 = ax.get_xlim()
        new_left  = max(x - (x - x0) * factor, x_min)
        new_right = min(x + (x1 - x) * factor, x_max)
        if new_right - new_left < 1e-6:
            return
        ax.set_xlim(new_left, new_right)
        fig.canvas.draw_idle()

    fig.canvas.mpl_connect('scroll_event', on_scroll)

    seeded = [False]
    def _seed_home(_evt):
        if seeded[0]: return
        tb = getattr(fig.canvas, 'toolbar', None)
        if tb is not None and hasattr(tb, 'push_current'):
            tb.push_current()
            seeded[0] = True
    fig.canvas.mpl_connect('draw_event', _seed_home)


if __name__ == "__main__":
    # ---- Demo parameters ----
    pitch_ratio    = 0.5      # 0.5 = octave down, 0.75 = fourth down, etc.
    lpf_fc_hz      = 10000.0  # input low-pass cutoff (2nd-order Butterworth)
    bypass_attack  = True     # loop-first dev: force attack_impulse = 0
    # -------------------------
    run_pitch_shifter_demo(pitch_ratio=pitch_ratio,
                           lpf_fc_hz=lpf_fc_hz,
                           bypass_attack=bypass_attack)
