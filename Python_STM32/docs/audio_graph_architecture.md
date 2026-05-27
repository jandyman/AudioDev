# Audio Graph Architecture

This document describes the design-time audio graph architecture used in this
project. The scope is broader than the folder name suggests: these ideas apply
to any C++ DSP system that needs to run identically on embedded targets and on
a host machine for offline testing.

## Central Concepts

DSP processing on the STM32 or other embedded targets is far more efficient if
done on blocks of samples as opposed to per-sample processing. This architecture
describes a system of Blocks and Graphs that operate on chunk-based data, passing
data via fixed-size buffers. The buffer size aligns with the DMA half-buffer size
of the codec, trading off efficiency vs. latency. Per-sample techniques and
feedback (IIR filters, etc.) happen within blocks, not across them.

The chunk size is a build-time parameter — set it to the DMA half-buffer size for
embedded realtime, or to a large value for offline file-based processing in
Python. The same C++ source runs at any chunk size; only the buffer dimensions
change.

## Goals

- One C++ source tree compiles to multiple targets (STM32 firmware, host-native
  via pybind11) with no platform-specific logic inside DSP blocks.
- Graph topology is fixed at design time. The "graph" is just a sequence of
  chunk-processing function calls on static state — no node registry, no
  virtual dispatch, no runtime graph traversal.
- Any signal in the graph can be inspected from Python (host) or via RTT
  (target) by name, without restructuring the graph.
- The DSP source for an algorithm is byte-identical across all run modes.

## Processing model

The system processes audio as a network of **Blocks** and **Graphs** connected
by their input and output ports.

- A **Block** is a unit of DSP computation. It has zero or more input ports
  and one or more output ports. Each port carries a single signal.
- A **Graph** is a collection of Blocks (or other Graphs) wired together. A
  Graph is itself a Block at the level above — same external interface, same
  instantiation rules. Hierarchy is free.
- **Buffers** are not user-declared. The graph compiler generates one per
  signal in the graph (internal and external) and shares it across all readers.
- **Parameters** come in two flavors: design-time (baked into the generated
  code) and runtime (settable via control after the graph is running).

All buffers are at the build's configured chunk size, and the whole system runs
at a single sample rate.

## Run modes

Three run modes share the same DSP code:

1. **STM32 realtime** — codec ISR drives chunk-by-chunk processing.
2. **STM32 offline** — input buffer in flash → run graph → dump output via RTT.
   Slow but bit-exact to firmware behavior. Useful for verification.
3. **Native offline (pybind11)** — Python feeds NumPy arrays through, reads
   any buffer by name from the graph. The fast path for algorithm iteration.

**Native realtime is not a target.** The only deployment target is embedded;
the only purpose of host-native execution is fast iteration during development.

## Naming convention

**Everything is snake_case.** Block type names, filenames (`.cpp`, `.dsp`, `.h`),
C++ class names, and Python class names are all identical snake_case strings.
No conversion is needed anywhere — the type name in the graph file is the
filename without extension and is also the C++ class name.

Examples: `harmonic_rejector`, `loop_controller`, `dual_tap_delay`, `mixer2`.

The generated pipeline class takes the graph's name directly (e.g. a graph
named `pitch_shifter` produces `class pitch_shifter`).

## Blocks

A block is a plain C++ class.

- No virtual functions, no inheritance from a framework base class.
- Chunk-based interface: `process(const float* const* inputs, float* const* outputs, int n)`.
  Each call consumes and produces `n` samples per port. Per-sample / feedback
  techniques (IIRs, Faust-style algorithms) live inside the block; the
  inter-block contract is always chunk-based.
- All state in fixed-size member arrays. No allocation in `process()`.
- Constructor allocates and initializes; `process()` is pure compute.
- No awareness of platform (no `#ifdef STM32`, no calls into a `Platform::*`
  namespace from inside DSP code).

Port names, types, and parameter declarations live in a `@block` marker comment
at the top of the source file. The graph description references those names but
does not redeclare them.

