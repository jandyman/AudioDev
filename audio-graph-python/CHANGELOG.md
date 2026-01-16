# Changelog

## 2026-01-15 - Split Chorus and File Reorganization

### Added

**Split Chorus C++ Module**
- New `split_chorus` processor in `dsp_library/cpp/`
- Takes mono input, outputs two channels with independent delay/modulation
- Python bindings: `pybind_split_chorus.cpp`
- Example: `examples/test_split_chorus.py`

**Graph Specification Language**
- DSL for defining cascade graphs: `examples/cascade_spec.txt`
- Parser in `python/graph_spec.py`
- Supports comments, parameters inline
- Tests: `tests/test_graph_spec.py`

### Changed

**File Reorganization**
- DSP library now central source for both Python and Max
- Max externals reference `dsp_library/` headers
- Clear separation: dsp_library → bindings → python wrappers

### Files Added
- `dsp_library/cpp/include/split_chorus.h`
- `dsp_library/cpp/src/split_chorus.cpp`
- `audio-graph-python/bindings/pybind_split_chorus.cpp`
- `audio-graph-python/examples/test_split_chorus.py`
- `audio-graph-python/examples/cascade_spec.txt`
- `audio-graph-python/python/graph_spec.py`

---

## 2026-01-10 - Enhanced Graph System

### Added

**Named Processors**
- Processors now accessed by name instead of index
- `graph.add_processor(name, processor)`
- Access via `graph.processors[name]`

**Capture Mode**
- Optional intermediate signal capture for debugging
- `AudioGraph(sample_rate, capture_intermediates=True)`
- `graph.get_captured_signal(processor_name, channel)`
- `graph.get_all_captured_signals()` returns all intermediate signals
- Useful for visualizing signal flow and debugging

**Chunked Processing**
- Process signals in small chunks to test state management
- `graph.process_serial(signal, chunk_size=512)`
- Automatically accumulates results across chunks
- Validates that stateful processors work correctly

**Combined Features**
- Capture mode + chunked processing: inspect intermediate signals across chunk boundaries
- Named access makes it easy to find specific signals
- Full visualization support for signal flow analysis

### Changed
- `AudioGraph.add_processor()` now requires a name parameter
- `AudioGraph.processors` is now a dict (was list)
- Added `AudioGraph.processor_order` to maintain processing sequence

### Files Modified
- `python/graph.py` - Enhanced AudioGraph class
- `tests/test_example.py` - Updated to use named processors
- `README.md` - Added documentation for new features

### Files Added
- `tests/test_capture.py` - Comprehensive tests for capture mode and chunking
- `CHANGELOG.md` - This file

## Example Usage

```python
# Create graph with capture
graph = AudioGraph(44100, capture_intermediates=True)

# Add named processors
graph.add_processor("input_gain", gain1)
graph.add_processor("compressor", comp)
graph.add_processor("output_gain", gain2)

# Set parameters by name
graph.processors["input_gain"].set_param("gain", 0.8)

# Process in chunks
output = graph.process_serial(signal, chunk_size=512)

# Inspect intermediates
comp_output = graph.get_captured_signal("compressor", 0)

# Visualize
all_signals = graph.get_all_captured_signals()
for name, channels in all_signals.items():
    plt.plot(channels[0], label=name)
plt.legend()
plt.show()
```
