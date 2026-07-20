# Distributed Routing - Concrete Example

## Simple Two-Level Hierarchy

This example shows how OSC messages flow through nested patchers using distributed routing.

### The Hierarchy

```
Main Patcher
├── /master
│   ├── /preamp (andy.gain~)
│   └── /eq (subpatcher)
│       ├── /band1 (andy.filter~)
│       └── /band2 (andy.filter~)
└── /channel
    └── /1 (subpatcher)
        ├── /preamp (andy.gain~)
        └── /comp (andy.compressor~)
```

---

## Message Flow Example

### iPad sends: `/master/eq/band1/frequency 440`

**Step 1: Main Patcher**
```
[udpreceive 7400]  ← Receives: /master/eq/band1/frequency 440
    ↓
[OSC-route /master /channel]  ← Matches "/master"
    ↓                            Strips it off
Outputs: /eq/band1/frequency 440
    ↓
[p master]  ← Sends to master subpatcher
```

**Step 2: [p master] Subpatcher**
```
[inlet]  ← Receives: /eq/band1/frequency 440
    ↓
[OSC-route /preamp /eq]  ← Matches "/eq"
    ↓                       Strips it off
Outputs: /band1/frequency 440
    ↓
[p eq]  ← Sends to eq subpatcher
```

**Step 3: [p eq] Subpatcher**
```
[inlet]  ← Receives: /band1/frequency 440
    ↓
[OSC-route /band1 /band2]  ← Matches "/band1"
    ↓                         Strips it off
Outputs: /frequency 440
    ↓
[andy.filter~ @name band1]  ← Receives: /frequency 440
    ↓
[OSC-route /frequency /q /gain]  ← Matches "/frequency"
    ↓                                Strips it off
Outputs: 440
    ↓
[prepend frequency(  ← Creates message: "frequency 440"
    ↓
Back to [andy.filter~]  ← Sets frequency attribute
```

---

## Key Mechanisms

### 1. OSC-route Strips Prefix

**Input:**  `/master/eq/band1/frequency 440`
**After:** `[OSC-route /master]`
**Output:** `/eq/band1/frequency 440`

The matched component is **removed**, remainder is **passed through**.

### 2. Each Level is Self-Contained

**[p master] doesn't know about:**
- The parent patcher
- Its siblings (/channel)
- What comes before /master in the path

**[p master] only handles:**
- Messages that start with /preamp
- Messages that start with /eq
- Nothing else

### 3. No Messages "Fall Through"

If [p master] receives `/unknown/something 123`:
```
[inlet]
    ↓
[OSC-route /preamp /eq]  ← Doesn't match "/unknown"
    ↓
Second outlet (unmatched) → Could connect to error handler
                          → Or just ignore (nothing connected)
```

**Unmatched messages go to the rightmost outlet of OSC-route.**

---

## Complete Patcher Structure

### Main Patcher: `main.maxpat`

```
┌─────────────────────────────────────────┐
│  [udpreceive 7400]                      │
│       ↓                                  │
│  [OSC-route /master /channel]           │
│       ↓           ↓                      │
│  [p master]  [p channel_strip]          │
│       ↓           ↓                      │
│  [ezdac~ 1 2] [ezdac~ 3 4]              │
└─────────────────────────────────────────┘
```

### Subpatcher: `p master`

```
┌─────────────────────────────────────────┐
│  [inlet]  ← From parent                 │
│       ↓                                  │
│  [OSC-route /preamp /eq]                │
│       ↓           ↓                      │
│  [andy.gain~] [p eq]                    │
│       ↓           ↓                      │
│  [outlet~]   [outlet~]                  │
└─────────────────────────────────────────┘
```

### Subpatcher: `p eq` (inside p master)

```
┌─────────────────────────────────────────┐
│  [inlet]  ← From p master               │
│       ↓                                  │
│  [OSC-route /band1 /band2]              │
│       ↓               ↓                  │
│  [andy.filter~]  [andy.filter~]         │
│       ↓               ↓                  │
│  [outlet~]       [outlet~]              │
└─────────────────────────────────────────┘
```

---

## Message Examples

### Example 1: Master Preamp
```
iPad sends: /master/preamp/gain 0.5

Flow:
[udpreceive 7400] ← /master/preamp/gain 0.5
    ↓
[OSC-route /master] ← Strips /master, outputs /preamp/gain 0.5
    ↓
[p master] receives /preamp/gain 0.5
    ↓
[OSC-route /preamp] ← Strips /preamp, outputs /gain 0.5
    ↓
[andy.gain~] receives /gain 0.5
    ↓
(Internal routing to set gain attribute)
```

