# DSP Library

Framework-agnostic audio DSP implementations for use across multiple platforms.

## Purpose

This library contains pure C++ and Faust DSP implementations that are shared between:
- **Python graph system** (audio-graph-python): For algorithm development and testing
- **Max externals** (max_externals): For deployment in Max/MSP patches

## Structure

```
dsp_library/
├── cpp/
│   ├── include/          # C++ DSP headers (framework-agnostic)
│   └── src/              # C++ DSP implementations
└── faust/                # Faust DSP files
```

## Design Principles

1. **Framework-agnostic**: Core DSP logic has no dependencies on Max, Python, or any specific framework
2. **Single source of truth**: Write DSP once, wrap for different platforms
3. **Standard C++**: Uses only standard library types (vector, string, etc.)
4. **Clean interfaces**: Simple init/process/parameter pattern

## Usage

### In Python (audio-graph-python)
```python
# Bindings wrap DSP classes with pybind11
from build.pybind_example_processor import ExampleProcessor
processor = ExampleProcessor()
processor.init(44100)
```

### In Max (max_externals)
```cpp
// Max wrapper includes DSP headers
#include "../../dsp_library/cpp/include/example_processor.h"
// ... Max-specific wrapper code
```

### Faust Modules
Faust `.dsp` files are compiled dynamically by DawDreamer in Python or can be compiled to C++ for Max externals.

## Current Modules

### C++ Processors
- **example_processor**: Simple gain (template/example)
- **split_chorus**: Split chorus effect - mono input, stereo output with independent delay/modulation per channel

### Faust Modules
- **gain.dsp**: Simple gain processor
- **split_gain.dsp**: Split signal with gain on one output
- **dual_tap_delay.dsp**: Shared delay buffer with two independent read taps, 9th order Lagrange interpolation (for chorus/pitch shift)

## Adding New Processors

1. Create framework-agnostic C++ class in `cpp/include/` and `cpp/src/`
2. Create pybind11 bindings in `audio-graph-python/bindings/`
3. Create Max external wrapper in `max_externals/`
4. Update build systems accordingly

## License

(Add your license information here)
