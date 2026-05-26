# Audio Graph Architecture

This document describes the design-time audio graph architecture used in this
project. The scope is broader than the folder name suggests: these ideas apply
to any C++ DSP system that needs to run identically on embedded targets and on
a host machine for offline testing.

## Central Concepts

DSP processing on the STM32 or other embedded targets is far more efficient if 
on blocks of samples as opposed to per sample processing like you'd do in pure 
data or Faust. So this architecture describes a system of Blocks and Graph that 
operate on this chunk based data, passing data via buffers of data. The buffer 
size will almost align with the DMA size of the codec transfers, it's a tradeoff
of efficiency vs. latency. This is a well known technique for efficients Audio 
DSP. Per sample techniques and feedback such as are required for IIR filter and 
such happen within blocks. At some future time we may incorporate feedback at a 
guestural time scale, but that is future development.

The chunk size is a build-time parameter — set it to 1 for debug or test, to
the DMA half-buffer size for embedded realtime, or to something very large for
offline file-based processing integrated with Python. The same C++ source runs
at any chunk size; only the buffer dimensions change.

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
  and one or more output ports. Each port carries a single signal. Port names
  and types come from the block's C++ class.
- A **Graph** is a collection of Blocks (or other Graphs) wired together. A
  Graph is itself a Block at the level above — same external interface, same
  instantiation rules. Hierarchy is free.
- **Buffers** are not user-declared. Python generates one per signal in the
  graph (internal and external) and shares it across all readers. The user
  writes blocks and connections; Python allocates the storage.
- **Parameters** come in two flavors: design-time (baked into the generated
  code) and runtime (settable via control after the graph is running).

All buffers are at the build's configured chunk size (DMA half-buffer for
embedded realtime; smaller or larger for debug or batch builds), and the
whole system runs at a single sample rate. Multi-rate processing isn't on the
roadmap; if we ever need downsampled subgraphs we'll design it then.

## Run modes

Three run modes share the same DSP code:

1. **STM32 realtime** — codec ISR drives chunk-by-chunk processing.
2. **STM32 offline** — input buffer in flash → run graph → dump output via RTT.
   Slow but bit-exact to firmware behavior. Useful for verification.
3. **Native offline (pybind11)** — Python feeds NumPy arrays through, reads
   any buffer by name from the directory. The fast path for algorithm
   iteration.

**Native realtime is not a target.** Max/MSP, JUCE, and similar plugin hosts
are off the table. The only deployment target is embedded; the only purpose
of host-native execution is fast iteration during development.

## Blocks

A block is a plain C++ class.

- No virtual functions, no inheritance from a framework base class.
- Chunk-based interface: each `process()` call consumes and produces a buffer
  of N samples per port, where N is the build's configured chunk size.
  Per-sample / feedback techniques (IIRs, Faust-style algorithms) live inside
  the block; the inter-block contract is always chunky.
- All state in fixed-size member arrays. No allocation in `process()`.
- Constructor allocates and initializes; `process()` is pure compute.
- No awareness of platform (no `#ifdef STM32`, no `#ifdef DEBUG`, no calls
  into a `Platform::*` namespace from inside DSP code).

Port names, types, and parameter declarations form the block's external
interface and live in a block definition marker at the top of the source
file (see Block source files). The graph description references those names
but does not redeclare them.

## Block source files

Block definitions live alongside their C++ source in the same file. Each
block source file contains:

- A **block definition** — the S-expression interface used by the graph
  compiler (port names and types, parameter declarations, anything the
  graph needs to know to wire this block in). Embedded as a marked
  C-style comment near the top of the file.
- The **C++ implementation** — the class, chunk-based `process()` method,
  state, parameter setters.

The marker form is provisional but follows this shape:

```cpp
/* @block
(define-block Biquad
  (inputs (audio in))
  (outputs (audio out))
  (params
    (b0 :default 1.0)
    (b1 :default 0.0)
    (b2 :default 0.0)
    (a1 :default 0.0)
    (a2 :default 0.0)))
*/

#include "biquad.h"
// ... C++ implementation ...
```

The build pipeline extracts `@block` markers from imported source files to
register block types with the graph compiler. The C++ portion compiles
normally; the marker is a comment as far as the C++ compiler is concerned.

**One block per file is the default convention.** Multiple `@block` markers
in one file are allowed for families of closely related blocks (variants
that share helpers), but the default is one block per file for
discoverability.

