# Embedded DSP Subsystem — Concept

The platform-neutral concept and design thinking behind the AudioDev embedded-DSP
ecosystem. These are the *ideas* — the goals, the graph/module abstraction, the
development methodology — independent of any particular MCU. The concrete
realization lives in `Python_STM32/` (STM32H7-specific firmware, blocks, and build
tooling); this folder is where the reusable, target-agnostic reasoning is kept.

It began as the original vision document. The project has since built a working
system, and several early decisions were inverted by what was learned. This README
reconciles the two: what became real, what changed, and what still stands.

## What became real (and differs from the original concept)

- **C++/Faust-first, not SciPy-first.** The original plan was to prototype
  algorithms in SciPy/NumPy and *generate* embedded C++ from them. That inverted:
  DSP is now written once in **C++ or Faust**, and Python is a **test harness only**
  (drive pybind11-wrapped blocks, generate signals, plot). No DSP logic lives in
  Python.
- **Faust is a first-class implementation language** for feedback-dense blocks
  (resonators, IIRs, coupled envelope followers). The original docs predate Faust
  entirely.
- **Static graph, compiled from a text netlist — not a runtime object API.** The
  original `Module`/`Graph` Python classes (see `Module Spec.md`, `core.py`) that
  were connected and topologically sorted *at runtime* were replaced by an
  **S-expression `.graph` file compiled into concrete C++** at design time. The
  abstraction survived; the runtime framework did not.
- **One source, two targets.** The "seamless transition from prototype to embedded"
  goal was realized more strongly than envisioned: the *same* C++ compiles for
  arm-none-eabi and natively via pybind11. The code under test *is* the firmware —
  there is no separate simulation, and no codegen step to distrust.
- **Flat, single-rate signals — for now.** The multichannel `DSP Signal` / `Signal
  Spec` model was set aside for a single-sample-rate, one-buffer-per-signal model
  (multichannel = N parallel signals). See "Still live," below — this one is coming
  back.

## Still live and platform-neutral (worth carrying forward)

These ideas were never superseded and are not written down elsewhere:

- **Development methodology** — the two lifecycles (algorithm-development and
  module-development) in `Project Concept.md`. A general "how you work" process,
  target-independent.
- **Signal-spec propagation** — the design analysis in `Graph Preparation Design.md`
  of pushing channel-count / sample-rate through a graph (bidirectional, format
  transforms, constraint solving). Deferred when the system went single-rate, but
  **newly relevant**: the per-string program (`Python_STM32/docs/per_string_roadmap.md`)
  is 8-channel, which walks straight back into this problem.
- **Embedded buffer reuse** — the lifetime-analysis / last-reader / graph-coloring
  memory-reuse thinking in `Graph Preparation Design.md`. The current architecture
  only names this as a "future optimizer pass"; the actual algorithm sketch is here.
- **System-state taxonomy** — module-definition vs. graph-configuration vs.
  runtime-processing state, and why separating them enables per-category
  optimization (`Project Concept.md`).
- **Visual designer** — the schematic-editor concept and the principle that a
  diagram can *generate* the graph, with graphical tooling always supplementary and
  never load-bearing (`visual_designer_poc/`).
- **Python coding standards** — `Python Coding Standards.md`; Python is still the
  live test harness, so these conventions still apply.

## File status

| File | Status |
|------|--------|
| `Project Concept.md` | Concept — mostly current; workflow/signal sections annotated inline where superseded. |
| `Graph Preparation Design.md` | Concept — still valuable (signal-spec propagation, buffer reuse). |
| `Python Coding Standards.md` | Current — live conventions for the Python harness. |
| `visual_designer_poc/` | Aspiration — unbuilt, concept intact. |
| `Module Spec.md`, `core.py`, `test_core.py` | Historical — the superseded runtime `Module`/`Graph` framework; kept as record. |
| `Development Journal.md` | Historical — session-by-session decision log for code that no longer exists. |

For the concrete, current architecture see `Python_STM32/docs/audio_graph_architecture.md`
and the two `.claude/CLAUDE.md` files.
