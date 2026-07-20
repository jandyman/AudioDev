# Max/MSP Processing Models & Parameter Updates

**Quick Reference:**
- **Modern approach:** Use attributes for parameters (see "Attributes" section)
- **Legacy approach:** Proxy inlets (see "Legacy: Proxy Inlets" section)
- **Multichannel:** Use MC objects for variable channel counts (see "MC" section)

---

## Important: Max's String-Based Architecture

**Max uses string keys extensively throughout its API.** This is a core design pattern from 1988.

### String Keys Are Used For:
- **Method registration:** `class_addmethod(c, (method)func, "dsp64", ...)`
- **Message routing:** `"bang"`, `"float"`, `"list"`, `"anything"`
- **Attribute names:** `CLASS_ATTR_DOUBLE(c, "frequency", ...)`
- **Special methods:** `"multichanneloutputs"`, `"assist"`, `"dblclick"`

### Why Strings (not ENUMs)?
While ENUMs existed in K&R C (1978), Max chose strings for:
- **User extensibility** - Users can create custom message names
- **Dynamic behavior** - Messages can be parsed at runtime
- **No central registry** - Each external defines its own messages
- **Flexibility** - Add new methods without recompiling Max core

### The Downside:
❌ **No type safety** - Typos cause silent failures
```cpp
// WRONG - typo, no compiler error, just fails silently
class_addmethod(c, (method)func, "multichanneloutput", A_CANT, 0);
//                                                    ^ missing 's'

// CORRECT
class_addmethod(c, (method)func, "multichanneloutputs", A_CANT, 0);
//                                                     ^ must be exact
```

❌ **No autocomplete** - Must memorize or look up exact strings
❌ **Runtime-only errors** - Mistakes found during execution, not compilation

### Best Practice:
**Always copy/paste string keys from working examples or documentation.** Don't type from memory.

Common magic strings you'll use:
- `"dsp64"` - Required for audio processing
- `"multichanneloutputs"` - Required for MC support
- `"assist"` - Provide inlet/outlet help text
- `"bang"`, `"float"`, `"int"`, `"list"` - Handle message types

---

## The Two Processing Domains

Max objects operate in one or both of two distinct processing domains:

### 1. Control-Rate (Event-Based) Processing

**Used by:** Non-audio objects (number boxes, message boxes, counters, etc.)

**Characteristics:**
- Asynchronous - triggered by events (user input, messages from other objects)
- Processes one value at a time
- No fixed timing - happens when messages arrive
- Lower CPU overhead
- Examples: `[metro]`, `[counter]`, `[+ 5]`

**Message Flow:**
```
[number box] → sends "float" message → [+ 10] → processes immediately → output
     ↓
 User clicks
```

### 2. Signal-Rate (Block-Based) Processing

**Used by:** Audio objects (those with ~ suffix)

**Characteristics:**
- Synchronous with audio clock
- Processes blocks of samples continuously
- Fixed timing based on sample rate and vector size
- Default: 64 samples/block at 44.1kHz = ~1.45ms per block
- Higher CPU overhead (always running when audio is on)
- Examples: `[cycle~]`, `[+~]`, `[andy.gain~]`

**Processing Flow:**
```
Audio On → DSP Chain Setup → Continuous block processing
                                    ↓
                         [64 samples] → process → output → repeat
```

### Audio Objects: Hybrid Processing

**Audio objects can handle BOTH control-rate and signal-rate processing!**

This is what makes them powerful - they can:
1. Process audio blocks continuously (signal-rate)
2. Respond to control messages (control-rate)

**Example flow:**
```
     Control-Rate Input              Signal-Rate Input
            ↓                                ↓
    [flonum] → "float" msg         [noise~] → audio blocks
            ↓                                ↓
       obj_float()                  inlet 0 (signal inlet)
            ↓                                ↓
    sets param_value ←───────── reads param_value
                                       ↓
                                 obj_perform64()
                                       ↓
                               [64 samples processed]
                                       ↓
                                  Audio output
```

