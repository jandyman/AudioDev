# andy.gain~ Remote Control Project

Complete system for controlling Max/MSP audio externals remotely via OSC (Open Sound Control).

## Overview

This project demonstrates the full stack for remote control of Max audio processing:

1. **Max External** (`andy.gain~`) - Audio processing with attribute-based parameters
2. **Max Patcher** - OSC receiver and routing
3. **macOS Test App** - SwiftUI controller (localhost testing)
4. **iPad App** - Remote control over WiFi (future)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Remote UI Layer                                             │
│  ┌──────────────────┐        ┌──────────────────┐          │
│  │  SwiftUI Mac App │   OR   │  SwiftUI iPad App│          │
│  │   (localhost)    │        │   (WiFi network) │          │
│  └────────┬─────────┘        └────────┬─────────┘          │
└───────────┼──────────────────────────┼────────────────────┘
            │                           │
            └───────────┬───────────────┘
                        │ OSC Messages
                        │ UDP Port 7400
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  Max/MSP Layer                                               │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Max Patcher (andy.gain_osc.maxpat)                │    │
│  │  ┌──────────────┐  ┌──────────┐  ┌─────────────┐  │    │
│  │  │ udpreceive   │→ │OSC-route │→ │gain $1      │  │    │
│  │  │ 7400         │  │/gain     │  │message      │  │    │
│  │  └──────────────┘  └──────────┘  └──────┬──────┘  │    │
│  └─────────────────────────────────────────┼─────────┘    │
│                                              ↓               │
│  ┌────────────────────────────────────────────────────┐    │
│  │  andy.gain~ External (andy.gain~.mxo)              │    │
│  │  - Attribute: @gain (0.0 to 10.0)                  │    │
│  │  - DSP: Multiply audio signal by gain              │    │
│  │  - Universal binary (x86_64 + arm64)               │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
andy.gain_project/
├── README.md                          ← This file
├── external/
│   └── andy.gain_tilde/              ← Max external source
│       ├── gain_tilde.cpp            ← C++ implementation
│       ├── CMakeLists.txt            ← Build configuration
│       ├── CUSTOM_UI_GUIDE.md        ← Max UI integration
│       └── build/externals/
│           └── andy.gain~.mxo        ← Built external (universal)
├── max_patcher/
│   ├── andy.gain_osc.maxpat          ← OSC integration patcher
│   └── README.md                      ← Setup instructions
├── ui_macos/
│   ├── GainControl/                   ← SwiftUI Mac app (localhost)
│   │   ├── GainControlApp.swift
│   │   ├── ContentView.swift
│   │   └── OSCController.swift
│   └── README.md                      ← Build instructions
└── ui_ios/
    └── (future iPad app)              ← Remote WiFi control
```

## Quick Start

### 1. Build the External

```bash
cd external/andy.gain_tilde
rm -rf build && mkdir build && cd build
cmake -G Xcode ..
xcodebuild -configuration Debug
lipo -info externals/andy.gain~.mxo/Contents/MacOS/andy.gain~
# Should show: x86_64 arm64
```

### 2. Configure Max

1. Open Max → Options → File Preferences
2. Add path: `external/andy.gain_tilde/build/externals/`
3. **Restart Max** (critical!)

### 3. Open Max Patcher

1. Open `max_patcher/andy.gain_osc.maxpat`
2. Lock patcher (Cmd+E)
3. Enable audio (speaker icon)
4. You should hear white noise

### 4. Test with Python

```bash
# Install Python OSC library
pip install python-osc

# Create test script
cat > test_osc.py << 'EOF'
from pythonosc import udp_client

# Connect to Max
client = udp_client.SimpleUDPClient("127.0.0.1", 7400)

# Send gain value
client.send_message("/gain", 0.5)
print("Sent: /gain 0.5")
EOF

# Run it
python test_osc.py
# Noise volume should change!
```

For interactive testing:
```python
# test_interactive.py
from pythonosc import udp_client
import time

client = udp_client.SimpleUDPClient("127.0.0.1", 7400)

# Test different gain values
gains = [0.0, 0.25, 0.5, 1.0, 2.0, 0.5]
for gain in gains:
    print(f"Setting gain to {gain}")
    client.send_message("/gain", gain)
    time.sleep(1)  # Wait 1 second between changes
