# Python Experimentation & Diagnostic Plotting

How to use the shared host tooling for offline experimentation — generating
signals, running them through pure-Python, Faust, or compiled-C++ DSP, and
plotting the results with interactive, zoomable diagnostic figures.

Python here is the **test harness only** — it drives DSP and plots; it does not
implement shipping DSP logic (see `audio_graph_architecture.md` and the project
`.claude/CLAUDE.md`). Scripts are run from **PyCharm** under the `scipy` conda
env: no CLI arguments, configurable values are plain variables at the bottom of
the file. Demo/lab scripts use a `_demo.py` / `_lab.py` suffix — never a `test_`
prefix (PyCharm collects `test_*.py` for pytest, which blocks interactive plots).

This document grows incrementally; today it focuses on the plotting tools.

## The shared toolbox: `python/lib/diagnostic_plot.py`

One import sets up matplotlib for offline diagnostics **and** must come *before*
`import matplotlib.pyplot` — it selects a cooperative backend (TkAgg) and points
`MPLCONFIGDIR` at a writable cache. The canonical header:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'python'))
from lib.diagnostic_plot import install_x_zoom, load_audio_mono   # BEFORE pyplot
import numpy as np
import matplotlib.pyplot as plt
```

It provides two helpers: `load_audio_mono(path)` (file I/O, below) and
`install_x_zoom(fig, x_min, x_max)` (navigation, below).

## File I/O

**Loading.** `load_audio_mono(name, folder=TEST_AUDIO_DIR)` returns
`(sample_rate, samples)` with `samples` a float64 mono array in `[-1, 1]`
(int16/int32 are scaled; multi-channel is downmixed to channel 0).

- `name` — a bare filename, resolved under `folder`; the helper finds that folder
  relative to itself, so you don't reconstruct `../../../test_audio` from wherever
  your script lives. A `name` *with* a directory part (or absolute) is used as-is.
- `folder` — the search directory; defaults to the repo-root `test_audio/`.

```python
sr, audio = load_audio_mono("Fourth Test.wav")   # -> <repo>/test_audio/Fourth Test.wav
```

**Saving.** `out_path(name, folder=TEST_AUDIO_OUT_DIR)` returns a full path to
hand to `wav.write`, creating the directory.

- `name` — a bare filename, resolved under `folder`; a path with a directory part
  is used as-is. Use the `<input_stem>_<tag>.wav` convention — input stem verbatim
  (spaces, case), tag describing the transform. Never write generic names like
  `out.wav`.
- `folder` — the output directory; defaults to the repo-root `test_audio_out/`.

```python
import scipy.io.wavfile as wav
wav.write(out_path("Fourth Test_pitch_shifted_-5st.wav"), sr, out_i16)
```

**Multichannel — generated next to a reference.** To A/B processed audio against
a reference (the dry input, or a known-good render), save them as the channels of
one WAV: stack into an `(N, n_channels)` array, normalize by the **global** peak
(not per-channel — that preserves the relative levels you're trying to compare),
and pass it to `scipy.io.wavfile.write` as int16, which interleaves `(N, ch)` for
you. Convention: channel 0 = dry/reference, the processed signal(s) in the rest.
Then you can pan L/R to compare by ear and plot the columns on shared-x panels to
compare them time-aligned.

```python
import scipy.io.wavfile as wav
stereo = np.stack([reference, generated], axis=1)   # (N, 2): col0 = ref, col1 = generated
peak = np.abs(stereo).max()
if peak > 0:
  stereo = stereo / (peak * 1.05)                   # joint normalize, ~5% headroom