**Thread Safety Note:**
- Control functions run on main thread
- Perform functions run on audio thread (real-time critical)
- Simple atomic types (single `double`) are usually safe
- Complex state needs synchronization (attributes handle this automatically)

### Block Size & Timing

**Vector size (block size):** Set in Max's Audio Status window
- Default: 64 samples
- Options: 32, 64, 128, 256, 512, 1024, 2048 samples
- Smaller = lower latency, higher CPU usage
- Larger = higher latency, lower CPU usage

**At 44.1kHz:**
- 64 samples = 1.45ms latency
- 512 samples = 11.6ms latency

**Control vs Signal Latency:**
- Control messages: Near-instant (microseconds)
- Signal processing: Delayed by current block size
- This is why parameter updates feel immediate even though audio processing is block-based!

---

## Basic Parameter Updates

Before diving into multiple parameters, let's understand how a single parameter works.

### Simple Message Handler

```cpp
typedef struct _gain {
  t_pxobject obj;
  double gain_value;
} t_gain;

// Register the handler
void ext_main(void *r) {
  // ... class setup ...
  class_addmethod(c, (method)gain_float, "float", A_FLOAT, 0);
  // ...
}

// Handle incoming float messages
void gain_float(t_gain *x, double f) {
  x->gain_value = f;
  object_post((t_object *)x, "gain set to: %f", f);
}

// Read parameter in perform function
void gain_perform64(t_gain *x, t_object *dsp64,
                    double **ins, long numins,
                    double **outs, long numouts,
                    long sampleframes, long flags,
                    void *userparam) {
  double *in = ins[0];
  double *out = outs[0];
  double gain = x->gain_value;  // Read current value

  long n = sampleframes;
  while (n--) {
    *out++ = *in++ * gain;
  }
}
```

### Naming Convention: `classname_messagetype`

The function `gain_float` follows Max's convention:
- **Not describing what it does** (set gain)
- **Describing what message it handles** (float messages)

When you register:
```cpp
class_addmethod(c, (method)gain_float, "float", A_FLOAT, 0);
```

Max routes all "float" messages to this handler.

**Other common message types:**
- `obj_int` - handles "int" messages
- `obj_bang` - handles "bang" messages
- `obj_list` - handles "list" messages
- `obj_anything` - catch-all handler

---

## Modern Approach: Attributes (RECOMMENDED)

**Attributes are the recommended way to handle parameters in modern Max externals.**

### Why Use Attributes?

**Advantages:**
- ✅ Thread-safe (Max handles synchronization)
- ✅ No manual memory management
- ✅ Automatable in Max (for live recording)
- ✅ Saveable with patcher
- ✅ Inspector integration (appears in object inspector)
- ✅ Message interface: `[gain 0.5(` or `[setgain 0.5(`
- ✅ Query current value: `[getgain(`
- ✅ Supports all data types (float, int, symbol, color, etc.)

**Disadvantages:**
- Slightly more complex setup
- Less direct than simple message handlers

### Complete Attribute Example

Here's a complete audio object with two parameters using attributes:

