# Design Decisions - Audio Graph Python

This document captures the key design decisions and discussions that shaped the audio-graph-python project.

## Overview

A hybrid audio processing system that combines:
- **Faust DSP modules** - On-the-fly compilation via DawDreamer
- **C++ DSP modules** - Compiled with pybind11
- **Python graph system** - Custom, lightweight routing and testing
- **Future Max/MSP export** - Same DSP code, different host

## Core Design Principles

### 1. Incrementalism Over Flexibility

**Decision:** Start simple, add complexity only when needed.

**Rationale:** With code generation tools, refactoring is much cheaper than it used to be. Better to start with a minimal working system and extend it based on actual needs rather than over-engineer for hypothetical requirements.

**Examples:**
- Single sample rate (no multi-rate support initially)
- Flat channel model (no multichannel signal objects)
- Serial graph topology first (parallel routing later)

### 2. Flat Channel Model

**Decision:** All signals are mono buffers. Multichannel = N parallel mono signals.

**Rationale:**
- Matches Faust's internal model exactly
- Matches Max's traditional approach (separate inlets/outlets)
- Simple to reason about
- Easy to implement
- Can add channel grouping metadata later if needed

**Interface:**
```python
class AudioProcessor:
    def get_num_inputs(self) -> int   # Just a count
    def get_num_outputs(self) -> int  # Just a count
    def process(self, inputs: List[np.ndarray]) -> List[np.ndarray]
```

**Trade-off:** No semantic grouping of channels (e.g., "stereo pair"). Must track manually or add metadata later.

### 3. Single Sample Rate

**Decision:** All processors in a graph run at the same sample rate.

**Rationale:**
- Neither Faust nor Max support multiple sample rates in a graph
- Simpler graph logic (no resampling nodes)
- Can add later if truly needed

### 4. Uniform Processor Interface

**Decision:** All processors (Faust, C++, future others) expose identical Python interface.

**Rationale:**
- Graph doesn't care about implementation
- Easy to test modules in isolation
- Easy to swap implementations
- Clear contract for new module types

**Standard Interface:**
```python
class AudioProcessor:
    def init(self, sample_rate: int) -> None
    def process(self, inputs: List[np.ndarray]) -> List[np.ndarray]
    def set_param(self, name: str, value: float) -> None
    def get_param(self, name: str) -> float
    def get_num_inputs(self) -> int
    def get_num_outputs(self) -> int
```

## Development Workflow Strategy

### Python First, Max Later

**Decision:** Develop and test in Python using soundfiles, export to Max when ready for real-time.

**Rationale:**
1. **Iteration speed** - Offline processing is much faster to iterate
2. **Testing rigor** - Full Python ecosystem (pytest, numpy, matplotlib)
3. **Debugging** - Can inspect all intermediate signals
4. **Validation** - Compare outputs, generate plots, catch bugs early
5. **Direct transfer** - Same Faust .dsp files compile to Max externals

**Workflow:**
```
Write Faust/C++ → Test in Python → Validate → Export to Max
     ↓                  ↓              ↓           ↓
  .dsp file      DawDreamer/     pytest/plots   Max external
  .cpp file      pybind11                        .mxo
```

### Why Not DawDreamer's Graph?

**Decision:** Use DawDreamer for Faust compilation only, build our own graph system.

**Rationale:**
- DawDreamer's graph is designed for DAW-style audio production
- We need custom features: capture mode, chunked processing, Max export
- Simpler to extend our own lightweight system
- Still leverage DawDreamer for what it's good at: Faust compilation

**Architecture:**
```python
class FaustProcessor(AudioProcessor):
    def __init__(self, dsp_file_path):
        self.engine = daw.RenderEngine(44100, 512)  # Use DawDreamer
        self.proc = self.engine.make_faust_processor("proc")
        # ... wrap in our interface
```

## C++ Integration Strategy

### pybind11 with Code Generation

**Decision:** C++ is source of truth, use comment hints to generate pybind11 wrappers.

**Alternative Considered:** Python classes as spec (like previous SciPy/Streaming approach).

**Rationale:**
1. **No duplication** - C++ header is single source of truth
2. **DSP-focused** - Audio engineers often prefer writing C++ directly
3. **Faust does heavy lifting** - Less C++ overall since Faust handles many modules
4. **Simpler generator** - Parse C++, not introspect Python
5. **Incremental adoption** - Add hints only where needed

**Proposed Hint System:**
```cpp
// @pybind: struct
// @expose: all_fields
struct ProcessorState {
  float lastout;
};

// @pybind: processor
struct MyProcessor {
  ProcessorState state;

  // @pybind: method
  void init(int sample_rate);

  // @pybind: method
  // @numpy: buffers=[in/out, in/out]
  void process(vector<vector<float>>& buffers);
};
```

**Tool:** Python script (`gen_pybind.py`) parses hints and generates `pybind_*.cpp` files.

### Build System: Simple Makefiles

**Decision:** Single makefile with minimal file noise (like SciPy/Streaming approach).

