# gain~ Max/MSP External

A simple gain/volume control external for Max/MSP.

## What This Does

- Multiplies an audio signal by a gain value
- Demonstrates basic Max external structure with block-based audio processing
- Shows how to accept parameters and handle float messages
- **Demonstrates location-independent build configuration** (see BUILD_DEPENDENCIES.md)

## Project Structure

```
gain_tilde/
├── CMakeLists.txt            # Location-independent CMake configuration
├── BUILD_DEPENDENCIES.md     # Detailed explanation of build system
├── gain_tilde.cpp            # C++ source code for the external
├── setup.sh                  # Script to generate Xcode project
└── README.md                 # This file
```

## Key Feature: Location Independence

This project can be copied ANYWHERE on your system and will build correctly. The only
configuration needed is the SDK path in CMakeLists.txt line 15. All build output goes
to the shared `objects/` folder at the project root.

For details on how this works, see [BUILD_DEPENDENCIES.md](BUILD_DEPENDENCIES.md).

## Setup Instructions

### 1. Verify SDK Path

The CMakeLists.txt is already configured with your SDK path:
```
/Users/andy/Dropbox/Developer/AudioDev/max-sdk
```

If you move the SDK, edit line 7 in CMakeLists.txt.

**Note:** The build output goes to the shared `objects/` folder at the project root, where Max can find all externals and abstractions.

### 2. Generate Xcode Project

```bash
cd "/Users/andy/Dropbox/Developer/AudioDev/Max Experiments/gain_tilde"
./setup.sh
```

This creates a `build/` directory with the Xcode project.

### 3. Build in Xcode

```bash
open build/gain_tilde.xcodeproj
```

Or from command line:
```bash
cd build
xcodebuild -configuration Debug
```

Build with Cmd+B in Xcode.

### 4. Use the External

The compiled `andy.gain~.mxo` will be in the `objects/` folder at the project root.

Add the objects folder to Max's search path:
1. Max → Options → File Preferences
2. Add path: `/Users/andy/Dropbox/Developer/AudioDev/Max Experiments/objects`
3. Restart Max

### 5. Use in Max

1. Restart Max (or clear the object cache)
2. Create a new patcher
3. Create a `gain~` object
4. Connect audio input and output
5. Send it a float to change gain (e.g., number box connected to inlet)

## Usage Examples

### Basic Usage
```
[adc~]
|
[gain~ 0.5]  <- creates with initial gain of 0.5
|
[dac~]
```

### With Control
```
[flonum]
|
[gain~]
|
[dac~]
```

Send float values to change the gain in real-time.

## Parameters

- **Argument**: Initial gain value (default: 1.0)
  - Example: `gain~ 0.75` starts with gain of 0.75

- **Float inlet**: Sets gain value
  - Range: any float (negative values will invert phase)
  - 0.0 = silence
  - 1.0 = unity gain
  - >1.0 = amplification

## Debugging

### Print Messages

The external posts messages to Max's console:
- On creation: "gain~ initialized with gain: X"
- On DSP setup: sample rate and vector size info
- On gain change: "gain set to: X"

Open Max Console (Cmd+M) to see these messages.

### Xcode Debugging

To debug with breakpoints:

1. Build Debug configuration in Xcode
2. Product → Scheme → Edit Scheme
3. Set Executable to Max application
4. Set breakpoints in gain_tilde.cpp
5. Run (Cmd+R) - this launches Max
6. Use your gain~ object
7. Breakpoints will hit

## Next Steps

This is a minimal working external. Future enhancements:

- Add smoothing to prevent clicks when changing gain
- Add dB-to-linear conversion for more musical control
- Add Python/pybind11 wrapper for testing
- Add custom UI in SwiftUI

## Troubleshooting

**"Object not found"**: Max hasn't found the .mxo file
- Check that it's in ~/Documents/Max 8/Library/
- Restart Max
- Check Max Console for load errors

**Build errors**: SDK path issue
- Verify SDK path in CMakeLists.txt line 4
- Re-run setup.sh

**"Cannot be loaded due to system security policy"** (M1/M2 Mac):
```bash
codesign --force --deep -s - build/Debug/gain~.mxo
```

## File Details

### gain_tilde.cpp

The C++ source implements:
- `ext_main()`: Initialization, registers the class
- `gain_new()`: Object creation, sets up inlets/outlets
- `gain_dsp64()`: DSP chain setup
- `gain_perform64()`: Block-based audio processing (the actual DSP)
- `gain_float()`: Handles float messages to change gain
- `gain_free()`: Cleanup

### CMakeLists.txt

Configured to:
- Use absolute path to your Max SDK
- Include Max and MSP headers
- Link against Max frameworks
- Output gain~.mxo bundle

The SDK path is hardcoded, so this project works anywhere on your system.
