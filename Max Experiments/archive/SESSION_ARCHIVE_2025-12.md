# Session Archive - December 2025

Consolidated session notes from Max/MSP external development project.

---

## Session 1: Universal Binary Build Success (2025-12-01)

### Accomplishments
- ✅ Fixed Bash tool (working after restart)
- ✅ Successfully rebuilt `andy.gain~` with universal binary support
- ✅ Verified with `lipo`: both `x86_64` and `arm64` architectures present
- ✅ Tested in Max: loads correctly, passes signal
- ✅ **Architecture error RESOLVED** - external works on Apple Silicon!

### Key Learnings

#### Build System
- **Critical:** SDK defaults to Intel-only, breaks on Apple Silicon
- **Solution:** Add `CMAKE_OSX_ARCHITECTURES "x86_64;arm64"` before SDK include
- **Folder Naming:** Use `_tilde` suffix → SDK converts to `~` in output
- **Location Independence:** Override `C74_SUPPORT_DIR` and `C74_LIBRARY_OUTPUT_DIRECTORY`

#### Architecture Issue
- **Symptom:** "could not load due to incorrect architecture"
- **Cause:** Built for x86_64 only
- **Fix:** Universal binary configuration in CMakeLists.txt line 23
- **Verification:** `lipo -info` should show both architectures

#### Max Integration
- Always **restart Max** after rebuilding (caches externals)
- Search path order: Local → Custom → Built-ins
- Use unique names to avoid collisions

### Documentation Created
- README.md - Overview and quick start
- BUILD_SYSTEM.md - Build configuration guide
- CODING_STYLE.md - K&R/Google C++ standards
- NEW_EXTERNAL_GUIDE.md - Step-by-step checklist

---

## Session 2: Modern Attribute System (2025-12-02)

### Accomplishments

#### 1. Understanding Max's Processing Models ✅
Created comprehensive documentation covering:
- Control-rate vs. signal-rate processing
- Event-based vs. block-based execution
- Thread safety considerations
- Message routing and naming conventions

**Key insight:** Audio objects are hybrid - they process continuous audio blocks while responding to discrete control messages.

#### 2. Modern Attribute System ✅
Explored and documented the attribute-based parameter system:
- **Why it's better:** Thread-safe, automatable, saveable, inspector integration
- **Legacy alternatives:** Proxy inlets (messy, 1988 design) and named message handlers
- **Custom setters:** For complex parameters that need side effects (coefficient recalculation)

#### 3. Multichannel (MC) Support ✅
Documented Max 8's MC system:
- Single inlet/outlet carries multiple channels (1 to 4096+)
- Cleaner than old multi-inlet approach
- Dynamic channel counts
- More efficient than wrapped instances

#### 4. Updated andy.gain~ to Modern Pattern ✅

**Before:**
```cpp
void gain_float(t_gain *x, double f) {
  x->gain_value = f;
}
```

**After:**
```cpp
CLASS_ATTR_DOUBLE(c, "gain", 0, t_gain, gain);
CLASS_ATTR_FILTER_CLIP(c, "gain", 0.0, 10.0);
CLASS_ATTR_SAVE(c, "gain", 0);
```

**Benefits gained:**
- Thread-safe
- Automatable in Max
- Saveable with patcher
- Inspector integration
- Range limiting (0.0 to 10.0)
- Queryable via `[getgain(`

#### 5. Created DSP External Template ✅
Comprehensive template with:
- Complete working code structure
- Custom setter pattern for derived state
- Checklist for new externals
- Common patterns (time-based, frequency-based, enums, buffers)

### Technical Patterns Established

#### Custom Setter Pattern
```cpp
t_max_err module_param_set(t_module *x, void *attr, long argc, t_atom *argv) {
  if (argc && argv) {
    double value = atom_getfloat(argv);
    x->param = value;
    module_calculate_coefficients(x);  // Recalc derived state
  }
  return MAX_ERR_NONE;
}
```

