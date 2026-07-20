# GainControl - macOS Test App

SwiftUI application for controlling `andy.gain~` via OSC (Open Sound Control) on localhost.

## Purpose

This is a **local testing app** that runs on the same Mac as Max. It validates the OSC protocol before deploying to iPad.

## Features

- Clean SwiftUI interface
- Real-time gain control (0.0 to 10.0)
- Preset buttons (Mute, Quiet, Half, Unity, +6dB)
- Connection status indicator
- OSC messages sent to `localhost:7400`

## Creating the Xcode Project

Since Xcode project files are complex and binary, create the project manually:

### 1. Create New Project

1. Open Xcode
2. File → New → Project
3. Select **macOS** → **App**
4. Click **Next**

### 2. Configure Project

- **Product Name:** `GainControl`
- **Team:** Your team (or "None")
- **Organization Identifier:** `com.yourname` (or any identifier)
- **Interface:** **SwiftUI**
- **Language:** **Swift**
- **Storage:** None (uncheck Core Data, CloudKit, etc.)

Click **Next**, save to: `ui_macos/`

### 3. Add Source Files

Replace the default files with the provided ones:

1. Delete the auto-generated `ContentView.swift` and `GainControlApp.swift`
2. Drag these files into the project:
   - `GainControlApp.swift`
   - `ContentView.swift`
   - `OSCController.swift`

Make sure "Copy items if needed" is **unchecked** (files are already in correct location).

### 4. Configure Build Settings

No special configuration needed! The app uses only built-in frameworks:
- SwiftUI (UI)
- Network (UDP/OSC)

### 5. Build and Run

1. Select target: **My Mac**
2. Click ▶️ (Run) or Cmd+R
3. App window should appear

## Usage

### Step 1: Start Max

1. Open `../max_patcher/andy.gain_osc.maxpat`
2. Lock patcher (Cmd+E)
3. Enable audio (speaker icon)

You should hear white noise.

### Step 2: Launch App

1. Run GainControl app from Xcode
2. Connection indicator should turn **green**
3. Move slider or click preset buttons
4. Gain should change in real-time!

### Step 3: Test

- **Slider:** Drag to adjust gain (0.0 to 10.0)
- **Mute:** Sets gain to 0.0 (silence)
- **Unity:** Sets gain to 1.0 (normal level)
- **+6dB:** Sets gain to 2.0 (twice as loud)

## OSC Protocol

The app sends OSC messages in this format:

```
Address: /gain
Type: float
Range: 0.0 to 10.0
Transport: UDP port 7400
```

**Example message:**
```
/gain 0.75
```

This maps directly to the `andy.gain~` attribute:
```
[andy.gain~ @gain 0.75]
```

## Architecture

```
SwiftUI UI Layer
    ↓
OSCController (Network framework)
    ↓
UDP Socket (localhost:7400)
    ↓
Max [udpreceive 7400]
    ↓
[OSC-route /gain]
    ↓
[andy.gain~ @gain]
```

## Troubleshooting

### Connection shows red (Disconnected)

- Make sure Max patcher is open and running
- Check that `udpreceive 7400` object exists in Max patcher
- Port 7400 might be blocked (unlikely on localhost)

### Slider moves but no audio change

- Enable audio in Max (speaker icon bottom-right)
- Check Max console for errors
- Try sending value manually in Max: `[gain 0.5(` message box

### App won't build

- Check Xcode version (macOS 13+ required for SwiftUI features used)
- Make sure all three `.swift` files are added to target
- Clean build folder: Product → Clean Build Folder (Shift+Cmd+K)

## Network Traffic Inspection

To see OSC messages being sent:

```bash
# Install socat (if needed)
brew install socat

# Monitor UDP port 7400
sudo tcpdump -i lo0 -n udp port 7400 -X
```

You should see OSC message bytes when moving the slider.

## Next Steps

Once this local test app works:

1. **Port to iOS/iPadOS:**
   - Change deployment target to iOS
   - Change `host` to Mac's IP address (e.g., "192.168.1.100")
   - Deploy to iPad on same WiFi network

2. **Add bidirectional communication:**
   - Max sends current gain value back to UI
   - UI displays actual state (not just local slider position)

3. **Add more parameters:**
   - Pan control
   - Multiple instances
   - Preset management

## Code Overview

### GainControlApp.swift
- Entry point
- Window configuration

### ContentView.swift
- SwiftUI interface
- Slider, buttons, labels
- Calls OSCController on value changes

### OSCController.swift
- UDP socket setup using Network framework
- OSC message formatting (binary protocol)
- Sends `/gain <float>` messages

## Technical Notes

- **UDP vs TCP:** UDP is used for low-latency control (no connection overhead)
- **OSC Format:** Binary format with 4-byte alignment (see OSC 1.0 spec)
- **Big-endian:** OSC uses network byte order (big-endian)
- **Type tags:** `,f` indicates one float argument

## References

- [OSC Specification](http://opensoundcontrol.org/spec-1_0)
- [Max OSC Documentation](https://docs.cycling74.com/max8/vignettes/osc_topic)
- [SwiftUI Documentation](https://developer.apple.com/documentation/swiftui/)
- [Network Framework](https://developer.apple.com/documentation/network)