```cpp
#include "ext.h"
#include "ext_obex.h"
#include "z_dsp.h"

// Object structure
typedef struct _attrgain {
  t_pxobject obj;

  // Parameters (attributes will reference these)
  double gain;        // Linear gain value
  double pan;         // Pan position (0.0 = left, 1.0 = right)
} t_attrgain;

// Global class pointer
static t_class *attrgain_class = NULL;

// Function prototypes
void *attrgain_new(t_symbol *s, long argc, t_atom *argv);
void attrgain_free(t_attrgain *x);
void attrgain_dsp64(t_attrgain *x, t_object *dsp64, short *count,
                    double samplerate, long maxvectorsize, long flags);
void attrgain_perform64(t_attrgain *x, t_object *dsp64,
                        double **ins, long numins,
                        double **outs, long numouts,
                        long sampleframes, long flags,
                        void *userparam);
void attrgain_assist(t_attrgain *x, void *b, long m, long a, char *s);

// Initialization
void ext_main(void *r) {
  t_class *c;

  c = class_new("andy.attrgain~",
                (method)attrgain_new,
                (method)attrgain_free,
                sizeof(t_attrgain),
                0L,
                A_GIMME,
                0);

  class_addmethod(c, (method)attrgain_dsp64, "dsp64", A_CANT, 0);
  class_addmethod(c, (method)attrgain_assist, "assist", A_CANT, 0);

  // Register attributes
  CLASS_ATTR_DOUBLE(c, "gain", 0, t_attrgain, gain);
  CLASS_ATTR_FILTER_CLIP(c, "gain", 0.0, 10.0);  // Limit range
  CLASS_ATTR_LABEL(c, "gain", 0, "Gain");
  CLASS_ATTR_SAVE(c, "gain", 0);  // Save with patcher

  CLASS_ATTR_DOUBLE(c, "pan", 0, t_attrgain, pan);
  CLASS_ATTR_FILTER_CLIP(c, "pan", 0.0, 1.0);  // 0.0 to 1.0
  CLASS_ATTR_LABEL(c, "pan", 0, "Pan Position");
  CLASS_ATTR_SAVE(c, "pan", 0);

  class_dspinit(c);
  class_register(CLASS_BOX, c);
  attrgain_class = c;

  post("andy.attrgain~ - gain with attributes");
}

// Object creation
void *attrgain_new(t_symbol *s, long argc, t_atom *argv) {
  t_attrgain *x = (t_attrgain *)object_alloc(attrgain_class);

  if (x) {
    dsp_setup((t_pxobject *)x, 1);  // One signal inlet
    outlet_new((t_object *)x, "signal");  // Stereo left
    outlet_new((t_object *)x, "signal");  // Stereo right

    // Set default values
    x->gain = 1.0;
    x->pan = 0.5;  // Center

    // Process attributes from creation arguments
    attr_args_process(x, argc, argv);
  }

  return x;
}

void attrgain_free(t_attrgain *x) {
  dsp_free((t_pxobject *)x);
}

// DSP chain setup
void attrgain_dsp64(t_attrgain *x, t_object *dsp64, short *count,
                    double samplerate, long maxvectorsize, long flags) {
  object_method(dsp64, gensym("dsp_add64"), x, attrgain_perform64, 0, NULL);
}

// Audio processing
void attrgain_perform64(t_attrgain *x, t_object *dsp64,
                        double **ins, long numins,
                        double **outs, long numouts,
                        long sampleframes, long flags,
                        void *userparam) {
  double *in = ins[0];
  double *out_left = outs[0];
  double *out_right = outs[1];

  // Read attributes (thread-safe)
  double gain = x->gain;
  double pan = x->pan;

  // Calculate left/right gains from pan
  double left_gain = gain * (1.0 - pan);
  double right_gain = gain * pan;

  for (long i = 0; i < sampleframes; i++) {
    double sample = in[i];
    out_left[i] = sample * left_gain;
    out_right[i] = sample * right_gain;
  }
}

// Assist strings
void attrgain_assist(t_attrgain *x, void *b, long m, long a, char *s) {
  if (m == ASSIST_INLET) {
    snprintf(s, 256, "(signal) Audio Input");
  } else if (a == 0) {
    snprintf(s, 256, "(signal) Left Output");
  } else {
    snprintf(s, 256, "(signal) Right Output");
  }
}
```

### Using Attributes in Max

**Setting attributes:**
```
[gain 0.5(          → Set gain to 0.5
[pan 1.0(           → Set pan to full right
[gain 2.0 pan 0.3(  → Set multiple attributes
```

**Getting attribute values:**
```
[getgain(           → Outputs current gain value
[getpan(            → Outputs current pan value
```

**Creation arguments with attributes:**
```
[andy.attrgain~ @gain 0.5 @pan 0.75]
```