**Rationale:**
- Fast builds
- No CMake complexity for simple modules
- Only final `.so` files, no intermediate clutter
- Familiar pattern (already validated)

**Usage:**
```bash
make -f build/audio.make TARGET=my_processor
# Generates: build/pybind_my_processor.cpython-312-darwin.so
```

## Graph System Features

### Named Processors

**Decision:** All processors accessed by name in a graph.

**Rationale:**
- Easy to find signals when debugging
- Maps naturally to graph description language
- Clear when reading code: `graph.processors["compressor"]`
- Matches Max object naming

### Capture Mode

**Decision:** Optional mode to record all intermediate signals.

**Rationale:**
- Essential for debugging complex chains
- Visualize signal flow
- Compare against reference implementations
- Minimal overhead when disabled

**Usage:**
```python
graph = AudioGraph(44100, capture_intermediates=True)
graph.add_processor("gain", gain_proc)
graph.add_processor("filter", filter_proc)
output = graph.process_serial(input_signal)

# Access any intermediate
filter_out = graph.get_captured_signal("filter", channel=0)
```

### Chunked Processing

**Decision:** Support processing in small chunks to test state management.

**Rationale:**
- Real-time audio processes in small buffers (64-512 samples)
- Stateful processors (delays, filters) can have chunk-boundary bugs
- Need to validate: `chunked_output == full_buffer_output`

**Usage:**
```python
# Process in 512-sample chunks
output = graph.process_serial(input_signal, chunk_size=512)

# Verify state management works
output_full = graph.process_serial(input_signal)
np.testing.assert_allclose(output, output_full, rtol=1e-6)
```

**Implementation:** Automatically accumulates results and captured signals across chunks.

## Graph Description Language

### Proposed Syntax

**Decision:** Simple text format with explicit pin indexing.

**Key Features:**
1. Clear sections: Processors, Parameters, Connections
2. Explicit indexing: `processor[pin_index]`
3. Visual arrows: `source[0] -> dest[1]`
4. Shorthand for matching counts: `blka -> blkb` (all-to-all)
5. Comments: `#` for documentation

**Example:**
```
## Processors
input: Input(channels=2)
gain: FaustGain("gain.dsp")
filter: FaustFilter("filter.dsp")
output: Output(channels=2)

## Parameters
gain.gain = 0.75
filter.freq = 1000

## Connections
input[0] -> gain[0]           # Left channel
input[1] -> gain[1]           # Right channel
gain -> filter                # Implicit: all outputs to all inputs
filter -> output              # Stereo pair
```

**Connection Rules:**
- `blka -> blkb` - Connect all outputs to all inputs (must match count)
- `blka[i] -> blkb[j]` - Single pin connection
- `blka[i:j] -> blkb[i:j]` - Range notation

**Future:** Parser to load `.graph` files and build Python AudioGraph.

## Faust Integration Insights

### Callback Mechanism

Understanding gained: Faust uses visitor pattern for UI registration.

**How it works:**
1. Faust generates `buildUserInterface(UI* ui_interface)` method
2. Max/Python creates a `MapUI` object implementing the `UI` interface
3. Call `dsp->buildUserInterface(map_ui)` to register parameters
4. Faust calls back with parameter name and pointer to internal storage
5. MapUI stores `name -> pointer` mapping
6. Set parameters: `map_ui->setParamValue("gain", 0.5)` updates internal pointer

**Key insight:** Parameters are registered via callbacks, not declared in advance. The UI object is passed TO the Faust code, not vice versa.

**This explains:**
- Why DawDreamer can compile `.dsp` strings on-the-fly
- How the same Faust code works with different UIs (Max, Web, Python)
- Why we can use string-based parameter setting

## Future Work

### Metadata System (When Needed)

If flat model becomes limiting, add channel grouping:

```python
class AudioProcessor:
    def __init__(self):
        self.output_groups = [
            {"name": "audio", "channels": 2, "start_idx": 0},
            {"name": "envelope", "channels": 1, "start_idx": 2}
        ]
```

### Parallel Routing (When Needed)

Extend graph to support:
- Splits (duplicate signal to multiple destinations)
- Mixers (combine multiple signals)
- Arbitrary routing (not just series chains)

### Max Export Tool (When Ready)

Generate Max patchers from graph descriptions:
- `.graph` file → Max patcher
- Python graph → Max patcher
- Same processors (Faust/C++ compiled for Max)

### pybind11 Generator (Soon)

Implement `gen_pybind.py` to parse C++ hints and generate wrappers.

## References

- **SciPy/Streaming** - Previous metaprogramming approach with Python specs
- **Max SDK** - Audio external development patterns
- **DawDreamer** - Faust integration and on-the-fly compilation
- **faust-python-interop** - Existing test project with DawDreamer

## Key Takeaway

**Start simple, iterate fast, extend when needed.** The combination of code generation (for boilerplate), incremental development (test each piece), and clear interfaces (uniform processor API) gives us confidence to start minimal and evolve the system organically.
