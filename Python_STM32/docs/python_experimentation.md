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

**Loading.** `load_audio_mono(path)` returns `(sample_rate, samples)` with
`samples` a float64 mono array in `[-1, 1]` (int16/int32 are scaled; multi-
channel is downmixed to channel 0). Input WAVs live in the repo-root
`test_audio/` directory.

**Saving.** Output WAVs go in the repo-root `test_audio_out/` directory, named
`<input_stem>_<tag>.wav` — the input stem preserved verbatim (spaces, case),
the tag describing the transform (e.g. `Fourth Test_pitch_shifted_-5st.wav`).
Never write generic names like `out.wav`. Do **not** save matplotlib PNGs next
to the audio — use the interactive window.

**Buffer-centric play/save.** `projects/pitch_shifter/audio_buf_tools.py` adds
`load_wav`, `save_wav`, `output_path(input_path, tag)`, and `play(buf, sr)`
(in-process audition via `sounddevice`) for slicing and listening to numpy
buffers without writing files. It's project-local for now (promote to
`python/lib/` when a second project uses it).

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
`pan_frac` (fraction of the visible width moved per notch, default 0.20).

### Useful panel patterns

- **Event markers** — `ax.axvline(t[idx], color='green', lw=0.8, alpha=0.35)` per
  event index; big, semi-transparent lines read clearly when zoomed out.
- **State tinting** — `ax.axvspan(t[a], t[b], color=c, alpha=0.15, lw=0)` to shade
  spans where a selector/mode is active.
- **Overlay on a twin axis** — put a derived quantity (f0, confidence) on
  `ax.twinx()` so it shares the time axis but keeps its own y scale.
- **Probe panels** — plot any internal node tapped by name (next section); e.g.
  the YIN period gated by confidence, or the loop controller's latency.

Worked examples: `projects/pitch_shifter/pitch_shifter_demo.py` (5-panel
pipeline) and `projects/yin/yin_demo.py` (probes + a lag-domain snapshot).

## Three ways to put DSP under the plots

### 1. Pure Python (numpy)

Quickest for sketching an idea or building ground truth. Per the architecture,
this is a **temporary prototyping step** before C++/Faust — don't let real DSP
settle here. Generate a signal, process it in numpy, plot. (Example:
`yin_validate.py`'s reference YIN is pure numpy used only as ground truth.)

### 2. A Faust block

Two routes:

- **One-shot, no build** — `audio_buf_tools.run_faust(input_buf, dsp_path,
  params={...})` does a single `dawdreamer` round-trip and returns the output
  buffer. Params are addressed by short label; `run_faust` sets
  `faust_libraries_paths` to the `.dsp`'s own directory first so sibling
  `.lib`/`.dsp` imports resolve regardless of cwd. Best for auditioning a block
  in isolation.
- **A pybind module** — `make -f faust.make DSP=<name> DSP_LIB_DIR=<dir>` from
  `python/` compiles one `.dsp` to a stateful pybind module for chunk-by-chunk
  driving from Python.

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
