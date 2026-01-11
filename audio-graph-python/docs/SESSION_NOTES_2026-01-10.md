# Session Notes - 2026-01-10

## Session Overview

Discussion focused on architecture and design of the audio-graph-python system, with emphasis on understanding existing patterns (Faust, Max) and designing a clean incremental workflow.

## Key Topics Covered

### 1. Understanding Existing Systems

**Faust Callback Mechanism**
- Investigated how Faust Max gain object works
- Discovered visitor pattern: `buildUserInterface(UI* ui)`
- Faust code calls back to register parameters with UI object
- MapUI stores name->pointer mappings for parameter access
- Location: `Max Experiments/andy.gain_project/external/andy.faust_gain_tilde/`

**Key Files:**
- `faust_gain.cpp:97-100` - `buildUserInterface()` method
- `faust_minimal.h:65-130` - MapUI implementation
- `faust_gain_tilde.cpp:89-90` - Where UI object is passed to Faust

**Insight:** Parameters registered dynamically via callbacks, not declared statically.

### 2. Development Workflow Discussion

**Decision: Python-First with Max Export Later**

Rationale:
- Faster iteration with offline processing
- Full testing infrastructure (pytest, numpy, matplotlib)
- Incremental algorithm development
- Direct path to Max (same Faust files compile to Max externals)

**Workflow:**
```
Develop → Test → Validate → Export
Python    Python  Python     Max
```

### 3. Interface Design

**Three Systems to Align:**
1. Faust - Generated C++ with `compute(int count, FAUSTFLOAT** inputs, FAUSTFLOAT** outputs)`
2. Max - DSP64 perform routines with double** pointers
3. Python - Our custom graph system

**Unified Interface:**
```python
class AudioProcessor:
    def init(sample_rate: int)
    def process(inputs: List[np.ndarray]) -> List[np.ndarray]
    def set_param(name: str, value: float)
    def get_num_inputs() -> int
    def get_num_outputs() -> int
```

**Key Decisions:**
- Flat channel model (N mono signals, not multichannel objects)
- Single sample rate (no multi-rate support initially)
- String-based parameters (matches Faust MapUI pattern)

### 4. C++ Integration Strategy

**Question:** How to generate pybind11 bindings?

**Previous Approach (SciPy/Streaming):**
- Python classes with dataclasses as spec
- `code_gen.py` introspects Python and generates C++ + pybind11
- Single source of truth: Python

**New Approach (Audio Graph):**
- C++ headers as source of truth
- Comment hints guide code generation
- Parser extracts structure and generates pybind11
- Less duplication, more DSP-focused

**Proposed Hints:**
```cpp
// @pybind: struct
// @expose: all_fields
struct State { ... };

// @pybind: processor
struct MyProcessor {
  // @pybind: method
  void init(int sample_rate);

  // @pybind: method
  // @numpy: buffers=[in/out, in/out]
  void process(vector<vector<float>>& buffers);
};
```

**Tool:** `gen_pybind.py` (to be implemented)

### 5. Graph Description Language

**Design Goals:**
- Simple to write and read
- Handle splits and arbitrary routing
- Explicit pin indexing (flat model)
- Visual clarity

**Proposed Syntax:**
```
## Processors
gain: FaustGain("gain.dsp")
filter: MyFilter()

## Parameters
gain.gain = 0.75

## Connections
input[0] -> gain[0]
gain[0] -> filter[0]
filter -> output        # Implicit all-to-all (if counts match)
```

**Features:**
- Explicit indices: `processor[pin]`
- Shorthand: `a -> b` connects all outputs to all inputs
- Range notation: `a[0:2] -> b[0:2]`
- Comments: `#`

**Hierarchy Support (Future):**

Post-session discussion on walk: Hierarchy can be cleanly added using port statements in subgraphs.

