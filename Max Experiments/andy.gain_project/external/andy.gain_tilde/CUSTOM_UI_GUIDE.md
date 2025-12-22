# Custom UI for andy.gain~ in Max

## Quick Start: Using Built-in UI Objects

Since `andy.gain~` uses attributes, Max's built-in UI objects work automatically.

### Method 1: Simple Message Box (5 minutes)

**Create this patcher:**

```
Object Palette:
1. Press 'n' → type "noise~" → Enter
2. Press 'n' → type "andy.gain~" → Enter
3. Press 'n' → type "ezdac~" → Enter
4. Press 'n' → type "live.dial" → Enter
5. Press 'm' → type "gain $1" → Enter

Connections:
[noise~] → [andy.gain~] → [ezdac~]
                ↑
         [gain $1(
                ↑
         [live.dial]
```

**Configure live.dial:**
- Select it → Cmd+I (Inspector)
- Range and Display:
  - Range/Enum: 0.0 10.0
  - Unit Style: Float
- Parameter:
  - Parameter Mode Enable: ON
  - Name: gain
  - Range: 0.0 10.0

**How it works:**
1. User moves dial → outputs float
2. Message box converts to `gain <value>`
3. Sent to andy.gain~ → attribute setter called
4. Gain updated, coefficients recalculated (if any)

### Method 2: Using pattr System (More Professional)

The `pattr` system binds UI directly to object attributes without message boxes.

**Create this patcher:**

```
Objects needed:
1. [pattrstorage gain_preset]  ← Manages presets
2. [autopattr @autoname 1]     ← Auto-binds all UI
3. [live.dial @varname gain]   ← UI control
4. [noise~]
5. [andy.gain~ @gain 1.0]
6. [ezdac~]

Connections:
[pattrstorage gain_preset] (no connections needed)
[autopattr @autoname 1] (no connections needed)

[live.dial @varname gain] (NO patch cables!)
[noise~] → [andy.gain~] → [ezdac~]
```

**How to create:**

1. **Add objects:**
   ```
   n → pattrstorage gain_preset
   n → autopattr @autoname 1
   n → live.dial
   n → noise~
   n → andy.gain~
   n → ezdac~
   ```

2. **Configure live.dial (Inspector):**
   ```
   Parameter:
   - Parameter Mode Enable: ON
   - Type: Float
   - Range: 0.0 10.0
   - Unit Style: Float

   Scripting Name:
   - Scripting Name: gain
   ```

3. **Configure andy.gain~ (Inspector):**
   ```
   Parameter:
   - Parameter Mode Enable: ON

   Scripting Name:
   - Scripting Name: andy_gain
   ```

4. **Link them with pattrstorage:**
   - Click pattrstorage object
   - In Max console, type:
     ```
     pattrstorage gain_preset subscribe andy_gain::gain
     pattrstorage gain_preset subscribe gain
     ```

**Advantages:**
- No message boxes needed
- Automatic bidirectional sync (UI ↔ object)
- Preset management (store/recall)
- MIDI learn works automatically
- Automation recording works

### Method 3: Direct Inspector Control (Simplest)

**No UI objects needed!**

1. Create: `[andy.gain~]`
2. Lock patcher (Cmd+E)
3. Select object
4. Open Inspector (Cmd+I)
5. Adjust gain slider in Inspector

**Advantages:**
- Zero setup
- Perfect for testing
- Works immediately

**Disadvantages:**
- Not visible in patcher
- Can't see value while performing

---

## Built-in UI Objects You Can Use

### live.dial (Recommended)
- **Use for:** Continuous parameters (gain, frequency, Q)
- **Range:** Set in Inspector
- **Appearance:** Circular dial
- **MIDI learn:** Built-in

### live.slider (Alternative)
- **Use for:** Continuous parameters (vertical or horizontal)
- **Range:** Set in Inspector
- **Appearance:** Linear slider

### live.menu (For enums)
- **Use for:** Discrete choices (filter type, mode)
- **Options:** Set in Inspector

### live.toggle
- **Use for:** On/off (bypass, mute)
- **Values:** 0 or 1

### live.numbox
- **Use for:** Precise numeric entry
- **Allows:** Typing exact values

---

## Complete Example Patcher

Here's a professional layout:

```
┌─────────────────────────────────────────────────┐
│  andy.gain~ Control Panel                       │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────┐                                   │
│  │ [pattrstorage gain_preset]                   │
│  │ [1] [2] [3] [Store]                          │
│  └──────────┘                                   │
│                                                  │
│  ┌──────────┐                                   │
│  │  GAIN    │                                   │
│  │   [●]    │ ← live.dial @varname gain         │
│  │  0.50    │                                   │
│  └──────────┘                                   │
│                                                  │
│  ┌────────────────────────────┐                │
│  │ [noise~] → [andy.gain~]    │                │
│  │              ↓              │                │
│  │           [ezdac~]          │                │
│  └────────────────────────────┘                │
│                                                  │
└─────────────────────────────────────────────────┘
```