## Block source files

Each block is a single source file. The `@block` marker and the implementation
live together in that file.

**C++ block** — `harmonic_rejector.cpp` + `harmonic_rejector.h`:
```cpp
/* @block
(define-block harmonic_rejector
 (inputs in)
 (outputs x_filt_0 ... selected_filter P sigma_sel qualified)
 (params (fc_0 :default 60) ...))
*/

#include "harmonic_rejector.h"
// ... C++ implementation ...
```

**Faust block** — `input_lpf.dsp` only (no sibling `.cpp`):
```faust
/* @block
(define-block input_lpf
 (inputs in)
 (outputs out)
 (params (fc :default 10000)))
*/

import("stdfaust.lib");
fc = hslider("fc", 10000, 100, 20000, 1);
process = fi.lowpass(2, fc);
```

The `@block` marker lives in the `.dsp` file for Faust blocks. The Faust
compiler ignores the `/* */` comment. No sibling `.cpp` stub is needed.

The graph compiler detects Faust vs C++ by file extension: if `type.dsp`
exists, the block is Faust; if only `type.cpp` exists, it is C++. In both
cases the `@block` marker is read from that same file.

**One block per file** is the convention. The type name, filename (without
extension), and C++ class name are always identical.

## Block location

**Private blocks** (used by one project) live in the project folder alongside
the `.graph` file — e.g. `pitch_shifter_demo/harmonic_rejector.cpp`. The graph
compiler always searches the graph file's own directory first, so no
configuration is needed.

**Shared blocks** (proven to be genuinely reused across multiple projects) live
in a shared library (`dsp_cpp/`, `dsp_faust/`). Only promote to shared after
real cross-project reuse is observed — never speculatively. The cost of
regenerating "the same" block for two projects is lower than the cost of a
shared dependency that almost-fits-both.

Currently shared (genuinely generic): `biquad`, `eq_design`, `faust_minimal.h`,
`faust_processor_wrapper.h`.

## Block discovery

The graph compiler finds blocks by name, not by scanning. For each block type
referenced in a graph:

1. Convert the type name to a filename (it already is one — snake_case, no
   conversion needed).
2. Search for `type.dsp` (Faust) or `type.cpp` (C++) in the search path.
3. Read the `@block` marker from the found file.

The search path consists of:
- The graph file's own directory (always first, implicit).
- Any `(include-dir PATH)` directories declared in the graph file.

Nothing is hardcoded in the compiler. A graph that uses only local blocks needs
no path declarations at all.

## Buffers

Buffers are fixed-size sample arrays at the build's configured chunk size.
The user never declares them — the compiler generates one per signal from the
connection structure, shared by all readers.

Default: no buffer reuse. Every buffer in the graph is automatically inspectable
from Python by name. Buffer reuse is a future optimizer pass if memory pinches.

Delay lines and other multi-sample storage internal to a block are block-private
state, not graph buffers.

## Graphs

A graph is a collection of port declarations, block instantiations, and
connections.

- **Acyclic.** No graph-level feedback. Feedback belongs inside blocks.
- **Hierarchical.** A graph is a block at the level above. Instantiating a
  graph uses the same `(block ...)` form.
- **Call order is derived.** Humans describe connections; the compiler
  topologically sorts to derive the call order.
- **Encapsulation.** You cannot reach inside an instantiated subgraph.

## Graph description language

Graphs are described in a small S-expression dialect. All names are snake_case.

```lisp
(graph pitch_shifter
 (include-dir "../shared_blocks")   ; optional: add a directory to the search path
 (port input audio_in lpf.in)       ; external input, routed to lpf.in
 (port output audio_out mixer.out)  ; external output, fed from mixer.out
 (block lpf input_lpf :fc 10000)    ; instance lpf of type input_lpf, fc param = 10000
 (block zc zero_crossing_detector)
 (block mixer mixer2)
 (connect lpf.out zc.in mixer.in1)  ; fan-out: lpf.out feeds two inputs
 (connect zc.zc_out mixer.in2))
```