**Design:**
```
# reverb_chain.graph (subgraph)
## Ports
input: 2
output: 2

## Processors
pre: FaustGain("gain.dsp")
reverb: FaustReverb("reverb.dsp")
post: FaustGain("gain.dsp")

## Connections
input[0:2] -> pre[0:2]
pre -> reverb
reverb -> post
post -> output

# main.graph (top-level)
## Processors
chain1: reverb_chain.graph   # Subgraph as processor
chain2: reverb_chain.graph   # Separate instance

## Parameters
chain1.pre.gain = 0.8         # Dot notation for nested params
chain1.reverb.decay = 2.0
chain2.pre.gain = 0.6         # Independent instance
```

**Implementation Rules:**
1. **Port Declarations** - Non-top-level graphs declare input/output counts
2. **Uniform Interface** - Subgraphs look exactly like processors
3. **Dot Notation** - Parameters accessed via `subgraph.processor.param`
4. **Tree Structure Only** - No circular dependencies allowed
5. **Unique Names Per Scope** - Names must be unique at each hierarchy level
6. **Multiple Instances** - Each named instance is independent with its own state

**Resolution Logic:**
- `.graph` extension → Load subgraph recursively
- `.dsp` extension → Load Faust module
- No extension with `()` → Load C++ class

**Benefits:**
- ✅ Clean encapsulation
- ✅ Testable subgraphs in isolation
- ✅ Composable (build complex from simple)
- ✅ Matches Max subpatcher model
- ✅ No fundamental blockers to future implementation

**Considerations:**
- Circular dependency detection during graph loading
- Capture mode depth configuration (capture inside subgraphs or just boundaries)
- Parameter namespace flattening vs hierarchical

### 6. Graph System Enhancements

**Implemented Features:**

**Named Processors:**
- `graph.add_processor("gain", proc)`
- Access: `graph.processors["gain"]`
- Essential for graph description language mapping

**Capture Mode:**
- `AudioGraph(sample_rate, capture_intermediates=True)`
- Records all intermediate signals
- Access: `graph.get_captured_signal("processor_name", channel)`
- Perfect for debugging and visualization

**Chunked Processing:**
- `graph.process_serial(signal, chunk_size=512)`
- Tests state management across chunk boundaries
- Accumulates results automatically
- Validates: `chunked == full_buffer` (within tolerance)

**Combined:**
- Capture + chunked = inspect intermediates across chunks
- Named access = easy to find specific signals
- Visual debugging = plot entire signal flow

### 7. Why Not Use DawDreamer's Graph?

**Decision:** Use DawDreamer for Faust only, build custom graph.

**Reasons:**
1. Need custom features (capture, chunking, Max export)
2. DawDreamer graph designed for DAW-style audio production
3. Simpler to extend our lightweight system
4. Still leverage DawDreamer's Faust compilation strength

**Architecture:**
```python
class FaustProcessor:
    def __init__(self, dsp_file):
        self.engine = daw.RenderEngine(44100, 512)  # Use DawDreamer
        # Wrap in our AudioProcessor interface
```

## Important Insights

### Faust's Flat Model

**Discovery:** Faust doesn't have multichannel signals as first-class objects.

Everything is mono signals composed in parallel:
```faust
process = _,_ : some_reverb;  // Not "one stereo input", but "two mono inputs"
```

**Implication:** No semantic grouping (e.g., "stereo pair" vs "two mono"). Our flat model matches this naturally.

### Hierarchy in Faust

**Question:** How does Faust support hierarchy?

**Answer:** It doesn't really. Just composition of flat signal counts.

**Example:** Compressor with stereo audio + mono sidechain
```faust
compressor = _,_,_ : ... : _,_;  // 3 in, 2 out (no grouping metadata)
```

You mentally track "first 2 are stereo, 3rd is sidechain" but it's not in the type system.

**Our approach:** Start flat, add metadata later if needed.

### On-the-Fly Compilation

**DawDreamer Trick:** Embeds libfaust compiler

```python
with open("gain.dsp") as f:
    dsp_code = f.read()

proc.set_dsp_string(dsp_code)  # Compiles on-the-fly, no build step!
```

