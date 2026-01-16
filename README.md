# AudioDev

Audio DSP development ecosystem for algorithm development, testing, and deployment.

## Active Projects

### [audio-graph-python](./audio-graph-python/)
Hybrid Faust/C++ audio processing graph system with Python control.
- Flat channel model (all signals mono, multichannel = N parallel signals)
- Uniform interface for Faust and C++ processors
- Named processor access, capture mode for debugging, chunked processing
- Graph specification language for cascade definitions

### [dsp_library](./dsp_library/)
Framework-agnostic C++ and Faust DSP implementations shared across platforms.
- **C++ Processors**: example_processor, split_chorus
- **Faust Modules**: gain, split_gain, dual_tap_delay (9th order Lagrange interpolation)
- Single source of truth: write DSP once, wrap for Python and Max

### [max_externals](./max_externals/)
Max/MSP external wrappers for DSP processors.
- **dual_tap_delay~**: Faust-based dual tap delay
- **split_chorus~**: C++ split chorus effect
- Thin wrappers that include DSP from dsp_library

## Reference Projects

### [Embedded DSP DevSystem](./Embedded%20DSP%20DevSystem/)
Conceptual framework for DSP algorithm development lifecycle (Python prototyping to embedded C++).
Contains design documents and architectural decisions.

### [DaisyExamples](./DaisyExamples/)
Examples for Electro-Smith Daisy embedded audio platform. 80+ DSP algorithm examples.

### [SciPy](./SciPy/)
Python-based signal processing algorithm development and analysis.

### [PitchShifter](./PitchShifter/)
Early-stage bass guitar pitch shifter concept.

## Architecture

```
AudioDev/
├── dsp_library/           # Core DSP implementations (C++ and Faust)
│   ├── cpp/               # Framework-agnostic C++ DSP
│   └── faust/             # Faust DSP modules
├── audio-graph-python/    # Python graph system + pybind11 bindings
│   ├── python/            # Graph system
│   ├── bindings/          # pybind11 wrappers for dsp_library
│   └── examples/          # Working examples
├── max_externals/         # Max/MSP external wrappers
│   ├── dual_tap_delay_tilde/
│   └── split_chorus_tilde/
└── ...                    # Reference projects
```

## Design Principles

1. **Single source of truth**: DSP code lives in `dsp_library/`, wrapped for each platform
2. **Flat channel model**: All signals are mono, multichannel is N parallel mono signals
3. **Uniform interface**: All processors expose `init/process/set_param/get_param`
4. **Framework-agnostic**: Core DSP has no dependencies on Max, Python, or any framework

## Getting Started

See [audio-graph-python/QUICKSTART.md](./audio-graph-python/QUICKSTART.md) for a 5-minute introduction.

## Recent Changes

See [audio-graph-python/CHANGELOG.md](./audio-graph-python/CHANGELOG.md) for recent updates.

**Latest (2026-01-15)**:
- Split chorus C++ module with Python bindings
- Graph specification language for cascade definitions
- File reorganization with dsp_library as central DSP source
