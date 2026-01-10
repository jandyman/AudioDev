# Audio Graph Python

Hybrid audio processing graph system combining Faust and C++ processors with Python control.

## Project Structure

```
audio-graph-python/
├── cpp_modules/          # C++ DSP modules with pybind11 wrappers
├── faust_modules/        # Faust .dsp source files
├── python/               # Python graph system and processor wrappers
├── build/                # Build outputs (.so files)
└── tests/                # Test files
```

## Quick Start

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Build C++ Modules

```bash
cd build
make -f audio.make TARGET=example_processor
```

### Run Example

```bash
python tests/test_example.py
```

## Design Philosophy

- **Flat channel model**: All signals are mono, multichannel is N parallel mono signals
- **Single sample rate**: All processors run at the same sample rate
- **Uniform interface**: Faust and C++ modules expose identical Python API
- **Minimal file noise**: Only final .so files, no intermediate build products

## Creating New Modules

### C++ Module

1. Create `cpp_modules/mymodule.h` and `cpp_modules/mymodule.cpp`
2. Create `cpp_modules/pybind_mymodule.cpp` with pybind11 wrapper
3. Build: `make -f build/audio.make TARGET=mymodule`
4. Import: `from build.pybind_mymodule import MyModule`

### Faust Module

1. Create `faust_modules/mymodule.dsp`
2. Use FaustProcessor wrapper (no build step needed)
3. Load at runtime via DawDreamer

## Processor Interface

All processors (C++ and Faust) implement:

```python
class AudioProcessor:
    def init(self, sample_rate: int) -> None
    def process(self, inputs: List[np.ndarray]) -> List[np.ndarray]
    def set_param(self, name: str, value: float) -> None
    def get_param(self, name: str) -> float
    def get_num_inputs(self) -> int
    def get_num_outputs(self) -> int
```

## Graph Features

### Named Processors

All processors in a graph are accessed by name:

```python
graph = AudioGraph(sample_rate=44100)
graph.add_processor("gain", gain_proc)
graph.add_processor("filter", filter_proc)

# Access by name
graph.processors["gain"].set_param("gain", 0.5)
graph.processors["filter"].set_param("frequency", 1000)
```

### Capture Mode

Enable `capture_intermediates` to record all intermediate signals:

```python
# Create graph with capture enabled
graph = AudioGraph(sample_rate=44100, capture_intermediates=True)
graph.add_processor("gain", gain_proc)
graph.add_processor("filter", filter_proc)

# Process signal
output = graph.process_serial(input_signal)

# Access any intermediate signal
gain_output = graph.get_captured_signal("gain", channel=0)
filter_output = graph.get_captured_signal("filter", channel=0)

# Or get all at once
all_signals = graph.get_all_captured_signals()
for name, channels in all_signals.items():
    print(f"{name}: {len(channels)} channels")
    plt.plot(channels[0], label=name)
```

### Chunked Processing

Test state management by processing in small chunks:

```python
# Process entire file at once
output_full = graph.process_serial(input_signal)

# Process in 512-sample chunks (tests state management)
output_chunked = graph.process_serial(input_signal, chunk_size=512)

# Verify they match (state management working correctly)
np.testing.assert_allclose(output_chunked, output_full, rtol=1e-6)
```

Chunked processing automatically accumulates results across all chunks, so you get the full output signal. When combined with capture mode, you can inspect intermediate signals across chunk boundaries.

## Development Workflow

1. Write/edit DSP code (C++ or Faust)
2. Build C++ modules if needed (Faust compiles on-the-fly)
3. Test individual processors in Python
4. Compose into graph
5. Iterate quickly

## Future Extensions

- Parameter metadata system
- Named channel groups (stereo pairs, etc.)
- Multiple sample rate support
- Max/MSP export tooling
