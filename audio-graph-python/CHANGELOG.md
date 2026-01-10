# Changelog

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
