# andy.gain~ Updated to Modern Attributes

## What Changed

The `andy.gain~` external has been updated from legacy message handlers to the modern attribute-based approach.

### Before (Legacy):
```cpp
// Used gain_float() message handler
void gain_float(t_gain *x, double f) {
  x->gain_value = f;
}

// Registered with:
class_addmethod(c, (method)gain_float, "float", A_FLOAT, 0);
```

### After (Modern):
```cpp
// Uses attribute registration
CLASS_ATTR_DOUBLE(c, "gain", 0, t_gain, gain);
CLASS_ATTR_FILTER_CLIP(c, "gain", 0.0, 10.0);
CLASS_ATTR_LABEL(c, "gain", 0, "Gain");
CLASS_ATTR_SAVE(c, "gain", 0);
CLASS_ATTR_DEFAULT(c, "gain", 0, "1.0");

// Processes attributes automatically
attr_args_process(x, argc, argv);
```

## Benefits of Attributes

✅ **Thread-safe** - Max handles synchronization automatically
✅ **Automatable** - Can record parameter changes in Max
✅ **Saveable** - Saves with patcher file
✅ **Inspector integration** - Appears in object inspector
✅ **Queryable** - Can get current value
✅ **Range limiting** - Built-in clipping (0.0 to 10.0)
✅ **Default value** - Automatically set

## Usage in Max

### Setting Gain Value

**Via message:**
```
[gain 0.5(  → Set gain to 0.5
[gain 2.0(  → Set gain to 2.0
```

**At object creation:**
```
[andy.gain~ @gain 0.5]  → Creates with gain = 0.5
[andy.gain~]            → Creates with default gain = 1.0
```

**Via Inspector:**
- Click object
- Open Inspector (Cmd+I)
- Adjust "Gain" slider (range: 0.0 to 10.0)

### Getting Current Value

```
[getgain(  → Outputs current gain value
```

### Automation

The gain parameter can now be automated:
1. Enter presentation mode
2. Right-click object → "Automate Attribute" → "gain"
3. Record automation in your DAW or Max's `live.step` objects

### Saving with Patcher

When you save your Max patcher, the gain value is automatically saved.
```
[andy.gain~ @gain 0.75]  → Reopening patcher restores gain = 0.75
```

## Code Changes Summary

### Removed:
- `gain_float()` function (legacy message handler)
- Manual argument parsing in `gain_new()`
- `class_addmethod(c, (method)gain_float, ...)` registration
- Removed debug `object_post()` calls from DSP setup

### Added:
- Five `CLASS_ATTR_*` macros for attribute registration
- `attr_args_process()` call in constructor
- Automatic range clipping (0.0 - 10.0)
- Inspector integration
- Save/load capability

### Modified:
- Struct member: `gain_value` → `gain` (cleaner naming)
- Constructor now uses `attr_args_process()` for arguments
- Consistent 2-space indentation throughout

## Testing

1. **Restart Max** (required after rebuild!)
2. Create `[andy.gain~]` object
3. Test message control:
   ```
   [noise~] → [andy.gain~ @gain 0.5] → [dac~]
   [0.5(  → [andy.gain~]  (adjust gain)
   ```
4. Test inspector control (Cmd+I)
5. Save patcher and reopen to verify persistence

## Architecture

The external remains a universal binary:
```
$ lipo -info andy.gain~.mxo/Contents/MacOS/andy.gain~
Architectures: x86_64 arm64
```

Works on both Intel and Apple Silicon Macs.

## Next Steps

This modern attribute approach should be used for all future externals. See `MAX_PROCESSING_MODELS.md` for complete documentation on:
- Custom attribute getters/setters
- Multiple attributes
- Attribute arrays
- Advanced attribute features

## File Location

```
andy.gain_tilde/
├── gain_tilde.cpp        ← Updated source code
├── CMakeLists.txt        ← Unchanged (universal binary config)
├── build/
│   └── externals/
│       └── andy.gain~.mxo ← Rebuilt external
└── ATTRIBUTE_UPDATE.md   ← This file
```