**Inspector integration:**
- Attributes automatically appear in Max's Inspector panel
- `CLASS_ATTR_LABEL` sets the display name
- `CLASS_ATTR_FILTER_CLIP` adds range limiting
- `CLASS_ATTR_SAVE` makes it save with the patcher

### Attribute Macros Reference

**Basic types:**
```cpp
CLASS_ATTR_DOUBLE(c, "name", 0, t_obj, member);      // double
CLASS_ATTR_LONG(c, "name", 0, t_obj, member);        // long int
CLASS_ATTR_FLOAT(c, "name", 0, t_obj, member);       // float
CLASS_ATTR_CHAR(c, "name", 0, t_obj, member);        // char
CLASS_ATTR_SYM(c, "name", 0, t_obj, member);         // t_symbol*
CLASS_ATTR_ATOM(c, "name", 0, t_obj, member);        // t_atom
```

**Array types:**
```cpp
CLASS_ATTR_DOUBLE_ARRAY(c, "name", 0, t_obj, member, size);
CLASS_ATTR_LONG_ARRAY(c, "name", 0, t_obj, member, size);
```

**Common modifiers:**
```cpp
CLASS_ATTR_LABEL(c, "name", 0, "Display Name");
CLASS_ATTR_SAVE(c, "name", 0);                       // Save with patcher
CLASS_ATTR_FILTER_CLIP(c, "name", min, max);         // Limit range
CLASS_ATTR_DEFAULT(c, "name", 0, "1.0");             // Default value
CLASS_ATTR_ORDER(c, "name", 0, "1");                 // Inspector order
CLASS_ATTR_STYLE_LABEL(c, "name", 0, "text");        // Style hint
CLASS_ATTR_CATEGORY(c, "name", 0, "Behavior");       // Category in inspector
```

### Custom Attribute Getters/Setters

For validation or side effects:

```cpp
typedef struct _customattr {
  t_pxobject obj;
  double frequency;
  double q_factor;

  // Internal state that needs updating when params change
  double coef_a0, coef_a1, coef_a2;
  double coef_b0, coef_b1, coef_b2;
} t_customattr;

// Custom setter with validation and coefficient update
t_max_err customattr_frequency_set(t_customattr *x, void *attr,
                                    long argc, t_atom *argv) {
  if (argc && argv) {
    double freq = atom_getfloat(argv);

    // Validation
    if (freq < 20.0) freq = 20.0;
    if (freq > 20000.0) freq = 20000.0;

    x->frequency = freq;

    // Recalculate filter coefficients
    calculate_filter_coefficients(x);

    object_post((t_object *)x, "Frequency set to: %f Hz", freq);
  }
  return MAX_ERR_NONE;
}

// Registration with custom setter
void ext_main(void *r) {
  // ... class setup ...

  CLASS_ATTR_DOUBLE(c, "frequency", 0, t_customattr, frequency);
  CLASS_ATTR_ACCESSORS(c, "frequency", NULL, customattr_frequency_set);
  CLASS_ATTR_LABEL(c, "frequency", 0, "Filter Frequency");

  // ...
}
```

---

## Alternative: Named Message Handlers

If you don't need all the features of attributes, named message handlers are simpler:

```cpp
typedef struct _namedparams {
  t_pxobject obj;
  double gain;
  double pan;
} t_namedparams;

// Register handlers for specific message names
void ext_main(void *r) {
  // ... class setup ...

  class_addmethod(c, (method)namedparams_gain, "gain", A_FLOAT, 0);
  class_addmethod(c, (method)namedparams_pan, "pan", A_FLOAT, 0);

  // ...
}

// Handler for "gain" message
void namedparams_gain(t_namedparams *x, double f) {
  x->gain = CLAMP(f, 0.0, 10.0);
  object_post((t_object *)x, "Gain: %f", x->gain);
}

// Handler for "pan" message
void namedparams_pan(t_namedparams *x, double f) {
  x->pan = CLAMP(f, 0.0, 1.0);
  object_post((t_object *)x, "Pan: %f", x->pan);
}
```