**Faust blocks pair two files.** The Faust algorithm lives in a `.dsp` file
with its own tooling; a sibling `.cpp` file carries the `@block` definition
and a minimal adapter around Faust's generated `compute(int n, float**
inputs, float** outputs)`. Because the block API is also chunk-based, the
adapter is just argument adaptation — no shape change, no per-sample
wrapping. Both files are real source in their native language — no
embedded-string tricks, no preprocessor to split sections. The Faust file
uses Faust's syntax checkers and tools (`faust2sndfile`, etc.) directly;
the C++ file uses C++ tooling.

Mixing C++ and Faust within a single block source file is not supported.
When a problem has both feedback-dense and straight-through parts, split it
into two blocks at the graph level instead.

## Buffers

Buffers are fixed-size sample arrays at the build's configured chunk size.
The user never declares them — Python generates buffers from the connection
structure: one per signal, shared by all readers.

- Default: no buffer reuse. Memory is cheap on the STM32H750; debuggability
  is gold. Every buffer in the graph is automatically inspectable from Python
  (host) or via RTT (target).
- Buffer reuse becomes an optional optimizer pass if memory ever pinches.

Delay lines and other multi-sample storage internal to a block are
block-private state, not buffers in the graph-description sense.

## Probes

A probe is conceptually a no-op block with one input whose purpose is to pin
a buffer (prevent reuse).

Until buffer reuse exists, every buffer is automatically persistent, so
probes are not needed as a syntactic construct yet. When we add a reuse
optimizer pass, the `probe` form will mark which buffers must escape reuse.

## Graphs

A graph is a collection of port declarations, block instantiations, and
connections.

- **Acyclic.** No graph-level feedback. The use cases that motivate audio
  feedback (resonators, comb filters, Karplus-Strong) need sample-resolution
  feedback, which belongs inside a block. Cross-block feedback would
  replicate what Faust already does well inside a block, with worse latency.
- **Hierarchical.** A graph IS a block at the level above. Instantiating a
  graph as a block uses the same `(block ...)` form; the graph's external
  port declarations become the block's external port names.
- **Call order is derived, not specified.** Humans describe what connects to
  what; Python topologically sorts to derive the call order.
- **Connections are local in scope.** You cannot reach inside an instantiated
  subgraph to address its internal blocks. Encapsulation is preserved.

## Description language

For small graphs, English in a prompt to Claude is sufficient. SimpleEQ proved
this works.

For larger graphs, a tiny S-expression dialect. Keywords:

- `(import SOURCE ...)` — make block types defined in another source file
  visible to this graph. The graph compiler scans the named files for
  `@block` markers and registers them. Distinct from C++ `#include`,
  which the generated `.cpp` issues for actual code; `import` is purely
  for block-type discovery at graph-compile time. Exact form provisional.
- `(graph NAME ...)` — define a graph.
- `(port input NAME dest1 [dest2 ...])` — declare an external input port of
  the graph and route it to one or more internal block input ports. Fan-out
  is expressed by listing multiple destinations.
- `(port output NAME source)` — declare an external output port of the graph,
  fed by one internal source.
- `(block NAME TYPE :param value ...)` — instantiate a Block (or another
  Graph) inside the current graph.
- `(connect SOURCE dest1 [dest2 ...])` — wire one internal source to one or
  more internal destinations. Fan-out is expressed by listing multiple
  destinations.

Port-to-block routing and connections are conceptually identical: all
consumers of a signal read from the same buffer the producer wrote. There are
no buffer copies — `(port input ...)` and `(connect ...)` both compile to
shared-buffer reads.

Port references:

- `audio_in` — refers to the current graph's external port `audio_in`.
- `hr.out` — refers to block `hr`'s `out` port.

Example — the pitch-shifter pipeline (block and port names are illustrative;
concrete names will be settled as we migrate the blocks):

```
(graph pitch_shifter
  (port input audio_in hr.in)
  (port output audio_out mix.out)
  (block hr HarmonicRejector :sr 48000)
  (block zc ZCDetector :sr 48000)
  (block loop LoopController :sr 48000 :pitch_ratio 0.5)
  (block delay DualTapDelay :sr 48000)
  (block mix Mixer2)
  (connect hr.out zc.in delay.in)
  (connect zc.impulse loop.zc_in)
  (connect loop.tap1_delay_ms delay.tap1_delay_ms)
  (connect loop.tap2_delay_ms delay.tap2_delay_ms)
  (connect loop.gain1 mix.gain1)
  (connect loop.gain2 mix.gain2)
  (connect delay.tap1 mix.in1)
  (connect delay.tap2 mix.in2))
```

Conventions:

- Spaces only. Single space between tokens; no column alignment, no tabs.
- Keyword args use `:key value` (LISP-machine style).
- Parameter syntax is provisional. The SimpleEQ project already has a working
  parameter structure (typed name, range, default per parameter; exposed via
  RTT on STM32 and pybind on host) that any new block should align with;
  we'll settle the description-language form against that reference.

A parser for this dialect is roughly 30 lines of Python. JSON is a fallback
if broader tooling becomes important.

## Code generation

Python reads the graph description and emits a plain `.cpp` file:

- Static buffer allocations for every signal in the graph (generated from the
  connection structure; the user does not declare them).