### Example 2: EQ Band 2
```
iPad sends: /master/eq/band2/q 2.5

Flow:
[udpreceive 7400] ← /master/eq/band2/q 2.5
    ↓
[OSC-route /master] ← Strips /master, outputs /eq/band2/q 2.5
    ↓
[p master] receives /eq/band2/q 2.5
    ↓
[OSC-route /preamp /eq] ← Strips /eq, outputs /band2/q 2.5
    ↓
[p eq] receives /band2/q 2.5
    ↓
[OSC-route /band1 /band2] ← Strips /band2, outputs /q 2.5
    ↓
[andy.filter~ band2] receives /q 2.5
    ↓
(Sets Q parameter)
```

### Example 3: Channel Strip
```
iPad sends: /channel/1/preamp/gain 0.8

Flow:
[udpreceive 7400] ← /channel/1/preamp/gain 0.8
    ↓
[OSC-route /master /channel] ← Strips /channel, outputs /1/preamp/gain 0.8
    ↓
[p channel_strip] receives /1/preamp/gain 0.8
    ↓
(Similar routing inside channel strip)
```

---

## Why This Works

### 1. Natural Hierarchy
- Patcher structure = OSC path structure
- Easy to visualize
- Easy to debug (can see each level)

### 2. Modularity
- Each subpatcher is independent
- Can test [p eq] standalone
- Can reuse [p channel_strip] 16 times

### 3. Explicit Routing
- Every level explicitly handles its namespace
- No ambiguity about where messages go
- Matches Max's philosophy

### 4. Scalability
```
Level 1: [OSC-route /master /channel /effects /mix]  ← 4 modules
Level 2: [OSC-route /preamp /eq /comp]               ← 3 per module
Level 3: [OSC-route /band1 /band2 /band3 /band4]     ← 4 per EQ
```

Even with deep nesting, each level only needs a few OSC-route arguments.

---

## Common Patterns

### Pattern 1: Parameter Routing at Leaf Level

Inside a module that has multiple parameters:

```
[inlet]  ← Receives: /gain 0.5
    ↓
[OSC-route /gain /pan /mute]
    ↓      ↓      ↓
[prepend gain(  [prepend pan(  [prepend mute(
    ↓              ↓              ↓
[andy.module~ receives "gain 0.5", "pan 0.3", "mute 0"]
```

### Pattern 2: Instance Routing (Multiple Copies)

For N instances of the same module:

```
[inlet]
    ↓
[OSC-route /1 /2 /3 /4]
    ↓     ↓   ↓   ↓
[p instance] [p instance] [p instance] [p instance]
```

Or using poly~:
```
[inlet]
    ↓
[prepend target]  ← Converts /1/gain to "target 1 /gain"
    ↓
[poly~ channel_strip 16]  ← Routes by instance number
```

### Pattern 3: Unmatched Handler

Catch errors at each level:

```
[inlet]
    ↓
[OSC-route /preamp /eq]
    ↓         ↓        ↓ (unmatched outlet)
  handled  handled    |
                      ↓
                [print "Unmatched in master:"]
```

---

## Debugging Tips

### 1. Add Print Objects at Each Level

```
[inlet]
    ↓
[t a a]  ← Split message
  ↓   ↓
  |   [print "master received:"]  ← Debug output
  ↓
[OSC-route /preamp /eq]
```

### 2. Test Each Level Independently

Create a test message in each patcher:
```
[message /eq/band1/gain 0.5]
    ↓
[p master]  ← Test this level without parent
```

### 3. Check Message Flow

Use Max's debug mode:
- View → Show Messages
- Click connections to see values
- Use [print] objects liberally

---

## Next Steps

### Study This Flow:

1. Read through "Message Examples" section
2. Trace each step manually
3. Note how each OSC-route strips one level
4. Understand why unhandled messages don't pass through

### When Ready:

1. I can create actual .maxpat files showing this
2. We can build a 2-level example to test
3. Then expand to your full architecture

---

## Key Takeaways

✅ **Each level strips one path component**
✅ **OSC-route does the parsing automatically**
✅ **Patcher hierarchy = OSC path hierarchy**
✅ **No messages "fall through" - explicit routing only**
✅ **Each subpatcher is self-contained**

**This is how professional Max systems handle hierarchical control.**

---

Take your time studying this. When you're ready, we can:
- Build a working example
- Add discovery/introspection
- Scale it to your full system

No rush!
