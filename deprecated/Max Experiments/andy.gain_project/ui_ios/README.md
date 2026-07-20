# GainControl - iOS/iPadOS App

SwiftUI application for controlling `andy.gain~` via OSC over WiFi.

## Features

- **iPad-optimized UI** with large touch targets
- **WiFi control** - Send OSC messages to Mac over network
- **Configurable IP address** - Settings panel to set Mac's IP
- **Real-time gain control** (0.0 to 10.0)
- **6 preset buttons** with large touch targets
- **Connection status indicator**
- **Portrait and landscape support**

## Requirements

- iOS/iPadOS 16.0 or later
- Mac and iPad on **same WiFi network**
- Max running on Mac with `andy.gain_osc.maxpat` open

## Building the App

The Xcode project is ready to build:

### 1. Open in Xcode

Double-click `GainControl.xcodeproj` or:
```bash
open GainControl.xcodeproj
```

### 2. Select Deployment Target

- **For iPad:** Select your iPad as destination
- **For Simulator:** Select "iPad Pro" or similar

### 3. Configure Signing

1. Select project in navigator
2. Select "GainControl" target
3. Signing & Capabilities tab
4. Set your Team (or use automatic signing)

### 4. Build and Run

Click ▶️ or press Cmd+R

## Network Setup

### Find Your Mac's IP Address

1. On Mac: System Preferences → Network
2. Note the IP address (e.g., `192.168.1.100`)

### Configure the iPad App

1. Launch app on iPad
2. Tap **gear icon** (top-right)
3. Enter Mac's IP address
4. Tap **Apply**
5. Connection indicator should turn **green**

## Usage

### Step 1: Start Max on Mac

1. Open `../../max_patcher/andy.gain_osc.maxpat`
2. Lock patcher (Cmd+E)
3. Enable audio (speaker icon)

You should hear white noise on Mac.

### Step 2: Launch iPad App

1. Run app on iPad
2. Configure Mac's IP in settings
3. Connection indicator turns green

### Step 3: Control Gain

- **Slider:** Drag to adjust gain (0.0 to 10.0)
- **Presets:**
  - **Mute:** 0.0 (silence)
  - **Quiet:** 0.25
  - **Half:** 0.5
  - **Unity:** 1.0 (normal level) ← Default
  - **+6dB:** 2.0 (twice as loud)
  - **Max:** 10.0 (maximum)

Volume on Mac should change in real-time!

## Architecture

```
iPad (WiFi)
    ↓
OSCController (Network framework)
    ↓
UDP Socket (Mac IP:7400)
    ↓
Mac [udpreceive 7400]
    ↓
[OSC-route /gain]
    ↓
[andy.gain~ @gain]
```

## Differences from macOS Version

| Feature | macOS | iOS/iPadOS |
|---------|-------|------------|
| **Network** | localhost | WiFi (configurable IP) |
| **UI Size** | Compact | Large touch targets |
| **Settings** | Hardcoded | Settings panel |
| **Orientation** | Fixed | Portrait + Landscape |
| **Deployment** | Mac only | iPad + iPhone |

## Code Structure

### GainControlApp.swift
- Entry point
- No window resizing (iOS)

### ContentView.swift
- Main UI with large controls
- Preset buttons with touch-friendly size
- Settings sheet for IP configuration
- NavigationView wrapper

### OSCController.swift
- Same OSC protocol as macOS
- Configurable host IP
- Network framework for UDP

## Testing on Simulator

The app will build and run on Simulator, but **OSC won't work** because:
- Simulator uses different network stack
- Can't reach Mac's UDP ports easily

**For full testing, deploy to physical iPad.**

## Troubleshooting

### Connection stays red

1. **Check WiFi:** Both devices on same network
2. **Check IP:** Mac's IP address is correct
3. **Check Max:** Patcher is running and unlocked
4. **Check Firewall:** Allow Max in Mac firewall settings

### IP address not working

Find Mac's IP:
```bash
# On Mac Terminal:
ifconfig | grep "inet " | grep -v 127.0.0.1
```

Look for line like: `inet 192.168.1.100`

### Slider moves but no audio change

- Enable audio in Max
- Check Max console for errors
- Try sending value manually in Max: `[gain 0.5(`

### App won't build

- Check deployment target (iOS 16.0+)
- Set signing team in project settings
- Clean build: Product → Clean Build Folder (Shift+Cmd+K)

## Firewall Configuration (Mac)

To allow UDP port 7400:

1. System Preferences → Security & Privacy
2. Firewall → Firewall Options
3. Add Max application
4. Allow incoming connections

Or via command line:
```bash
# Check if firewall is on
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate

# Add Max (if firewall is on)
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /Applications/Max.app
```

## Network Traffic Inspection

To see OSC messages being sent from iPad:

On Mac:
```bash
# Monitor UDP port 7400
sudo tcpdump -i en0 -n udp port 7400 -X
```

You should see OSC message bytes when moving the slider on iPad.

## Deploying to Physical iPad

### 1. Connect iPad

- USB cable to Mac
- Trust computer on iPad

### 2. Select Device

- In Xcode, select your iPad from device list (not Simulator)

### 3. Run

- Click ▶️
- App installs and launches on iPad

### 4. First Launch

- May need to trust developer certificate:
  - iPad: Settings → General → Device Management
  - Trust your developer profile

## Known Limitations

- **One-way communication:** iPad → Mac only (no feedback yet)
- **No connection retry:** Must manually reconnect if network drops
- **No persistence:** IP address not saved between launches
- **No validation:** Doesn't verify Max is actually running

## Future Enhancements

Potential additions:
- Save IP address to UserDefaults
- Bidirectional OSC (Max sends current gain back)
- Multiple parameters (pan, filter, etc.)
- Preset save/load
- Touch gestures (two-finger drag, pinch, etc.)
- Network discovery (find Mac automatically)
- Connection retry logic

## Technical Notes

- **OSC Format:** Same as macOS version (binary, big-endian)
- **UDP Transport:** Fast, low-latency, no connection overhead
- **Network Framework:** Modern Swift networking API
- **SwiftUI:** Declarative UI, works on iOS/iPadOS/macOS

## References

- [OSC Specification](http://opensoundcontrol.org/spec-1_0)
- [Network Framework](https://developer.apple.com/documentation/network)
- [SwiftUI iPad Apps](https://developer.apple.com/documentation/swiftui/)
- macOS version: `../ui_macos/` (same protocol, localhost)

---

**Status:** ✅ Built and tested in Simulator - Ready for deployment to iPad
