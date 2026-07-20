# split_chorus~ Max External

Split-band chorus effect for Max/MSP.

## Description

Splits audio into low and high frequency bands:
- **Low frequencies**: Pass through unchanged (bypass)
- **High frequencies**: Chorus effect with random LFO modulation

Uses the same DSP code as the Python version (`dsp_library/cpp/`).

## Parameters

- `crossover <float>`: Crossover frequency (20-480 Hz, default: 300 Hz)
- `delay <float>`: Center delay time (5-45 ms, default: 25 ms)
- `rate <float>`: LFO rate (0-20 Hz, default: 2 Hz)
- `depth <float>`: Modulation depth (0-1, default: 0.5)
- `wet <float>`: Dry/wet mix (0-1, default: 0.5)

## Building

### Requirements

1. **Max SDK**: Already installed at `/Users/andy/max-sdk`
2. **CMake**: For building
3. **Xcode**: For compiling
4. **DSP Library**: Core DSP code in `../../dsp_library/cpp/`

### Build Steps

```bash
cd max_externals/split_chorus_tilde
rm -rf build && mkdir build && cd build
cmake -G Xcode ..
xcodebuild -configuration Release
```

The external will be built to `Max Experiments/objects/split_chorus~.mxo` (alongside your other Max externals).

### Verify Universal Binary

```bash
lipo -info "../../Max Experiments/objects/split_chorus~.mxo/Contents/MacOS/split_chorus~"
# Should show: x86_64 arm64
```

### Installation

The external is in `Max Experiments/objects/` with your other Max externals (`andy.gain~`, `andy.faust_gain~`).
All Max externals are in one location!

## Usage in Max

```
[split_chorus~]
|
[dac~]

Messages:
- crossover 200   (set crossover to 200 Hz)
- delay 20        (set delay to 20 ms)
- rate 4          (set LFO rate to 4 Hz)
- depth 0.8       (set depth to 0.8)
- wet 0.6         (set wet mix to 0.6)
```

## Architecture

This external demonstrates the **shared DSP library** architecture:

```
dsp_library/cpp/
├── include/split_chorus.h       ← Core DSP (framework-agnostic)
└── src/split_chorus.cpp

max_externals/split_chorus_tilde/
└── split_chorus_tilde.cpp       ← Max wrapper (this file)

audio-graph-python/bindings/
└── pybind_split_chorus.cpp      ← Python wrapper (for testing)
```

The **same DSP code** works in both Max and Python!

**Output location**: All externals build to `Max Experiments/objects/` alongside your other Max externals.

## Verified

- ✅ DSP implementation complete and tested
- ✅ Works perfectly in Python (see `audio-graph-python/examples/test_split_chorus.py`)
- ✅ Max wrapper created (this external)
- ✅ **Max external built successfully** (universal binary: x86_64 + arm64)
- ✅ **Output to centralized objects folder**
- ✅ **Ready to use in Max/MSP**

## Implementation Notes

- Uses state variable filter for band splitting (simultaneous low/high outputs)
- Random LFO with smoothing to avoid zipper noise
- Linear interpolation for fractional delay
- Processes one channel (mono → mono)
- Universal binary (arm64 + x86_64)

## Related Files

- Test in Python: `audio-graph-python/examples/test_split_chorus.py`
- Core DSP: `dsp_library/cpp/src/split_chorus.cpp`
- Python bindings: `audio-graph-python/bindings/pybind_split_chorus.cpp`
- Built external: `Max Experiments/objects/split_chorus~.mxo`