**Usage in Max:**
```
[gain 0.5(  → calls namedparams_gain()
[pan 0.75(  → calls namedparams_pan()
```

**Advantages over attributes:**
- Simpler setup
- Direct control
- Less overhead

**Disadvantages vs. attributes:**
- Not automatable
- Not saveable with patcher
- No inspector integration
- Manual thread safety

---

## Legacy Approach: Proxy Inlets

**Historical Context:** Max was designed for 68k Macintosh in 1988. The proxy inlet system was the original way to handle multiple parameters via separate inlets. It persists for backward compatibility.

### Why This Design Is Messy

**Problems with proxy inlets:**
- Global state (`x->inlet`) gets overwritten on each message
- Not thread-safe by design
- Requires manual memory management (create/free proxies)
- Confusing creation order (right-to-left)
- Single message handler must dispatch to all parameters

**When you might still need proxies:**
- Maintaining compatibility with old Max patches
- Users expect traditional inlet-based control flow
- Creating Max-style objects that match built-in behavior

### Proxy Inlet Example

```cpp
typedef struct _proxyexample {
  t_pxobject obj;
  void *proxy;          // Proxy inlet object
  long inlet;           // Current inlet number (written by Max)

  double gain;
  double pan;
} t_proxyexample;

void *proxyexample_new(void) {
  t_proxyexample *x = (t_proxyexample *)object_alloc(proxyexample_class);

  if (x) {
    dsp_setup((t_pxobject *)x, 1);  // Signal inlet (inlet 0)

    // Create proxy for second parameter (inlet 1)
    // Note: Right-to-left creation order for multiple proxies
    x->proxy = proxy_new((t_object *)x, 1, &x->inlet);

    outlet_new((t_object *)x, "signal");

    x->gain = 1.0;
    x->pan = 0.5;
  }

  return x;
}

void proxyexample_float(t_proxyexample *x, double f) {
  long inlet = proxy_getinlet((t_object *)x);

  switch (inlet) {
    case 0:  // Main inlet - gain
      x->gain = f;
      object_post((t_object *)x, "Gain: %f", x->gain);
      break;

    case 1:  // Proxy inlet - pan
      x->pan = CLAMP(f, 0.0, 1.0);
      object_post((t_object *)x, "Pan: %f", x->pan);
      break;
  }
}

void proxyexample_free(t_proxyexample *x) {
  dsp_free((t_pxobject *)x);
  object_free(x->proxy);  // Free the proxy!
}
```

**Usage:**
```
[0.5]──────→ [proxyexample~] → audio out
           ↗
[0.75]────┘
  ↑         ↑
Inlet 1   Inlet 0
  Pan      Gain
```

### Multiple Proxy Inlets

For objects with many parameters:

```cpp
typedef struct _multiproxy {
  t_pxobject obj;
  void *proxies[3];  // 3 additional inlets (inlets 1, 2, 3)
  long inlet;

  double params[4];  // params[0-3] for inlets 0-3
} t_multiproxy;

void *multiproxy_new(void) {
  t_multiproxy *x = (t_multiproxy *)object_alloc(multiproxy_class);

  if (x) {
    dsp_setup((t_pxobject *)x, 1);  // Inlet 0

    // Create proxies RIGHT TO LEFT
    x->proxies[2] = proxy_new((t_object *)x, 3, &x->inlet);  // Inlet 3
    x->proxies[1] = proxy_new((t_object *)x, 2, &x->inlet);  // Inlet 2
    x->proxies[0] = proxy_new((t_object *)x, 1, &x->inlet);  // Inlet 1

    outlet_new((t_object *)x, "signal");

    // Initialize parameters
    for (int i = 0; i < 4; i++) {
      x->params[i] = 0.0;
    }
  }

  return x;
}

void multiproxy_float(t_multiproxy *x, double f) {
  long inlet = proxy_getinlet((t_object *)x);

  if (inlet >= 0 && inlet < 4) {
    x->params[inlet] = f;
    object_post((t_object *)x, "Inlet %d: %f", inlet, f);
  }
}

void multiproxy_free(t_multiproxy *x) {
  dsp_free((t_pxobject *)x);

  // Free all proxies
  for (int i = 0; i < 3; i++) {
    object_free(x->proxies[i]);
  }
}
```