**Objects:**
1. `pattrstorage gain_preset` - Preset manager
2. `live.dial @varname gain` - Gain control
3. `noise~` - Test signal
4. `andy.gain~` - Your external
5. `ezdac~` - Audio output

**Setup:**
1. Create all objects
2. Connect audio: noise~ → andy.gain~ → ezdac~
3. Configure live.dial (see Method 2)
4. Test: Move dial, hear volume change

---

## Understanding Parameter Mode

**Parameter Mode** is what makes binding work:

When you enable "Parameter Mode" on a UI object:
- Object becomes automatable
- MIDI learn available
- Can be saved with presets
- Can be controlled by Max for Live (if used in Live)

**On andy.gain~:**
```
Inspector → Parameter:
✓ Parameter Mode Enable
```

**On live.dial:**
```
Inspector → Parameter:
✓ Parameter Mode Enable
Type: Float
Range: 0.0 to 10.0
```

---

## Testing Your UI

### Basic Test:
1. Create patcher as described
2. Lock patcher (Cmd+E)
3. Start audio (bottom-right speaker icon)
4. Move dial
5. Hear volume change ✅

### Advanced Test:
1. Move dial to 0.5
2. Save patcher (Cmd+S)
3. Close patcher
4. Reopen patcher
5. Check dial position - should be 0.5 ✅
6. Check audio - should be at 0.5 gain ✅

### Inspector Test:
1. Lock patcher
2. Select andy.gain~
3. Open Inspector (Cmd+I)
4. Change gain in Inspector
5. Watch live.dial update automatically ✅ (if using pattr)

---

## Next Steps: Multiple Parameters

If you add more parameters to andy.gain~:

```cpp
// Add pan attribute
CLASS_ATTR_DOUBLE(c, "pan", 0, t_gain, pan);
CLASS_ATTR_FILTER_CLIP(c, "pan", 0.0, 1.0);
CLASS_ATTR_LABEL(c, "pan", 0, "Pan");
CLASS_ATTR_SAVE(c, "pan", 0);
```

**Add to patcher:**
```
[live.dial @varname gain]
[live.dial @varname pan]
        ↓
[andy.gain~ @gain 0.5 @pan 0.5]
```

Both dials automatically work with pattr system!

---

## Common Mistakes

### ❌ Message box doesn't work
**Problem:** Typed `[gain 0.5]` instead of `[gain 0.5(`
**Solution:** Message boxes must end with `(`

### ❌ Dial doesn't control external
**Problem:** Range mismatch (dial 0-127, attribute 0.0-1.0)
**Solution:** Set dial range in Inspector to match attribute range

### ❌ Value doesn't save
**Problem:** Forgot `CLASS_ATTR_SAVE(c, "gain", 0);`
**Solution:** Add to external, rebuild

### ❌ pattr doesn't bind
**Problem:** Parameter Mode not enabled
**Solution:** Enable on both UI object and external

---

## Max Patcher File Format (Optional)

Max patchers are JSON files. If you want to generate them programmatically:

```json
{
  "patcher": {
    "boxes": [
      {
        "box": {
          "maxclass": "live.dial",
          "varname": "gain",
          "parameter_enable": 1,
          "range": [0.0, 10.0],
          "patching_rect": [100, 100, 41, 48]
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "andy.gain~",
          "patching_rect": [100, 200, 70, 22]
        }
      }
    ],
    "lines": [
      {
        "patchline": {
          "source": ["obj-1", 0],
          "destination": ["obj-2", 0]
        }
      }
    ]
  }
}
```

But it's much easier to create patchers visually in Max!

---

## Resources

**Max Help:**
- Select any object → Right-click → "Open [object] Help"
- Try: live.dial help, pattr help, pattrstorage help

**Max SDK Examples:**
```
/Users/andy/Dropbox/Developer/AudioDev/max-sdk/
source/audio/
  - Look at built-in objects with UI
```

**Tutorials:**
- Max → File → Open Package Manager → Max Tutorials
- Look for "Parameter and Preset Management"

---

## Summary

**Easiest:** Use Inspector (Cmd+I) - Zero setup
**Recommended:** live.dial + message box - Simple, visible
**Professional:** pattr system - Presets, automation, MIDI learn

Your external is already UI-ready because you used attributes! Any Max UI object can control it.