```

### 5. Build Mac Test App

1. Open Xcode
2. Create new macOS App project → Save in `ui_macos/`
3. Add source files from `ui_macos/GainControl/`
4. Run app (Cmd+R)
5. Move slider → Gain changes in real-time!

See detailed instructions in each folder's README.

## Key Concepts

### Attribute-Based Parameters

The external uses Max's modern attribute system:

```cpp
CLASS_ATTR_DOUBLE(c, "gain", 0, t_gain, gain);
CLASS_ATTR_FILTER_CLIP(c, "gain", 0.0, 10.0);
CLASS_ATTR_SAVE(c, "gain", 0);
```

**Benefits:**
- UI agnostic - works with any interface
- Thread-safe by design
- Inspector integration
- Save/load support
- **Remote control ready** ✨

### OSC Protocol

Simple, text-based addresses with typed arguments:

```
/gain 0.75    ← Address + float value
```

**Why OSC?**
- Industry standard (music/audio)
- Human-readable addresses
- Built-in Max support
- Works over UDP (low latency)
- Easy to debug

### Localhost → Network

The **same code** works for:
- **Localhost testing:** `127.0.0.1:7400` (Mac to Mac)
- **WiFi remote:** `192.168.1.100:7400` (iPad to Mac)

Just change the IP address!

## OSC Message Format

| Component | Value | Description |
|-----------|-------|-------------|
| **Address** | `/gain` | Parameter identifier |
| **Type** | `f` | Float (32-bit) |
| **Range** | `0.0` to `10.0` | Gain value |
| **Transport** | UDP | Port 7400 |

Example messages:
```
/gain 0.0    ← Mute
/gain 0.5    ← Half volume
/gain 1.0    ← Unity gain
/gain 2.0    ← +6dB
/gain 10.0   ← +20dB (max)
```

## Development Workflow

### Phase 1: Local Testing ✅
1. Build external
2. Create Max patcher with OSC receiver
3. Test with `oscsend` command line
4. Build Mac test app
5. Verify real-time control

### Phase 2: Remote Control (Next)
1. Create Xcode iOS project
2. Copy SwiftUI code from Mac app
3. Change `localhost` to Mac's IP
4. Deploy to iPad
5. Control over WiFi!

### Phase 3: Enhancements (Future)
- Bidirectional communication (Max sends state back)
- Multiple parameters (pan, filter, etc.)
- Multiple instances
- Preset management
- Touch gestures (iPad-specific)

## Troubleshooting

### External won't load in Max
- Check Max search path includes `external/andy.gain_tilde/build/externals/`
- **Restart Max** (aggressive caching!)
- Verify with: `lipo -info andy.gain~.mxo/Contents/MacOS/andy.gain~`

### OSC not working
- Check firewall allows UDP port 7400
- Verify Max patcher is running (not locked in edit mode)
- Test with `oscsend` command first
- Check Max console for errors

### No sound
- Enable audio in Max (speaker icon)
- Check system audio output
- Gain might be set to 0.0 (mute)

## Technical Stack

| Layer | Technology |
|-------|------------|
| **DSP** | C++ (Max SDK) |
| **Audio Host** | Max/MSP 8+ |
| **Protocol** | OSC 1.0 |
| **Transport** | UDP (Network framework) |
| **UI (Mac)** | SwiftUI |
| **UI (iOS)** | SwiftUI (future) |
| **Build** | CMake + Xcode |

## File Naming Convention

- **Folder:** `andy.gain_tilde` (underscore)
- **Binary:** `andy.gain~.mxo` (tilde symbol)
- **Class:** `"andy.gain~"` (in code)
- **Max object:** `[andy.gain~]` (in patcher)

Max SDK automatically converts `_tilde` → `~` during build.

## Why This Pattern?

This architecture separates concerns cleanly:

```
UI Layer    → Protocol Layer → Max Layer → DSP Layer
(SwiftUI)      (OSC/UDP)       (routing)   (C++ audio)
```

**Benefits:**
1. **UI independence** - Swap UI without touching DSP code
2. **Testability** - Each layer can be tested independently
3. **Scalability** - Add parameters without UI changes
4. **Remote ready** - WiFi, Web, MIDI all use same attributes
5. **Maintainability** - Clear contracts between layers

## Next Steps

1. ✅ Build and test external
2. ✅ Test OSC with command line
3. ✅ Build Mac test app
4. ⏭️ Create iPad app
5. ⏭️ Add bidirectional communication
6. ⏭️ Add more parameters (pan, filter, etc.)

## Resources

- **Max SDK:** `/Users/andy/Dropbox/Developer/AudioDev/max-sdk/`
- **OSC Spec:** http://opensoundcontrol.org/spec-1_0
- **Max OSC:** https://docs.cycling74.com/max8/vignettes/osc_topic
- **SwiftUI:** https://developer.apple.com/documentation/swiftui/

## License

This is a demonstration project for learning Max external development and OSC communication.

## Author

Created as a template for remote-controlled Max audio processing.

---

**Status:** Phase 1 complete - Ready for local testing! 🎉