### Key Points About Proxies

1. **Creation order:** Right-to-left (highest inlet number first)
2. **Outlet creation order:** Also right-to-left
3. **Always check inlet:** Use `proxy_getinlet()` in message handlers
4. **Free proxies:** Call `object_free()` on each proxy in destructor
5. **Inlet 0 is real:** Only the leftmost inlet is the actual object
6. **Global state:** `x->inlet` is overwritten on every message

### Debugging Proxies

```cpp
void obj_float(t_obj *x, double f) {
  long inlet = proxy_getinlet((t_object *)x);
  object_post((t_object *)x, "Received %f at inlet %d", f, inlet);

  // Your parameter routing...
}
```

---

## Multiple Signal Inlets

For objects that need multiple audio inputs (not parameters):

```cpp
typedef struct _mixer {
  t_pxobject obj;
} t_mixer;

void *mixer_new(void) {
  t_mixer *x = (t_mixer *)object_alloc(mixer_class);

  if (x) {
    // Create 4 signal inlets
    dsp_setup((t_pxobject *)x, 4);
    outlet_new((t_object *)x, "signal");
  }

  return x;
}

void mixer_perform64(t_mixer *x, t_object *dsp64,
                     double **ins, long numins,
                     double **outs, long numouts,
                     long sampleframes, long flags,
                     void *userparam) {
  // Access each signal inlet
  double *in0 = ins[0];  // Inlet 0
  double *in1 = ins[1];  // Inlet 1
  double *in2 = ins[2];  // Inlet 2
  double *in3 = ins[3];  // Inlet 3
  double *out = outs[0];

  for (long i = 0; i < sampleframes; i++) {
    out[i] = (in0[i] + in1[i] + in2[i] + in3[i]) * 0.25;
  }
}
```

**Key points:**
- `dsp_setup(x, n)` creates `n` signal inlets
- `ins` array in `perform64()` gives access to each inlet's audio
- `numins` tells you how many are actually connected
- No proxies needed - this is built into MSP

---

## Multichannel Audio (MC)

**Since Max 8 (2018)**, Max supports multichannel signals on a single inlet/outlet.

### The Problem MC Solves

**Old approach:** One channel per inlet/outlet
```
[noise~]────┐
            ├→ [stereo~] ─┬→ Left out
[cycle~]────┘             └→ Right out

Problem: 8-channel surround = 8 cables (messy!)
```

**MC approach:** Multiple channels on one inlet/outlet
```
[mc.noise~ 8]──→ [mc.gain~] ──→ [mc.dac~]

Solution: 1 cable for 8 channels (or 64, or 256...)
```

### Creating MC-Capable Externals

MC externals process multiple channels in a single instance:

```cpp
typedef struct _mcgain {
  t_pxobject obj;
  double gain;
} t_mcgain;

void ext_main(void *r) {
  t_class *c;

  c = class_new("mc.gain~",
                (method)mcgain_new,
                (method)mcgain_free,
                sizeof(t_mcgain),
                0L,
                A_GIMME,
                0);

  class_addmethod(c, (method)mcgain_dsp64, "dsp64", A_CANT, 0);

  // KEY: Register as multichannel-capable
  class_addmethod(c, (method)mcgain_multichanneloutputs,
                  "multichanneloutputs", A_CANT, 0);

  class_dspinit(c);
  class_register(CLASS_BOX, c);
  mcgain_class = c;
}

// Declare output channel behavior
void mcgain_multichanneloutputs(t_mcgain *x, long outletindex, long *channelcount) {
  if (outletindex == 0) {
    *channelcount = 0;  // 0 = match input channel count
  }
}

// Process all channels
void mcgain_perform64(t_mcgain *x, t_object *dsp64,
                      double **ins, long numins,
                      double **outs, long numouts,
                      long sampleframes, long flags,
                      void *userparam) {
  double gain = x->gain;

  // Loop over channels
  for (long ch = 0; ch < numins && ch < numouts; ch++) {
    double *in = ins[ch];
    double *out = outs[ch];

    // Process this channel
    for (long i = 0; i < sampleframes; i++) {
      out[i] = in[i] * gain;
    }
  }
}
```

