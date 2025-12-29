# Max/MSP Externals Development - Claude Context

This is the AI assistant context file for the Max/MSP externals project. All documentation is organized in the root directory - this file just provides context and pointers for Claude Code.

---

## Quick Context

**Current Status:** ✅ Production-ready development system
**Code Style:** K&R/Google C++ with 2-space indentation
**Build System:** CMake + Xcode, location-independent
**Pattern:** Attribute-based parameters with custom setters

---

## Critical Information

### Universal Binary Requirement ⚠️
**MUST build for both x86_64 and arm64** to work on Apple Silicon Macs.

In `CMakeLists.txt` line 23:
```cmake
set(CMAKE_OSX_ARCHITECTURES "x86_64;arm64")
```

Without this: "incorrect architecture" error in Max.

### Folder Naming Convention
- Folder: `andy.YOURNAME_tilde`
- Output: `andy.YOURNAME~.mxo`
- Class: `"andy.YOURNAME~"` (in code)
- SDK auto-converts `_tilde` → `~`

### Max Integration
- **Always restart Max** after rebuilding (aggressive caching!)
- Search path: Add `objects/` folder to Max File Preferences
- Use `andy.` prefix to avoid name collisions

---

## Documentation Guide

All documentation is organized in the root directory. Here's what exists and where to find it:

### 📚 Documentation Structure

```
Max Experiments/
├── README.md                           ← Project overview (start here)
├── documentation/
│   ├── QUICK_REFERENCE.md              ← Copy/paste patterns (most used)
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

| Project | Description | Key Files |
|---------|-------------|-----------|
| **andy.gain_tilde/** | Template external | `gain_tilde.cpp`, `ATTRIBUTE_UPDATE.md` |
| **andy.gain_project/** | Remote control system | OSC routing, iOS/macOS apps |

---

## Common Tasks

### Quick Start for Developers
1. Read **documentation/QUICK_REFERENCE.md** for copy/paste patterns
2. Use **templates/DSP_EXTERNAL_TEMPLATE.md** as boilerplate
3. Reference **examples/ATTRIBUTE_SETTERS_EXAMPLE.md** for complex parameters
4. See **documentation/BUILD_SYSTEM.md** for build configuration details

### Create New External from Template
```bash
cd "/Users/andy/Dropbox/Developer/AudioDev/Max Experiments"
cp -r andy.gain_tilde andy.YOURNAME_tilde
cd andy.YOURNAME_tilde
# Update class name in source file
# Build (see QUICK_REFERENCE.md)
```

### Build External
```bash
cd your_external_tilde
rm -rf build && mkdir build && cd build
cmake -G Xcode ..
xcodebuild -configuration Debug
```

### Verify Universal Binary
```bash
lipo -info ../../../objects/your.external~.mxo/Contents/MacOS/your.external~
# Must show: x86_64 arm64
```

---

## Key Pattern: Modern Attribute System

**Parameters as attributes** - UI agnostic, remote-control ready:

```cpp
// Attributes with custom setters
CLASS_ATTR_DOUBLE(c, "param", 0, t_obj, param);
CLASS_ATTR_ACCESSORS(c, "param", NULL, obj_param_set);

// Setter recalculates derived state
t_max_err obj_param_set(t_obj *x, void *attr, long argc, t_atom *argv) {
  x->param = atom_getfloat(argv);
  obj_calculate_internal_state(x);  // ← Key step
  return MAX_ERR_NONE;
}
```

**Pattern flow:**
```
Parameters (attributes) → Custom Setters → Internal State → DSP Processing
     ↑                        ↓                                  ↓
   UI/Network          Calculate coeffs                    Audio thread
```

**Benefits:**
- Thread-safe (automatic)
- Automatable in Max
- Saveable with patcher
- Inspector integration
- Remote control ready (OSC, Web, MIDI)

---

## For Claude Code

### When Creating New Externals:
1. **Start with** `documentation/QUICK_REFERENCE.md` for patterns
2. **Use** `templates/DSP_EXTERNAL_TEMPLATE.md` as boilerplate
3. **Follow** the attribute pattern (not legacy proxy inlets)
4. **Implement** custom setters for complex parameters
5. **Reference** `examples/ATTRIBUTE_SETTERS_EXAMPLE.md` for filter example

### When Building:
1. **Verify** `CMAKE_OSX_ARCHITECTURES "x86_64;arm64"` in CMakeLists.txt
2. **Build** with: `cmake -G Xcode .. && xcodebuild -configuration Debug`
3. **Check** with: `lipo -info` must show both architectures
4. **Remind user** to restart Max after every rebuild

### Code Style:
- **K&R braces** (opening brace on same line)
- **2-space indentation** (no tabs)
- **lowercase_with_underscores** for names
- See **documentation/CODING_STYLE.md** for complete details

### Documentation References:

When user asks about:
- **Build issues** → `documentation/BUILD_SYSTEM.md`
- **Code style** → `documentation/CODING_STYLE.md`
- **Creating externals** → `templates/DSP_EXTERNAL_TEMPLATE.md`
- **Quick patterns** → `documentation/QUICK_REFERENCE.md`
- **OSC/routing** → `documentation/DISTRIBUTED_ROUTING_EXAMPLE.md`
- **Architecture/concepts** → `docs/MAX_PROCESSING_MODELS.md`
- **Complex parameters** → `examples/ATTRIBUTE_SETTERS_EXAMPLE.md`
- **History/learnings** → `archive/SESSION_ARCHIVE_2025-12.md`
- **Working example** → `andy.gain_tilde/gain_tilde.cpp`
- **Remote control** → `andy.gain_project/`

---

## Project Status

### ✅ Completed:
- Universal binary build system (x86_64 + arm64)
- Modern attribute-based parameter system
- Complete documentation suite
- Production-ready template
- Working examples (gain~, remote control)
- AI-assisted development workflow

### 🎯 Ready For:
- Building new DSP externals
- Adding complex parameters with custom setters
- Remote control (WiFi/Web/OSC)
- Scaling to complex hierarchical systems

---

## Resources

- **Max SDK:** `/Users/andy/Dropbox/Developer/AudioDev/max-sdk/`
- **Max SDK Docs:** `max-sdk/MaxAPI.pdf`
- **SDK Examples:** `max-sdk/source/audio/`

---

## Key Learnings

### Build System
- SDK defaults to Intel-only → must override for Apple Silicon
- Projects can exist anywhere (location-independent)
- All build output goes to shared `objects/` folder at project root

### Modern Pattern
- Attributes are the right approach (not proxy inlets)
- Custom setters for derived state (coefficients, etc.)
- Same interface for Max UI, OSC, Web, MIDI
- Separation: Parameters → Internal State → DSP

### Code Generation
- Attribute boilerplate is consistent → AI can generate it
- Templates provide starting point
- Examples demonstrate complex cases

---

*This is the only file in `.claude/` - all other documentation is in the root directory structure shown above.*
