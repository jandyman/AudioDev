# Python_STM32 — Claude Context

Active hub for STM32 audio-DSP development. Shared C++/Faust DSP blocks build two
ways from one source: natively via pybind11 (fast iteration) and arm-none-eabi
for the STM32H750. Cross-project C++/Python conventions live in the AudioDev-root
`.claude/CLAUDE.md`; this file holds what's specific to Python_STM32.

## Folder structure

- `projects/<algo>/` — one self-contained folder per algorithm: its Faust `.dsp`,
  hand-written C++ block `.cpp/.h`, the `.graph`, the pybind wrapper (generated
  from a template), demo/lab Python, and a thin `<graph>.make`. Active:
  `pitch_shifter/`, `yin/`.
- `projects/sandbox/` — scratch space for Python experimentation (tracked in git;
  only build artifacts ignored). Keeps the same 2-levels-deep paths so shared
  tooling imports work verbatim. Copy `_template.py` to start. See
  `docs/python_experimentation.md`.
- `python/` — shared host tooling: `graph_compiler.py`, `graph_build.mk`,
  `faust.make`, `bindings/`, `lib/`, and the RTT hardware-test scripts.
- `dsp_faust/`, `dsp_cpp/` — shared block libraries (promote here only on real reuse).
- `firmware/` — STM32 firmware (seed_h750).
- `docs/audio_graph_architecture.md` — the framework reference (graph format, build, conventions).

## Build (native, from a project folder)

Under the scipy conda env:
```bash
source ~/miniforge3/etc/profile.d/conda.sh && conda activate scipy
cd projects/pitch_shifter && make -f pitch_shifter.make
```
Self-contained and dependency-correct (generates the Faust cpp + pipeline header,
`-MMD` header tracking, per-TU compile + link — edit any source and the right
things rebuild). The thin `<graph>.make` just declares `MODULE`/`FAUST_BLOCKS`/
`DSP_CPP` and includes `../../python/graph_build.mk`. `faust.make` (run from
`python/`) is a separate tool for standalone single-block pybind modules used by
lab/diagnostic scripts. Full mechanics: `docs/audio_graph_architecture.md`.

## Current state — pitch shifter (native, working; YIN-driven loop)

Output-side pitch shifter; `pitch_ratio` 0.5 = octave-down (runtime param via
`set_param('lc.pitch_ratio', …)` — no recompile). **Validated flawless across all
the troublesome bass files** (descending-into-low-E, 2H-dominant notes). Pipeline
(`projects/pitch_shifter/pitch_shifter.graph`):

```
audio → lpf (input_lpf, Faust)
      → atk (attack_detector, Faust)   → loop_controller (trigger + active_gain)
      → yd  (yin_detector, C++)        → loop_controller (P + aperiodicity)
      → dtd (triple_tap_delay, Faust)
loop_controller → 3 tap delays + 3 gains → dtd → mixer3 (C++ summer) → audio_out_r
audio_out_l = dry input
```

The old peak-clock apparatus (pitch_detector LPF bank, zero_crossing_detector,
target-latency candidate search) was **deleted** — replaced by YIN's precise
period. With an accurate P, a read jump of exactly k·P is phase-matched by
periodicity, so the loop POINT no longer matters, only that the jump length ≈ P.

- **attack_detector** (Faust): boosted-threshold edge detector. `fast` vs `ref`
  envelopes, fire on a rising edge across a LIVE threshold; parallel dive path →
  `active_gain` for note muting. Tuned in `attack_detector_lab.py`, ported to Faust.
- **yin_detector** (C++): decimated brute-force YIN — ÷16 anti-alias FIR decimator
  → power-of-two decimated ring → difference fn / cumulative-mean-normalized diff
  / first-below-threshold pick / parabolic interp. Emits `P` (full-rate samples) +
  `aperiodicity` (low = confident). Robust to weak-fundamental/2H-dominant notes.
  Built standalone first in `projects/yin/`; pitch_shifter pulls it in cross-
  project via the graph_build.mk `BLOCK_DIRS` hook (no file move). ~1–2% of a
  500 MHz M7/voice; chunk-size agnostic.
- **loop_controller** (C++): owns all delay ramps + tap gains across three taps
  (active / loop-incoming / attack roles, dynamic across {0,1,2}); 1 ms attack
  fade-in / 10 ms fade-out; gates non-attack taps by `active_gain` (by ROLE).
  Loop policy: latency past the 50 ms operating point + confident P + lockout
  expired → jump read by DT−P (**k=1**). Lockout is ABSOLUTE (crossfade + settle,
  7 ms), NOT a multiple of P. Latch P while aperiodicity≤0.4, hold through dips,
  invalidate on attack (new note waits ~50 ms for YIN; attack tap covers onset).
  Tuning knobs = single constants in `loop_controller.h`.
- **mixer3** (C++): stateless weighted summer — all muting is upstream in loop_controller.

Demos: `pitch_shifter_demo.py` (full pipeline + probe plots, saves WAV),
`yin_validate.py` (score yd.P vs full-rate YIN truth per note),
`projects/yin/yin_demo.py` (standalone YIN probe plots),
`attack_detector_lab.py` (pure-Python detector experimentation).

## Conventions (Python_STM32-specific)

- A graph project is self-contained in `projects/<algo>/`; a block's default home
  is that folder — promote to `dsp_faust/`/`dsp_cpp/` only on genuine reuse.
- Every block exposes internal state as extra probe outputs so Python can tap any
  node (root CLAUDE.md "Signal node probing").
- `audio-graph-python/` (a sibling of Python_STM32) is DEPRECATED reference code —
  do not place new work there.

## Next steps

- **STM32 firmware port of the YIN-driven pitch shifter** (currently native-only)
  — the immediate focus. `CHUNK_SIZE` becomes the real SAI/DMA audio block size
  (a compile-time choice); `lc.pitch_ratio` stays a runtime control. The DSP is
  identical across targets; expect work in the thin platform layer + wiring the
  generated graph into the seed_h750 render callback.
- Doc debt: `loop_controller.md` (and `pitch_shifter.md`) still describe the old
  ZC/peak-clock apparatus — rewrite to the k·P policy.
- Optional startup guard for the file-start fire cluster (note 0 at t=0).
- Decimator stopband verification (swept-tone script) + per-block `.md` docs
  assembled by `graph_compiler`.
