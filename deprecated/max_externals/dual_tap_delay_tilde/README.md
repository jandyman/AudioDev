# dual_tap_delay~ Max External

High-quality dual tap delay for Max/MSP using Faust-generated DSP.

## Description

Single delay buffer with two independent read taps, featuring 9th-order Lagrange interpolation for smooth, artifact-free modulation. Much better than Max's default linear interpolation (tapin~/tapout~).

Uses Faust DSP code from `dsp_library/faust/dual_tap_delay.dsp`.

## Inputs (3 signal inlets)

1. **Audio Input** - Signal to be delayed
2. **Delay Time 1 (ms)** - Delay time for first tap (0-1000 ms)
3. **Delay Time 2 (ms)** - Delay time for second tap (0-1000 ms)

## Outputs (2 signal outlets)

1. **Tap 1** - First delayed output
2. **Tap 2** - Second delayed output

## Building

### Requirements

1. **Max SDK**: Already installed at `/Users/andy/max-sdk`
2. **CMake**: For building
3. **Xcode**: For compiling
4. **Faust**: For compiling DSP (must be in PATH)

### Build Steps

```bash
cd max_externals/dual_tap_delay_tilde
rm -rf build && mkdir build && cd build
cmake -G Xcode ..
xcodebuild -configuration Release
```

The external will be built to `Max Experiments/objects/dual_tap_delay~.mxo` (alongside your other Max externals).

### Verify Universal Binary

```bash
lipo -info "../../Max Experiments/objects/dual_tap_delay~.mxo/Contents/MacOS/dual_tap_delay~"
# Should show: x86_64 arm64
```

## Usage in Max

### Basic Usage

```
[sig~ 1000]        [sig~ 1500]
    |                  |
    |                  |
[phasor~ 440]      |  |
    |              |  |
    |              |  |
[dual_tap_delay~]--|  |
    |                 |
    |                 |
[dac~]            [dac~]
```

### For Chorus Effect

Replace tapin~/tapout~ in Max's Chorus~.maxpat:

```
[audio_in]  [lfo_1_ms]  [lfo_2_ms]
    |           |           |
[dual_tap_delay~]
    |           |
  [tap1]     [tap2]
```

## Technical Details

- **Interpolation**: 9th-order Lagrange (512 points)
- **Buffer size**: 1000ms (1 second)
- **Architecture**: Universal binary (x86_64 + arm64)
- **DSP**: Vectorized, double precision

## Advantages over tapin~/tapout~

1. **Better interpolation**: 9th-order Lagrange vs linear
2. **Smoother modulation**: No zipper noise or artifacts
3. **Dual taps in one object**: More efficient than separate tapin~/tapout~
4. **Shared buffer**: Both taps read from same delay line

## Architecture

This external demonstrates the **Faust DSP** workflow:

```
dsp_library/faust/
└── dual_tap_delay.dsp       ← Core DSP (Faust code)

max_externals/dual_tap_delay_tilde/
├── dual_tap_delay_tilde.cpp ← Max wrapper
└── CMakeLists.txt           ← Faust compilation + Max build

build/
└── faust_dual_tap_delay.cpp ← Generated C++ (CMake creates this)

Max Experiments/objects/
└── dual_tap_delay~.mxo      ← Final external
```

## Verified

- ✅ DSP implementation complete and tested in Faust
- ✅ Max external built successfully (universal binary: x86_64 + arm64)
- ✅ Output to centralized objects folder
- ✅ Ready to use in Max/MSP

## Related Files

- Faust DSP: `dsp_library/faust/dual_tap_delay.dsp`
- Built external: `Max Experiments/objects/dual_tap_delay~.mxo`
- Template: Based on `andy.faust_gain_tilde/`

## Next Steps

Use this external in Max's Chorus~ patcher by replacing tapin~/tapout~ with dual_tap_delay~. This will provide better sound quality with smoother modulation.