### MC Channel Count Behaviors

**In `multichanneloutputs` callback:**
```cpp
*channelcount = 0;   // Match input channel count (pass-through)
*channelcount = 2;   // Always output 2 channels (mono→stereo)
*channelcount = N;   // Always output N channels
```

### MC Example: Stereo Spreader

Always outputs stereo regardless of input channel count:

```cpp
typedef struct _spreader {
  t_pxobject obj;
} t_spreader;

void spreader_multichanneloutputs(t_spreader *x, long outletindex, long *channelcount) {
  *channelcount = 2;  // Always stereo output
}

void spreader_perform64(t_spreader *x, t_object *dsp64,
                        double **ins, long numins,
                        double **outs, long numouts,
                        long sampleframes, long flags,
                        void *userparam) {
  double *out_left = outs[0];
  double *out_right = outs[1];

  // Sum all input channels, spread to stereo
  for (long i = 0; i < sampleframes; i++) {
    double sum = 0.0;
    for (long ch = 0; ch < numins; ch++) {
      sum += ins[ch][i];
    }
    sum /= numins;  // Average

    out_left[i] = sum;
    out_right[i] = sum;
  }
}
```

### MC Example: Per-Channel Parameters

```cpp
typedef struct _mcgains {
  t_pxobject obj;
  double *gains;      // Array of per-channel gains
  long max_channels;
} t_mcgains;

void *mcgains_new(long max_channels) {
  t_mcgains *x = (t_mcgains *)object_alloc(mcgains_class);

  if (x) {
    dsp_setup((t_pxobject *)x, 1);
    outlet_new((t_object *)x, "signal");

    x->max_channels = max_channels ? max_channels : 32;
    x->gains = (double *)sysmem_newptr(x->max_channels * sizeof(double));

    // Initialize all gains
    for (long i = 0; i < x->max_channels; i++) {
      x->gains[i] = 1.0;
    }
  }

  return x;
}

// Accept list of per-channel gains
void mcgains_list(t_mcgains *x, t_symbol *s, long argc, t_atom *argv) {
  long num = MIN(argc, x->max_channels);

  for (long i = 0; i < num; i++) {
    x->gains[i] = atom_getfloat(argv + i);
  }
}

void mcgains_perform64(t_mcgains *x, t_object *dsp64,
                       double **ins, long numins,
                       double **outs, long numouts,
                       long sampleframes, long flags,
                       void *userparam) {
  // Apply per-channel gain
  for (long ch = 0; ch < numins && ch < numouts; ch++) {
    double *in = ins[ch];
    double *out = outs[ch];
    double gain = x->gains[ch];

    for (long i = 0; i < sampleframes; i++) {
      out[i] = in[i] * gain;
    }
  }
}

void mcgains_free(t_mcgains *x) {
  dsp_free((t_pxobject *)x);
  if (x->gains) {
    sysmem_freeptr(x->gains);
  }
}
```

**Usage:**
```
[mc.noise~ 4]
     ↓
[1.0 0.5 0.75 0.25(  ← list of per-channel gains
     ↓
[mc.gains~ 4]
     ↓
[mc.dac~]
```

### MC Advantages

**1. Cleaner patchers:**
- 1 cable for 64 channels vs. 64 cables

**2. Dynamic channel counts:**
```
[mc.noise~ 2]   → stereo
[mc.noise~ 8]   → 7.1 surround
[mc.noise~ 64]  → ambisonics
```

