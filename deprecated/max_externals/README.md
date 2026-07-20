# Max Externals

Max/MSP external wrappers for DSP processors defined in `dsp_library/`.

## Structure

Each external lives in its own subdirectory:

```
max_externals/
├── dual_tap_delay_tilde/ # dual_tap_delay~ - Faust-based dual tap delay
│   ├── *.xcodeproj       # Xcode project (CMake-generated)
│   └── ...
├── split_chorus_tilde/   # split_chorus~ - C++ split chorus effect
│   ├── *.xcodeproj       # Xcode project
│   └── ...
└── README.md             # This file
```

## Building Externals

Each external includes a Makefile for building:

```bash
cd gain_tilde/
make
```

The build system will:
1. Include headers from `dsp_library/cpp/include/`
2. Compile source from `dsp_library/cpp/src/`
3. Link Max SDK
4. Output `.mxo` bundle for macOS

## Design Pattern

Max externals follow this pattern:

```cpp
#include "../../dsp_library/cpp/include/example_processor.h"
#include "ext.h"       // Max SDK header

// Max object struct contains DSP processor
typedef struct _example_tilde {
    t_pxobject obj;
    ExampleProcessor* processor;  // Core DSP
} t_example_tilde;

// Max methods wrap processor methods
void example_tilde_dsp64(t_example_tilde *x, t_object *dsp64, /*...*/) {
    // Call processor->process() from Max perform routine
}
```

## Shared DSP Code

All DSP logic lives in `dsp_library/`. Max externals are thin wrappers that:
- Handle Max message passing
- Convert Max audio buffers to/from vector<vector<float>>
- Expose parameters as Max messages/attributes

## Current Externals

- **dual_tap_delay~**: Dual tap delay with shared buffer and 9th order Lagrange interpolation (Faust-based)
- **split_chorus~**: Split chorus effect with independent delay/modulation per channel (C++)

## Planned Externals

- **pitch_shifter~**: Bass guitar pitch shifter

## Resources

- [Max SDK Documentation](https://cycling74.com/sdk)
- [Writing Max Externals](https://cycling74.com/sdk/max-sdk-8.0.3/html/index.html)