#### Separation of Concerns
- **Parameters** - User-facing attributes (Hz, Q, gain, etc.)
- **Internal state** - Derived values (coefficients, phase increments)
- **DSP state** - History variables, buffers
- **Calculate function** - Converts parameters → internal state

### Architectural Insights

**Why attributes are ideal for DSP:**
```
UI Layer          → Attributes ← Remote Control (OSC/Web/MIDI)
                       ↓
              Custom Setters (main thread)
                       ↓
           Internal State (coefficients, buffers)
                       ↓
              DSP Processing (audio thread)
```

**Advantages:**
1. **UI Independence** - Change UI without touching DSP code
2. **Remote Ready** - Network protocols just query/set attributes
3. **Testable** - Programmatic control for unit tests
4. **Maintainable** - Clear contracts between layers
5. **Consistent** - Same pattern scales from simple to complex

### Documentation Created
- MAX_PROCESSING_MODELS.md - Complete processing model documentation
- ATTRIBUTE_SETTERS_EXAMPLE.md - Biquad filter with custom setters
- DSP_EXTERNAL_TEMPLATE.md - Production-ready template
- ATTRIBUTE_UPDATE.md - Migration guide

---

## Session 3: Remote Control Architecture (2025-12-02)

### Complete Working System Built ✅

Created a full remote control project with 4 components:

1. **Max External** (`andy.gain~`)
   - C++ audio processing with attribute-based parameters
   - Universal binary (x86_64 + arm64)
   - Modern attribute system

2. **Max Patcher** (`andy.gain_osc.maxpat`)
   - OSC receiver on UDP port 7400
   - Routes messages to andy.gain~ external

3. **macOS SwiftUI App**
   - Localhost testing app
   - OSC sender to port 7400
   - **Built successfully** ✅

4. **iOS/iPadOS SwiftUI App**
   - WiFi remote control
   - Configurable Mac IP address
   - **Built successfully** ✅

### Key Concepts Discussed

#### OSC (Open Sound Control)
**What it is:**
- Message format: `/address value` (e.g., `/gain 0.75`)
- Transport: UDP (low latency, connectionless)
- Industry standard for audio/music remote control

**What it is NOT:**
- ❌ Device discovery protocol
- ❌ Capability introspection system
- ❌ Acknowledgement/retry mechanism

**Key insight:** OSC is just a message format. Everything else must be built on top.

#### Max's Dual Processing Model
```
MESSAGE DOMAIN (Control-rate)          SIGNAL DOMAIN (Audio-rate)
- Discrete events                      - Continuous samples
- Asynchronous                         - Synchronous (44,100 Hz)
- "gain 0.75"                          - Audio buffers
```

**Critical concept:** A single inlet can receive BOTH message and audio data. Max routes them to different handlers internally.

#### Message Routing in Max
**Critical rule:** Unhandled messages do NOT pass through automatically.

**This is different from Unix pipes** - every level must strip its path prefix and route explicitly.

#### Distributed vs Centralized Routing

**Centralized:**
```
[andy.osc_router]  ← Single external handles ALL routing
```

**Distributed (Recommended):**
```
Level 1: [OSC-route /master /channel]
Level 2:   [OSC-route /preamp /eq]
Level 3:     [OSC-route /band1 /band2]
```

**Conclusion:** Distributed routing matches Max's patcher hierarchy naturally and scales better for heterogeneous systems.

#### Hierarchical Path Architecture

For heterogeneous, nested systems:
```
/master/
  /compressor/...
  /eq/
    /band1/...
    /band2/...
/channel/1/
  /preamp/...
  /gate/...
/effects/
  /reverb1/...
```

**Key insight:** OSC-route IS the distributed parser - it strips path prefixes at each level automatically.

### Architectural Decisions