- Block instances as static members.
- A `process_chunk(const float* in_buf, float* out_buf)` function that calls
  each block's `process()` in topological order, passing the appropriate
  named intermediate buffers. Each call processes one chunk; the chunk size
  is a build-time constant.

The generated `.cpp` is what compiles. No graph object at runtime, no node
iteration, no virtual dispatch — just a fixed sequence of chunk-processing
function calls.

The description is the source of truth; the `.cpp` is a build artifact.

The same description generates wiring for both targets. The only difference
between target builds is at the boundary: where audio enters (codec ISR vs
pybind input array) and where it leaves. The interior is byte-identical.

Inside `process_chunk`, each block's `process()` is called in topological
order on the named intermediate buffers. The buffers are real memory — the
default no-reuse policy means every buffer is inspectable by name from
Python (host) or RTT (target). The compiler may inline block bodies where
that pays off, but the architectural commitment is to the chunk-by-chunk
call sequence, not to fusing the whole graph into a single sample loop.

## Faust's role

Faust is a permanent implementation language for blocks where its declarative
feedback semantics earn their keep, not just a drafting step.

Reach for Faust when:

- A block has a multi-channel state machine with several feedback signals
  (e.g. `crossfade_control.dsp`'s 6-channel feedback).
- A block has multiple coupled envelope followers or complex IIR structures.
- A block has delay-modulation logic (chorus, flanger) with delay-line
  primitives and LFOs that Faust expresses concisely.

Stick with plain C++ when:

- The block is a fixed-coefficient filter (biquad, one-pole) where the C++ is
  shorter than the Faust would be.
- The block is straightforward chunk-wise math (gain, mixer, sum) where the
  C++ is a tight loop over the chunk.
- The block is delay-line storage with no feedback path.

Rule of thumb: if you find yourself writing many `prev_*` member variables to
express the algorithm, Faust is probably the right tool.

In either case, Faust's runtime never ships to the STM32. Faust compiles to
plain `.cpp` files that are embedded as first-class firmware code and called
in the chunk-by-chunk processing sequence.

Faust blocks live in paired `.dsp` + `.cpp` files — the `.cpp` carries the
`@block` definition and a minimal adapter around the Faust-generated class.
The chunk-based block API matches Faust's natural `compute()` shape, so the
adapter is just argument adaptation rather than a per-sample wrapper. See
Block source files for the file convention.

## Control

Parameters are setters on blocks. Each block declares its control surface in
one place: name, type, range, default. SimpleEQ already has a working
parameter structure — typed declarations exposed via the RTT control
transport on STM32 and via pybind on host — that any new block should align
with.

- **Design-time** parameters (sample rate, buffer sizes, fixed filter orders)
  are baked into the generated code at compile time.
- **Runtime** parameters (cutoffs, gains, pitch ratios) are settable via
  control after the graph is running. On host, pybind exposes setters
  directly. On STM32, RTT message handlers map incoming updates to the same
  setters. Updates happen foreground; the audio ISR never branches on "are
  parameters ready."

The control transport differs between targets, but the control surface — the
list of typed parameters per block — is declared once and shared.

## What we explicitly avoid

- Runtime graph framework with virtual dispatch (the
  `audio-graph-python/python/graph.py` `AudioGraph`/`AudioProcessor` model).
- Native realtime hosts (Max/MSP, JUCE, AU/VST). Embedded is the only target.
- Cross-block feedback edges with explicit `unit_delay` nodes. Feedback lives
  inside blocks.
- `#ifdef DEBUG` probe channels. Buffers are first-class and inspectable by
  default.
- Hand-coded call order in graph descriptions. Connections in, topological
  sort out.
- Buffer copies for port-to-block routing or fan-out. Consumers read from the
  producer's buffer.
- Dynamic memory allocation in the audio path. Allocation happens in
  constructors only.
- Reaching into a subgraph's internals from the enclosing graph.
  Encapsulation is preserved.

## What is still TBD

- Exact S-expression syntax inside the `@block` marker — the form shown in
  Block source files is provisional. The final form will solidify when we
  apply this convention to the pitch shifter blocks.
- `@block` marker extractor implementation — regex sweep vs. a real parser;
  deferred until the first non-trivial set of block files forces the choice.
- Exact form of the `(import ...)` keyword — provisional pending pitch
  shifter migration.
- Concrete parameter syntax in the description language — `:key value` is
  provisional. The SimpleEQ project's parameter structure is the reference;
  we should align when we settle this.
- Concrete C++ ABI for multi-port blocks — how to pass chunk-based inputs
  and produce chunk-based outputs without verbose call sites.
- How the buffer directory is exposed on STM32 — a single linker section the
  RTT bridge can iterate, or per-buffer named exports.
- The `probe` form: needed only when buffer reuse is implemented; deferred
  until then.
- Whether the s-expr parser is hand-written or built on an existing tiny
  library.
- Migration order for the pitch-shifter pipeline (first concrete test of this
  architecture, planned next).