**3. Automatic wrapping:**
- Max wraps non-MC objects to work in MC chains

**4. More efficient:**
- Single instance vs. multiple wrapped instances

### MC Performance Tips

**Efficient (good cache locality):**
```cpp
// Process channels in outer loop, samples in inner loop
for (long ch = 0; ch < numins; ch++) {
  double *in = ins[ch];
  double *out = outs[ch];
  for (long i = 0; i < sampleframes; i++) {
    out[i] = process(in[i]);
  }
}
```

**Less efficient (poor cache locality):**
```cpp
// Sample in outer loop, channels in inner loop
for (long i = 0; i < sampleframes; i++) {
  for (long ch = 0; ch < numins; ch++) {
    outs[ch][i] = process(ins[ch][i]);
  }
}
```

### MC Wrapper Behavior

Max automatically wraps regular MSP objects:
```
[mc.noise~ 4] → [gain~ 2.0] → [mc.dac~]
                     ↑
              Max creates 4 instances of gain~
```

**Implication:** Regular externals work in MC patches, but native MC implementations are more efficient.

---

## Comparison Table

| Feature | Attributes | Named Messages | Proxy Inlets | MC |
|---------|-----------|----------------|--------------|-----|
| **Thread-safe** | ✅ Yes | ⚠️ Manual | ⚠️ Manual | N/A (audio) |
| **Automatable** | ✅ Yes | ❌ No | ❌ No | N/A |
| **Saveable** | ✅ Yes | ❌ No | ❌ No | N/A |
| **Inspector** | ✅ Yes | ❌ No | ❌ No | N/A |
| **Setup complexity** | Medium | Low | High | Medium |
| **Memory mgmt** | Auto | Auto | Manual | Manual |
| **Use case** | Parameters | Simple params | Legacy/Inlets | Multi-channel |
| **Recommended** | ✅ Yes | ⚠️ Sometimes | ❌ Legacy only | ✅ For MC |

---

## Best Practices

### For New Externals:

1. **Use attributes for parameters** - Thread-safe, automatable, saveable
2. **Consider MC if channel count varies** - Cleaner, more flexible
3. **Avoid proxy inlets** - Unless maintaining legacy behavior
4. **Keep control handlers fast** - They run on main thread
5. **Keep perform functions faster** - They run on audio thread (real-time critical)
6. **Test with various configurations:**
   - 1, 2, 8, and 64 channels (for MC)
   - Different block sizes (32, 64, 512 samples)
   - High CPU load scenarios

### Performance Guidelines:

- **Avoid locks in perform** - Use lock-free techniques
- **Read parameters once per block** - Don't read repeatedly in inner loops
- **Use SIMD when possible** - vDSP, Accelerate framework
- **Profile with Instruments** - Optimize hot paths

### Debugging Tips:

```cpp
// Log parameter updates
void obj_float(t_obj *x, double f) {
  object_post((t_object *)x, "Received: %f", f);
  // ...
}

// Log DSP setup
void obj_dsp64(t_obj *x, t_object *dsp64, short *count,
               double samplerate, long maxvectorsize, long flags) {
  object_post((t_object *)x, "SR: %f, Vector: %d", samplerate, maxvectorsize);
  // ...
}
```

---

## Summary

### The Modern Way (Recommended)

```cpp
// Attributes for parameters
CLASS_ATTR_DOUBLE(c, "gain", 0, t_obj, gain);
CLASS_ATTR_SAVE(c, "gain", 0);

// MC for variable channel counts
class_addmethod(c, (method)obj_multichanneloutputs,
                "multichanneloutputs", A_CANT, 0);
```

### When to Use What

- **Simple mono/stereo, few parameters** → Basic object with attributes
- **Variable channel counts** → MC object with attributes
- **Legacy compatibility** → Proxy inlets (reluctantly)
- **Very simple controls** → Named message handlers

**Bottom line:** Attributes + MC = modern, clean, powerful Max externals.