#### ✅ Confirmed Approaches:
1. **OSC for transport** - Industry standard
2. **Attribute-based parameters** - UI-agnostic, remote-ready
3. **Distributed routing** - Matches Max's paradigm
4. **Hierarchical paths** - Scalable for heterogeneous systems
5. **Patcher routing** - Visual, debuggable, modular

#### 🤔 Still To Decide:
1. Bidirectional vs one-way communication
2. Discovery mechanism (auto-find or manual)
3. Registry external for introspection
4. Error handling and reporting
5. Multiple UI clients support

### Documentation Created
- DISTRIBUTED_ROUTING_EXAMPLE.md - Message routing walkthrough
- Project README for andy.gain_project
- BUILD_STATUS.md - Build verification

---

## Comparison: Legacy vs. Modern

| Aspect | Legacy (Proxy Inlets) | Modern (Attributes) |
|--------|----------------------|---------------------|
| **Thread safety** | Manual | Automatic |
| **UI integration** | Inlet-based (limited) | Any UI (unlimited) |
| **Remote control** | Complex routing | Direct attribute access |
| **Automation** | Not supported | Native support |
| **Persistence** | Manual | Automatic |
| **Inspector** | Not available | Automatic |
| **Setup complexity** | High (proxies) | Medium (macros) |
| **Boilerplate** | Manual dispatch | AI-assisted |

---

## Overall Status: Production Ready ✅

The established pattern is:
- ✅ Proven (built, tested across multiple projects)
- ✅ Documented (comprehensive guides and examples)
- ✅ Templated (ready to copy/paste)
- ✅ Scalable (works from simple to complex)
- ✅ Future-proof (UI agnostic, remote ready)

### File Structure Created
```
Max Experiments/
├── README.md
├── BUILD_SYSTEM.md
├── CODING_STYLE.md
├── NEW_EXTERNAL_GUIDE.md
├── templates/
│   └── DSP_EXTERNAL_TEMPLATE.md
├── examples/
│   └── ATTRIBUTE_SETTERS_EXAMPLE.md
├── docs/
│   └── MAX_PROCESSING_MODELS.md
├── andy.gain_tilde/                   ← Template project
└── andy.gain_project/                 ← Remote control project
    ├── external/andy.gain_tilde/
    ├── max_patcher/
    ├── ui_macos/
    └── ui_ios/
```

---

## Key Quotes

> "There is a lot of boilerplate, but Claude AI makes this painless."

**True!** The attribute system requires consistent boilerplate, but:
- AI can generate it from spec
- One-time cost, long-term benefits
- Same pattern works for all modules

---

> "This will map perfectly to WiFi/web UIs"

**Absolutely correct!** Attributes were designed exactly for this use case:
```
Local Max UI ←→ Attributes ←→ Remote WebSocket client
                    ↕
              OSC controller
                    ↕
              MIDI Learn
```

---

## Next Steps

### Ready For:
- 🎯 Building new DSP externals using established pattern
- 🎯 Adding complex parameters with custom setters
- 🎯 Remote control (WiFi/Web/OSC) - attributes are interface-ready
- 🎯 Scaling to complex hierarchical systems

### Future Modules (examples to build):
- **andy.biquad~** - Biquad filter
- **andy.delay~** - Delay line with modulation
- **andy.env~** - Envelope follower
- **andy.osc~** - Wavetable oscillator
- **andy.verb~** - Reverb processor

### Advanced Features to Consider:
- Device discovery mechanisms
- Capability introspection systems
- Bidirectional state synchronization
- VU meters and real-time displays
- Multiple client support

---

## Resources

- **Max SDK:** `/Users/andy/Dropbox/Developer/AudioDev/max-sdk/`
- **Max SDK Docs:** `max-sdk/MaxAPI.pdf`
- **SDK Examples:** `max-sdk/source/audio/`
- **Templates:** `Max Experiments/templates/`
- **Examples:** `Max Experiments/examples/`

---

*End of Session Archive*