**How:**
- DawDreamer links against libfaust
- Compiles DSP → LLVM IR → machine code at runtime
- No intermediate C++ files, no build system

**Why this matters:** Ultra-fast iteration for Faust modules.

## Design Philosophy

**Incrementalism with Code Generation Safety Net**

Core principle: "Don't over-engineer for hypothetical needs when refactoring is cheap."

**Why this works:**
1. Claude can generate boilerplate (pybind11, wrappers, tests)
2. Clear interfaces make refactoring straightforward
3. Start minimal, extend based on real needs
4. Validate each piece before moving forward

**Examples:**
- Start: Single sample rate → Add: Multi-rate (if ever needed)
- Start: Flat channels → Add: Channel grouping metadata (if needed)
- Start: Serial chains → Add: Parallel routing (when needed)

## Action Items Completed

1. ✅ Created `audio-graph-python` project structure
2. ✅ Implemented AudioGraph with capture mode
3. ✅ Implemented chunked processing
4. ✅ Created comprehensive test suite
5. ✅ Documented design decisions
6. ✅ Updated README with new features

## Next Steps (Future Work)

1. **pybind11 Generator** - Implement `gen_pybind.py` to parse C++ hints
2. **Graph Description Parser** - Load `.graph` files into AudioGraph
3. **First Real Algorithm** - Start building the actual DSP chain
4. **Faust Testing** - Validate FaustProcessor wrapper works
5. **Max Export** - Tools to generate Max patchers from graphs

## Files Created/Modified This Session

**New Project Structure:**
```
audio-graph-python/
├── README.md (updated)
├── QUICKSTART.md
├── CHANGELOG.md
├── requirements.txt
├── setup.sh
├── cpp_modules/
│   ├── audio_support.h
│   ├── example_processor.{h,cpp}
│   └── pybind_example_processor.cpp
├── faust_modules/
│   └── gain.dsp
├── python/
│   ├── __init__.py
│   ├── graph.py (enhanced)
│   └── processors.py
├── build/
│   └── audio.make
├── tests/
│   ├── test_example.py (updated)
│   └── test_capture.py (new)
└── docs/
    ├── DESIGN_DECISIONS.md (new)
    └── SESSION_NOTES_2026-01-10.md (this file)
```

## Key Code Patterns

**Processor Interface:**
```python
class AudioProcessor(ABC):
    @abstractmethod
    def init(self, sample_rate: int) -> None: pass

    @abstractmethod
    def process(self, inputs: List[np.ndarray]) -> List[np.ndarray]: pass

    @abstractmethod
    def set_param(self, name: str, value: float) -> None: pass
```

**Graph Usage:**
```python
# Create with capture
graph = AudioGraph(44100, capture_intermediates=True)

# Add named processors
graph.add_processor("gain", FaustProcessor("gain.dsp"))
graph.add_processor("filter", CppProcessor(MyFilter()))

# Process in chunks
output = graph.process_serial(input_signal, chunk_size=512)

# Inspect intermediates
gain_out = graph.get_captured_signal("gain", 0)
all_signals = graph.get_all_captured_signals()
```

## References to Existing Code

**Max Experiments:**
- `andy.gain_project/` - Working Max external with remote control
- Shows Faust → Max compilation and integration

**SciPy/Streaming:**
- `pybind/pybind.make` - Makefile pattern we're replicating
- `code_gen.py` - Previous metaprogramming approach
- `env.py` / `env.h` / `pybind_env.cpp` - Example of generated code

**faust-python-interop:**
- Existing DawDreamer + Faust test project
- Shows on-the-fly `.dsp` compilation

## Session Outcome

Successfully designed and implemented foundation for audio-graph-python:
- Clean architecture with clear separation of concerns
- Validated approach aligns with Faust, Max, and Python patterns
- Implemented key features (capture, chunking, named processors)
- Documented design decisions and rationale
- Ready to start building actual DSP algorithms

**Status:** Foundation complete, ready for incremental algorithm development.
