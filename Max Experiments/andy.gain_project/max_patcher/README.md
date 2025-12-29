# Max OSC Integration Patcher

This patcher receives OSC (Open Sound Control) messages and controls the `andy.gain~` external.

## Setup

### 1. Configure Max Search Path

Add the external build directory to Max's search path:

1. Open Max → Options → File Preferences
2. Click "+" to add a new path
3. Navigate to: `/Users/andy/Dropbox/Developer/AudioDev/Max Experiments/objects`
4. Save preferences
5. **Restart Max** (critical - Max caches externals)

### 2. Install OSC-route (if needed)

The patcher uses `OSC-route` object for parsing OSC messages.

- Check if it's installed: Create object → type `OSC-route`
- If missing, install via Package Manager:
  - Max → File → Show Package Manager
  - Search for "CNMAT OSC" or "odot"
  - Install the OSC package

### 3. Open Patcher

1. Open `andy.gain_osc.maxpat` in Max
2. Lock patcher (Cmd+E)
3. Enable audio (click speaker icon bottom-right)

## Signal Flow

```
UDP Port 7400
    ↓
[udpreceive 7400]  ← Listen for OSC messages
    ↓
[OSC-route /gain]  ← Extract /gain messages
    ↓
[flonum]           ← Display value (0.0 to 10.0)
    ↓
[gain $1]          ← Convert to attribute message
    ↓
[andy.gain~]       ← Set gain parameter
    ↑
[noise~]           ← Test signal
    ↓
[ezdac~]           ← Audio output
```

## Testing Locally (without UI app)

You can test OSC control using Python:

### Install Python OSC Library
```bash
pip install python-osc
```

### Ready-Made Test Scripts

Four test scripts are provided in this directory:

1. **`test_gain.py`** - Simple single value test
2. **`test_interactive.py`** - Automatic sequence of preset values
3. **`test_sweep.py`** - Smooth gain sweep (fade up/down)
4. **`test_repl.py`** - Interactive command-line controller

Run any of them:
```bash
python test_gain.py          # Quick test
python test_interactive.py   # Watch it change automatically
python test_sweep.py         # Smooth fade
python test_repl.py          # Type commands interactively
```

### Quick Test Script

Or create your own:

Create a simple test script:

```python
# test_gain.py
from pythonosc import udp_client

# Connect to Max (localhost, port 7400)
client = udp_client.SimpleUDPClient("127.0.0.1", 7400)

# Send gain messages
client.send_message("/gain", 0.5)   # Set gain to 0.5
client.send_message("/gain", 1.0)   # Set gain to 1.0 (unity)
client.send_message("/gain", 0.0)   # Mute
client.send_message("/gain", 5.0)   # +14dB
```

Run it:
```bash
python test_gain.py
```

You should hear the white noise volume change.

### Interactive Testing

For experimenting with different values:

```python
# test_interactive.py
from pythonosc import udp_client
import time

client = udp_client.SimpleUDPClient("127.0.0.1", 7400)

# Test sequence with pauses
test_values = [
    (0.0, "Mute"),
    (0.25, "Quiet"),
    (0.5, "Half"),
    (1.0, "Unity"),
    (2.0, "+6dB"),
    (5.0, "+14dB"),
    (1.0, "Back to Unity")
]

for gain, label in test_values:
    print(f"{label}: /gain {gain}")
    client.send_message("/gain", gain)
    time.sleep(1.5)  # Wait 1.5 seconds between changes

print("Test complete!")
```

### REPL Testing

For interactive exploration:

```python
# In Python REPL or iPython:
from pythonosc import udp_client

client = udp_client.SimpleUDPClient("127.0.0.1", 7400)

# Now type commands interactively:
client.send_message("/gain", 0.5)
client.send_message("/gain", 2.0)
# etc...
```

## OSC Message Format

**Address:** `/gain`
**Type:** `f` (float)
**Range:** `0.0` to `10.0`
**Example:** `/gain 0.75`

## Troubleshooting

### "andy.gain~ not found"
- Check Max search path includes `/Users/andy/Dropbox/Developer/AudioDev/Max Experiments/objects`
- Restart Max (it caches externals aggressively)
- Verify `.mxo` exists: `ls ../objects/`

### "OSC-route not found"
- Install CNMAT OSC package via Package Manager
- Alternative: Replace `OSC-route` with `route` (less flexible)

### No sound
- Enable audio (speaker icon bottom-right)
- Check system audio output device
- Check gain value isn't 0.0

### OSC not working
- Verify port 7400 is not blocked by firewall
- Check Max console for error messages
- Test with `oscsend` command first

## Network Configuration (for iPad remote)

To receive OSC from iPad on same WiFi:

1. Find Mac's IP address: System Preferences → Network
2. Update iPad app to send to Mac's IP (e.g., `192.168.1.100:7400`)
3. Ensure firewall allows UDP port 7400:
   - System Preferences → Security & Privacy → Firewall → Firewall Options
   - Allow incoming connections for Max

## Next Steps

- See `../ui_macos/` for Mac test application
- See `../ui_ios/` for iPad remote control app
