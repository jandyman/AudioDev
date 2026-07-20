# Max/MSP Externals Development

This folder contains Max/MSP external projects for live audio processing.

## Projects

### andy.gain_tilde
Simple gain control external - serves as **template project** for creating new externals.

**Status:** Working template with universal binary support

## Documentation

```
Max Experiments/
├── documentation/
│   ├── QUICK_REFERENCE.md              ← Copy/paste patterns (START HERE)
│   ├── BUILD_SYSTEM.md                 ← Build configuration and CMake
│   ├── CODING_STYLE.md                 ← K&R/Google C++ standards
│   └── DISTRIBUTED_ROUTING_EXAMPLE.md  ← OSC routing walkthrough
├── templates/
│   └── DSP_EXTERNAL_TEMPLATE.md        ← Production-ready template
├── examples/
│   └── ATTRIBUTE_SETTERS_EXAMPLE.md    ← Biquad filter with custom setters
├── docs/
│   └── MAX_PROCESSING_MODELS.md        ← Deep dive: control vs signal rate
└── archive/
    └── SESSION_ARCHIVE_2025-12.md      ← Session history and learnings
```

### 🎯 Working Projects

| Project | Description |
|---------|-------------|
| **andy.gain_tilde/** | Template external - modern attribute system |
| **andy.gain_project/** | Remote control system (OSC, iOS/macOS apps) |

## Quick Start

### Prerequisites
```bash
# Verify you have:
- Max SDK at: /Users/andy/Dropbox/Developer/AudioDev/max-sdk
- Xcode with command line tools
- CMake: brew install cmake
```

### Create New External from Template

```bash
cd "/Users/andy/Dropbox/Developer/AudioDev/Max Experiments"

# 1. Copy template
cp -r andy.gain_tilde andy.YOURNAME_tilde
cd andy.YOURNAME_tilde

# 2. Update class name in source code
# Edit gain_tilde.cpp line 32: class_new("andy.YOURNAME~", ...)

# 3. Generate build
rm -rf build && mkdir build && cd build
cmake -G Xcode ..

# 4. Build
xcodebuild -configuration Debug
# OR: open andy.YOURNAME_tilde.xcodeproj and press Cmd+B

# 5. Verify universal binary
lipo -info ../objects/andy.YOURNAME~.mxo/Contents/MacOS/andy.YOURNAME~
# Should show: x86_64 arm64
```

### Add to Max
Max → Options → File Preferences → Add search path:
```
/Users/andy/Dropbox/Developer/AudioDev/Max Experiments/objects
```

Restart Max, then create: `andy.YOURNAME~`

## Key Learnings

### Build System
- **Location Independent**: Projects can exist anywhere, not tied to SDK location
- **Universal Binary**: MUST build for both x86_64 and arm64 on modern Macs
- **Folder Naming**: Use `_tilde` suffix → SDK converts to `~` in output
- **Output Location**: All builds go to shared `objects/` folder at project root

### Architecture Support
**Critical:** SDK defaults to Intel-only (x86_64). This causes "incorrect architecture" errors on Apple Silicon Macs.

**Solution:** Add to CMakeLists.txt before including SDK:
```cmake
set(CMAKE_OSX_ARCHITECTURES "x86_64;arm64")
```

### Max Integration
- **Restart Required**: Max caches externals - always restart after rebuild
- **Search Order**: Local folder → Custom paths → Built-ins
- **Name Collisions**: Use unique prefixes (e.g., `andy.gain~` not `gain~`)

## Development Workflow

1. Edit source code in your editor
2. Build in Xcode (Cmd+B) or `xcodebuild -configuration Debug`
3. **Restart Max** (critical!)
4. Test external in Max patcher
5. Check Max Console (Cmd+M) for debug output

## Project Structure Standards

Each external project should contain:
```
andy.YOURNAME_tilde/
├── CMakeLists.txt          # Build configuration (see template)
├── YOURNAME_tilde.cpp      # External source code
├── README.md               # External-specific documentation
└── build/                  # Generated build artifacts (gitignored)
    └── externals/
        └── andy.YOURNAME~.mxo
```

## Common Issues

### "no such object"
- Check Max search path includes `objects/`
- Restart Max
- Check Max Console for load errors

### "incorrect architecture"
- Rebuild with universal binary support
- Verify: `lipo -info path/to/binary`
- Should show both x86_64 and arm64

### Build succeeds but changes don't appear
- Clean build: Shift+Cmd+K in Xcode
- Restart Max (it caches externals aggressively)
- Verify .mxo timestamp is recent

## Resources

- **Max SDK**: `/Users/andy/Dropbox/Developer/AudioDev/max-sdk/`
- **Max SDK Docs**: `max-sdk/MaxAPI.pdf`
- **SDK Examples**: `max-sdk/source/audio/` (working examples)
- **This Guide**: See documentation files in this folder

## Code Style

- K&R/Google C++ style
- 2-space indentation (no tabs)
- Opening brace on same line
- See [CODING_STYLE.md](CODING_STYLE.md) for details

## Notes

- Universal binary support is **required** for Apple Silicon Macs
- Max caches externals - **always restart** after rebuilding
- The `build/build/` nested folder is normal (Xcode intermediates)
- Build artifacts should be in `.gitignore`
