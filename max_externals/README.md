# Max Externals

Max/MSP external wrappers for DSP processors defined in `dsp_library/`.

## Structure

Each external lives in its own subdirectory:

```
max_externals/
├── gain_tilde/           # gain~ external
│   ├── gain_tilde.cpp    # Max wrapper code
│   └── Makefile          # Build script
├── dual_band_chorus_tilde/
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

(None yet - to be created)

## Planned Externals

- **dual_band_chorus~**: Dual-band chorus effect
- **pitch_shifter~**: Bass guitar pitch shifter

## Resources

- [Max SDK Documentation](https://cycling74.com/sdk)
- [Writing Max Externals](https://cycling74.com/sdk/max-sdk-8.0.3/html/index.html)
