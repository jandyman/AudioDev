# andy.faust_gain~ - Faust-Powered Gain External

Max/MSP external that demonstrates Faust DSP integration with the Max SDK.

## Overview

This external is functionally identical to `andy.gain_tilde` but uses Faust for DSP processing instead of hand-written C++. It demonstrates:
- Faust .dsp compilation integrated into CMake build
- Max SDK wrapper (shim) around Faust-generated C++ class
- Matching parameter interface (same `gain` attribute)
- Works with same OSC patcher and iOS/macOS UI apps

## Architecture

```
Max External Wrapper (faust_gain_tilde.cpp)
├── Max SDK attribute: "gain" (0.0 - 10.0)
├── perform64() callback
│   └── FaustGain::compute() ← Faust-generated DSP
└── FaustGain instance (from gain.dsp)
```

## Files

- **gain.dsp** - Faust DSP source code (simple gain processor)
- **faust_gain_tilde.cpp** - Max external wrapper/shim code
- **CMakeLists.txt** - Build configuration with Faust compilation
- **README.md** - This file

## Prerequisites

1. **Faust compiler installed:**
   ```bash
   brew install faust
   ```

2. **Max SDK** at `/Users/andy/max-sdk` (or set `MAX_SDK_PATH` environment variable)

3. **CMake and Xcode** (same as other Max externals)

## Build Instructions

```bash
cd "/Users/andy/Dropbox/Developer/AudioDev/Max Experiments/andy.gain_project/external/andy.faust_gain_tilde"

# Clean build
rm -rf build && mkdir build && cd build

# Generate Xcode project
cmake -G Xcode ..

# Build
xcodebuild -configuration Debug

# Verify universal binary
lipo -info ../../../objects/andy.faust_gain~.mxo/Contents/MacOS/andy.faust_gain~
# Should show: x86_64 arm64
```

## Build Process

The CMake build performs these steps:

1. **Faust Compilation:**
   ```bash
   faust -lang cpp -double -vec -lv 0 -cn FaustGain -o faust_gain.cpp gain.dsp
   ```
   - `-lang cpp`: Generate C++ code
   - `-double`: Use double precision (matches Max SDK)
   - `-vec`: Enable auto-vectorization
   - `-lv 0`: Vector size (0 = auto)
   - `-cn FaustGain`: Class name in generated C++

2. **C++ Compilation:**
   - Compiles `faust_gain_tilde.cpp` (Max wrapper)
   - Compiles `faust_gain.cpp` (Faust-generated)
   - Links with Max SDK

3. **Bundle Creation:**
   - Creates `.mxo` bundle for both architectures

## Usage in Max

Identical to `andy.gain_tilde`:

```
[andy.faust_gain~ @gain 1.5]
```

**Parameters:**
- `gain` - Amplitude multiplier (0.0 to 10.0, default 1.0)

**Inlets:**
- Signal inlet (audio input)

**Outlets:**
- Signal outlet (audio output)

## Integration with OSC/UI

Works with the existing OSC patcher and UI apps:
- Same attribute name: `gain`
- Same parameter range: 0.0 - 10.0
- No changes needed to `andy.gain_osc.maxpat`
- No changes needed to macOS/iOS UI apps

Just substitute `[andy.faust_gain~]` for `[andy.gain~]` in the patcher.

## Faust DSP Code

The Faust code (`gain.dsp`) is extremely simple:

```faust
import("stdfaust.lib");

gain = hslider("gain", 1.0, 0.0, 10.0, 0.01);

process = _ * gain;
```

This generates a C++ class `FaustGain` with:
- `init(int sample_rate)` - Initialize DSP
- `compute(int count, double** inputs, double** outputs)` - Process audio
- `setParamValue(const char* name, double value)` - Set parameter

The wrapper code instantiates this class and calls these methods.

## Comparison: C++ vs Faust

### andy.gain_tilde (C++)
```cpp
// In perform64:
double gain = x->gain;
for (int i = 0; i < sampleframes; i++) {
  out[i] = in[i] * gain;
}
```

### andy.faust_gain~ (Faust)
```cpp
// In perform64:
x->faust_dsp->compute(sampleframes, &in, &out);
```

Both produce identical results. Faust handles the loop internally.

## Advantages of Faust Approach

1. **Concise DSP code** - `process = _ * gain;` vs explicit loop
2. **Auto-vectorization** - Faust generates SIMD-optimized code
3. **Rapid prototyping** - Change .dsp file, rebuild, test
4. **Portable** - Same Faust code can target web, embedded, etc.

## Notes

- **First build takes longer** - Faust compilation adds ~1-2 seconds
- **Faust install required** - Build will fail if `faust` not in PATH
- **Generated C++ cached** - Only recompiles if .dsp file changes
- **Restart Max required** - After every rebuild (same as all externals)

## Troubleshooting

### "faust: command not found"
Install Faust: `brew install faust`

### Build fails with missing headers
Check Max SDK path in CMakeLists.txt line 7

### External won't load in Max
1. Verify universal binary: `lipo -info path/to/andy.faust_gain~`
2. Check Max Console for error messages
3. Ensure Max search path includes `objects/` folder

## Future Enhancements

- More complex Faust DSP algorithms (filters, effects, etc.)
- Multiple parameters
- Dynamic parameter range adaptation
- Integrate with Faust architecture files