Keywords:
- `(include-dir PATH)` — add a directory to the block search path. PATH is
  relative to the graph file's location.
- `(graph NAME ...)` — define a graph (snake_case name).
- `(port input NAME dest1 [dest2 ...])` — external input, routed to one or more
  block inputs. Fan-out by listing multiple destinations.
- `(port output NAME source)` — external output fed from one internal source.
- `(block INSTANCE TYPE :param value ...)` — instantiate a block. INSTANCE is
  the local name; TYPE is the block type (= filename = class name).
- `(connect SOURCE dest1 [dest2 ...])` — wire one source to one or more
  destinations. Fan-out by listing multiple destinations.

Formatting: spaces only, no tabs, no column alignment. Single space between
tokens.

## Code generation

The graph compiler (`graph_compiler.py`) reads the `.graph` file and emits a
single `#pragma once` C++ header:

- `#include` directives for each block type (the generated Faust `.cpp` or the
  block's `.h`).
- Static buffer arrays for every signal (`float buf_NAME[CHUNK_SIZE]`).
- Block instances as class members.
- `void process_chunk(const float* in, float* out, int n)` — calls each block's
  `process()` in topological order, passing named intermediate buffers.
- `const float* get_buffer(const char* name)` — returns a pointer to any named
  buffer, for probing from Python or RTT.
- `void set_param(const char* path, float value)` — routes `"inst.param"` paths
  to the appropriate block's `set_param()`.

The generated header is a build artifact — regenerate it from the `.graph` file
whenever the graph changes.

`CHUNK_SIZE` is a compile-time `#define`. The same source compiles at any chunk
size; buffer dimensions are the only thing that changes.

## Faust's role

Faust is a permanent implementation language for blocks where its declarative
feedback semantics earn their keep.

Reach for Faust when:
- A block has a multi-channel state machine with several feedback signals.
- A block has multiple coupled envelope followers or complex IIR structures.
- A block has delay-modulation logic where Faust's delay-line primitives and
  `~` feedback express the algorithm concisely.

Stick with plain C++ when:
- The block is a fixed-coefficient filter (biquad, one-pole).
- The block is straightforward chunk-wise math (gain, mixer, sum).
- The block is delay-line storage with no feedback path.

Rule of thumb: if you find yourself writing many `prev_*` member variables,
Faust is probably the right tool.

Faust's runtime never ships to the STM32. Faust compiles to plain `.cpp` files
that are called in the chunk-by-chunk processing sequence. Faust blocks expose
the same `process(const float* const*, float* const*, int n)` interface as C++
blocks via `FaustProcessorWrapper` (in `bindings/faust_processor_wrapper.h`).

## Build

From `Python_STM32/python/`:

```bash
# Rebuild Faust C++ for a block whose .dsp changed:
make -f faust.make DSP=dual_tap_delay DSP_LIB_DIR=pitch_shifter_demo

# Rebuild the full pipeline (runs graph compiler + compiles C++):
make -f pitch_shifter.make
```

The graph compiler runs automatically as a make dependency when the `.graph`
file changes.

## Control

Parameters are setters on blocks. Each block declares its control surface once
in its `@block` marker (name, default).

- **Design-time** parameters (sample rate, buffer sizes, fixed filter orders)
  are baked into the generated code at compile time.
- **Runtime** parameters (cutoffs, gains, pitch ratios) are settable via
  `set_param("inst.param", value)` after the graph is running.

## What is still TBD

- Hierarchical graphs (subgraph-as-block) — the description language supports
  it syntactically but the compiler does not yet implement it.
- Buffer reuse optimizer pass — deferred until memory pressure requires it.
- `(probe ...)` form — only needed alongside buffer reuse; deferred.
- How the buffer directory is exposed on STM32 for RTT inspection — likely a
  linker section the RTT bridge can iterate.
- Wiring the generated `pitch_shifter` class into the STM32 firmware codec ISR.