out_i16 = np.clip(stereo * 32767, -32768, 32767).astype(np.int16)
wav.write(out_path(f"{stem}_ref_vs_generated.wav"), sr, out_i16)
```

`pitch_shifter_demo.py` does exactly this (L = dry, R = shifted), so the saved
WAV is both an ear A/B and the source for its side-by-side input/output panels.

**Buffer-centric play/save.** `lib.audio_buf_tools` adds `load_wav`, `save_wav`,
`output_path(input_path, tag)`, and `play(buf, sr)` (in-process audition via
`sounddevice`) for slicing and listening to numpy buffers without writing files
(`from lib.audio_buf_tools import load_wav, play, ...`).

## Plotting — interactive diagnostic figures

The standard pattern is a multi-panel, shared-x figure with mouse-wheel
navigation. Build the panels, then call `install_x_zoom` once with the full
time range:

```python
t = np.arange(N) / sr
fig, ax = plt.subplots(3, 1, figsize=(15, 9), sharex=True)
ax[0].plot(t, audio, lw=0.5, color='0.6')
# ... fill the other panels ...
ax[0].set_xlim(0, t[-1])
fig.tight_layout()
install_x_zoom(fig, x_min=0.0, x_max=t[-1])
plt.show()
```

**`sharex=True` is essential** — it makes one panel's x-limits propagate to all,
so zoom/pan moves every panel together and they stay time-aligned.

### Navigation (no toolbar mode-switching)

| Gesture | Action |
| --- | --- |
| **scroll** | zoom x, anchored at the cursor (up = in, down = out) |
| **shift + scroll** | pan x left / right (down = back, up = forward) |
| **toolbar Home** | reset to the full original range |

Zoom is anchored at the cursor's x; pan preserves the current width and clamps
to the data range. `install_x_zoom` seeds the toolbar's navigation stack on the
first draw so **Home** always returns to the full view even after wheel
zoom/pan. Optional kwargs: `base_scale` (zoom factor per notch, default 1.3) and
`pan_frac` (fraction of the visible width moved per notch, default 0.40).

### Marking discrete events (triggers)

Overlaying discrete events — attack triggers, loop fires, bailouts — as vertical
lines across every panel is one of the most useful diagnostics: you instantly see
*when* something fired against *what the signals were doing*. `mark_events` (in
`lib.diagnostic_plot`) generalizes it:

```python
from lib.diagnostic_plot import mark_events
# Pass the whole axes array -> markers land on EVERY panel, time-aligned.
mark_events(axes, t, atk_trigger, color='orange', lw=1.0, label='attack')
mark_events(axes, t, loop_evts,   color='green',  lw=0.8, alpha=0.35)
```

The `events` argument is either a **per-sample 0/1 impulse/flag signal** (the
common case — e.g. a probe like `atk.trigger` or `lc.loop_event`; rising edges
are used, so single-sample impulses and held flags both give one marker per
event) or an **array of sample indices** you've already extracted. `axes` may be
a single Axes or the whole panel array — pass the array to mark all panels in one
call. Use a separate call per event *type* so each gets its own color; `label` is
attached to the first line only, so one legend entry appears. `event_indices(sig,
thresh)` is exposed separately if you just want the rising-edge indices (e.g. to
count events or slice around them). Keep lines semi-transparent (`alpha`) so they
read clearly without burying the waveform when zoomed out.

**Lines vs. point markers.** By default each event is a full-height vertical
line. To tag events at a specific height instead — handy for putting *different*
event types at different levels so they don't pile up — pass `marker` (`'^'`,
`'v'`, `'o'`, …) plus a `y` (data coordinate):

```python
mark_events(axes[4], t, gated_idx,   marker='v', y=48.0, color='b', label='loop suppressed')
mark_events(axes[4], t, bailout_idx, marker='^', y=5.0,  color='r', label='bailout')
```

Under the hood that's `ax.plot(t[idx], <constant y>, marker=...)` — point markers
at the event times — versus `axvline` for full-height lines. `pitch_shifter_demo.py`
uses exactly this to stack "loop suppressed" (▽, high) and "bailout" (△, low)
markers in one panel.

### Other panel patterns

- **State tinting** — `ax.axvspan(t[a], t[b], color=c, alpha=0.15, lw=0)` to shade
  spans where a selector/mode is active.
- **Probe panels** — plot any internal node tapped by name (next section); e.g.
  the YIN period gated by confidence, or the loop controller's latency.

### Overlay on a twin axis

To show a derived quantity (f0, confidence, a gain) against a panel's waveform
without squashing either, put it on a twin axis — it shares x but keeps its own
y scale:

```python
ax = axes[0]
ax.plot(t, audio, lw=0.5, color='0.6'); ax.set_ylabel('input')
axb = ax.twinx()                                  # shares x, independent y
axb.plot(t, f0, lw=1.2, color='C0')
axb.set_ylabel('f0 (Hz)', color='C0'); axb.set_ylim(0, 400)
```

Because the twin shares x (via the panels' `sharex=True` group), it zooms and
pans right along with everything else. One gotcha: `twinx()` axes aren't in the
array `subplots` returned, so `mark_events(axes, …)` draws onto the base panels
only — which is usually what you want (the line still spans the column); mark a
twin explicitly if you need markers on its scale.

Worked examples: `projects/pitch_shifter/pitch_shifter_demo.py` (5-panel
pipeline) and `projects/yin/yin_demo.py` (probes + a lag-domain snapshot).

## Three ways to put DSP under the plots

### 1. Pure Python (numpy)

Quickest for sketching an idea or building ground truth. Per the architecture,
this is a **temporary prototyping step** before C++/Faust — don't let real DSP
settle here. Load a wave file or generate a signal, process it in numpy, plot. (Example:
`yin_validate.py`'s reference YIN is pure numpy used only as ground truth.)

### 2. A Faust block

Two routes:

- **One-shot, no build** — `from lib.audio_buf_tools import run_faust`, then a
  single `dawdreamer` round-trip returns the output buffer. Best for auditioning
  a block in isolation:

  ```python
  out = run_faust(input_buf, dsp_path, params={"thresh": 0.3},
                  sr=sr, bs=128, out_duration=None)   # sr/bs/out_duration are keyword args
  ```

  - `input_buf` — mono numpy array of input samples.
  - `dsp_path` — **a path to the `.dsp` file**, not a bare name resolved under a
    default folder (unlike `load_audio_mono`). It's passed to Faust as-is, so a
    bare filename resolves against the *current working directory*; give a path
    that locates the file unambiguously (absolute, or built from the script dir,
    e.g. `os.path.join(os.path.dirname(__file__), "peak_detector.dsp")`). Its
    directory is added to Faust's library search path so sibling `.lib`/`.dsp`
    imports resolve regardless of cwd.
  - `params` — a dict that sets the block's Faust UI controls **by label**. The
    key is the label string from the Faust declaration — the first argument of
    `hslider`/`nentry`/`button`/`checkbox`/… — and the value is the raw value in
    that control's own range (not normalized). For a `.dsp` line
    `thresh = hslider("thresh", 0.3, 0.0, 1.0, 0.001);` you pass
    `params={"thresh": 0.3}`. Keys match the *leaf* label, not the full group
    path; an unknown key raises an error that **lists the available labels**, so a
    deliberate wrong guess (`params={"?": 0}`) is a quick way to discover them.
    The value is held constant for the whole render — for time-varying control,
    use the pybind route below. Omit `params` to use the `.dsp`'s declared
    defaults.

    **Author parameters with `nentry`, not `hslider`/`vslider`.** All three
    declare the same thing — a named control with `default, min, max, step` — but
    `hslider`/`vslider` bake a *UI-layout suggestion* (a horizontal/vertical
    slider) into the DSP source, conflating signal logic with widget choice.
    `nentry` ("numeric entry") is the UI-neutral form: it just says "this is a
    parameter." These blocks are driven programmatically anyway — `run_faust`
    sets controls by label, and on the embedded target they wire to real I/O — so
    the widget metaphor is noise. `nentry("label", default, min, max, step)` is a
    drop-in for `hslider` with the identical signature and the same label lookup.
  - `sr` — sample rate in Hz (default **48000**). Pass your input audio's rate:
    the bundled test files are 44.1 kHz, so a bare call would render them at the
    wrong rate — use `sr=sr` from `load_audio_mono` / `load_wav`.
  - `bs` — render block size in samples (default 128).
  - `out_duration` — render length in seconds; defaults to the input duration.
    For varispeed with ratio < 1, use `len(input_buf) / sr / ratio`.
  - `all_outputs` — `False` (default) returns the first output channel as a 1-D
    array; `True` returns **all** output channels as a `(n_outputs, n_samples)`
    2-D array, so a `process` that emits several probes can be unpacked:
    `smoothed, slope = run_faust(..., all_outputs=True)`.
- **A pybind module** — `make -f faust.make DSP=<name> DSP_LIB_DIR=<dir>` from
  `python/` compiles one `.dsp` to a stateful pybind module for chunk-by-chunk
  driving from Python.

**Testbench pattern — time-varying control inside the block.** `run_faust` holds
its `params` constant for the whole render, so to exercise *modulation* (an ADSR
sweeping a filter cutoff, an LFO, a gate) without building a pybind module,
generate the control signal **inside the `.dsp`** and expose it as an extra probe
output. The numpy side supplies the audio source and reads the probes back with
`all_outputs=True`. `projects/keybass_1/filter_sweep.dsp` is the worked example: a
steady numpy pulse is the input; the `.dsp` derives a one-shot gate from the
sample clock (`(ba.time/ma.SR) >= t_on & …`), runs `en.adsre`, maps it to a cutoff
(`offset * pow(2, env_oct*env)` — see the exponential/V-oct note below), and emits
`(filtered, env, cutoff, gate)` so `filter_sweep_demo.py` plots every stage
time-aligned with the shared-x toolset. Reach for the pybind route only when the
control itself must originate in Python (true sample-by-sample external drive).

Two conventions this pattern leans on: **testbenches use the diagnostic toolset**
(shared-x panels + `install_x_zoom` + `mark_events`), not ad-hoc matplotlib, and
they **return the rendered audio buffer** so it can be auditioned with `play()` at
a breakpoint. **Control→cutoff is exponential**: synth filter envelopes modulate
in the log-frequency (semitone/octave) domain — sum all modulation in
semitones/octaves, then `* pow(2, …)` to Hz just before the filter (Faust filters
take `fc` in Hz). A `min(ma.SR/6.5, …)` clamp keeps `moog_vcf`-family cutoffs in
their stable range.

### 3. A compiled C++ block or full graph (pybind)

The realistic path: the code under the plots **is the firmware code**. Build the
graph's pybind module from its project (`make -f <graph>.make`), then drive it:

```python
from build.pybind_pitch_shifter import pitch_shifter
ps = pitch_shifter(); ps.init(sr)
ps.set_param('lc.pitch_ratio', 0.5)
out = ps.process_chunk(audio.astype(np.float32))   # (N, kNumOutputs)
P    = ps.get_buffer('yd.P', N)                     # tap ANY node by name
conf = 1.0 - ps.get_buffer('yd.aperiodicity', N)
```

`process_chunk` feeds the whole file as one chunk (or chunk-by-chunk — same code
path), and `get_buffer('block.port', n)` returns a NumPy view of any internal
signal for plotting. This probe-by-name tap is the core diagnostic affordance —
every block exposes its internal state as extra outputs. Build mechanics (the
`.graph` format, generated header, manifest) live in
`audio_graph_architecture.md`; this doc is just how to *drive and plot* it.
