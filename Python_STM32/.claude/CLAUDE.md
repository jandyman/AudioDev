# Python_STM32 — Claude Context

Active hub for STM32 audio-DSP development. Shared C++/Faust DSP blocks build two
ways from one source: natively via pybind11 (fast iteration) and arm-none-eabi
for the STM32H750. Cross-project C++/Python conventions live in the AudioDev-root
`.claude/CLAUDE.md`; this file holds what's specific to Python_STM32.

## Folder structure

- `projects/<algo>/` — one self-contained folder per algorithm: its Faust `.dsp`,
  hand-written C++ block `.cpp/.h`, the `.graph`, the pybind wrapper, demo/lab
  Python, and a thin `<graph>.make`. Active: `pitch_shifter/`.
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

## Current state — pitch shifter (native, working)

Output-side pitch shifter; `pitch_ratio` 0.5 = octave-down. Pipeline
(`projects/pitch_shifter/pitch_shifter.graph`):

```
audio → lpf (input_lpf, Faust)
      → zc  (zero_crossing_detector, Faust) → loop_controller (zc_impulse)
      → atk (attack_detector, Faust)        → loop_controller (trigger + active_gain)
      → hr  (harmonic_rejector, C++)        → loop_controller (P / sigma / qualified gate)
      → dtd (triple_tap_delay, Faust)
loop_controller → 3 tap delays + 3 gains → dtd → mixer3 (C++ summer) → audio_out_r
audio_out_l = dry input
```

- **attack_detector** (Faust): boosted-threshold edge detector. `fast` (peak-hold
  + accel release) vs `ref` (two-stage-attack follower of fast); fire on a rising
  edge of `fast/ref` across a LIVE threshold `k` that rests at `k_nom`, snaps to
  `k_boost` on each fire, then decays back — an overridable holdoff, no debounce.
  A parallel dive path (slow/hold envelopes → `dive_strength` → `active_gain`)
  drives note muting downstream; kept separate from the trigger. Tuned in
  `attack_detector_lab.py` (pure Python), then ported to Faust (verified lab == Faust).
- **loop_controller** (C++): owns all delay ramps + tap gains across three taps
  (active / loop-incoming / attack roles, dynamic across {0,1,2}); 1 ms attack
  fade-in / 10 ms fade-out; gates non-attack taps by `active_gain` (by ROLE, not
  a fixed index); bailout + loop crossfades.
- **mixer3** (C++): stateless weighted summer — all muting is upstream in loop_controller.

Demos: `pitch_shifter_demo.py` (full pipeline + probe plots, saves WAV),
`attack_detector_lab.py` (pure-Python detector experimentation, painless to port to Faust).

## Conventions (Python_STM32-specific)

- A graph project is self-contained in `projects/<algo>/`; a block's default home
  is that folder — promote to `dsp_faust/`/`dsp_cpp/` only on genuine reuse.
- Every block exposes internal state as extra probe outputs so Python can tap any
  node (root CLAUDE.md "Signal node probing").
- `audio-graph-python/` (a sibling of Python_STM32) is DEPRECATED reference code —
  do not place new work there.

## Next steps

- Listen to the rebuilt pitch-shifter output; optional startup guard for the
  file-start fire cluster.
- Distribute per-block docs as sibling `.md` files assembled by `graph_compiler`.
- STM32 firmware build of the pitch shifter (currently native-only).
