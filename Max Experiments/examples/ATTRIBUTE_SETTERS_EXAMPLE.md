# Custom Attribute Setters - Practical Example

## The Problem

When an attribute changes, you often need to do more than just store the value:
- **Filter frequency/Q** → Recalculate filter coefficients
- **Delay time** → Reallocate delay buffer
- **Oscillator frequency** → Update phase increment
- **Envelope parameters** → Recalculate segment slopes

## The Solution: Custom Setters

Use `CLASS_ATTR_ACCESSORS` to register custom getter/setter functions.

## Complete Example: Biquad Filter

```cpp
#include "ext.h"
#include "ext_obex.h"
#include "z_dsp.h"
#include <math.h>

// Object structure
typedef struct _filter {
  t_pxobject obj;

  // User-facing parameters (attributes)
  double frequency;     // Cutoff frequency (Hz)
  double q;             // Resonance/Q factor
  long filter_type;     // 0=lowpass, 1=highpass, 2=bandpass

  // Internal state (calculated from parameters)
  double coef_a0, coef_a1, coef_a2;  // Numerator coefficients
  double coef_b1, coef_b2;            // Denominator coefficients (b0 normalized to 1)

  // Filter state variables
  double x1, x2;        // Input history
  double y1, y2;        // Output history

  double sample_rate;   // Current sample rate
} t_filter;

static t_class *filter_class = NULL;

// Function prototypes
void *filter_new(t_symbol *s, long argc, t_atom *argv);
void filter_free(t_filter *x);
void filter_dsp64(t_filter *x, t_object *dsp64, short *count,
                  double samplerate, long maxvectorsize, long flags);
void filter_perform64(t_filter *x, t_object *dsp64,
                      double **ins, long numins,
                      double **outs, long numouts,
                      long sampleframes, long flags,
                      void *userparam);
void filter_assist(t_filter *x, void *b, long m, long a, char *s);

// Custom attribute setters
t_max_err filter_frequency_set(t_filter *x, void *attr, long argc, t_atom *argv);
t_max_err filter_q_set(t_filter *x, void *attr, long argc, t_atom *argv);
t_max_err filter_type_set(t_filter *x, void *attr, long argc, t_atom *argv);

// Internal helper
void filter_calculate_coefficients(t_filter *x);

// Initialization
void ext_main(void *r) {
  t_class *c;

  c = class_new("andy.filter~",
                (method)filter_new,
                (method)filter_free,
                sizeof(t_filter),
                0L,
                A_GIMME,
                0);

  class_addmethod(c, (method)filter_dsp64, "dsp64", A_CANT, 0);
  class_addmethod(c, (method)filter_assist, "assist", A_CANT, 0);

  // Register frequency attribute with custom setter
  CLASS_ATTR_DOUBLE(c, "frequency", 0, t_filter, frequency);
  CLASS_ATTR_ACCESSORS(c, "frequency", NULL, filter_frequency_set);
  CLASS_ATTR_FILTER_CLIP(c, "frequency", 20.0, 20000.0);
  CLASS_ATTR_LABEL(c, "frequency", 0, "Cutoff Frequency (Hz)");
  CLASS_ATTR_SAVE(c, "frequency", 0);
  CLASS_ATTR_DEFAULT(c, "frequency", 0, "1000.0");

  // Register Q attribute with custom setter
  CLASS_ATTR_DOUBLE(c, "q", 0, t_filter, q);
  CLASS_ATTR_ACCESSORS(c, "q", NULL, filter_q_set);
  CLASS_ATTR_FILTER_CLIP(c, "q", 0.1, 20.0);
  CLASS_ATTR_LABEL(c, "q", 0, "Resonance (Q)");
  CLASS_ATTR_SAVE(c, "q", 0);
  CLASS_ATTR_DEFAULT(c, "q", 0, "0.707");

  // Register filter type attribute with custom setter
  CLASS_ATTR_LONG(c, "type", 0, t_filter, filter_type);
  CLASS_ATTR_ACCESSORS(c, "type", NULL, filter_type_set);
  CLASS_ATTR_FILTER_CLIP(c, "type", 0, 2);
  CLASS_ATTR_LABEL(c, "type", 0, "Filter Type (0=LP, 1=HP, 2=BP)");
  CLASS_ATTR_SAVE(c, "type", 0);
  CLASS_ATTR_DEFAULT(c, "type", 0, "0");
  CLASS_ATTR_ENUM(c, "type", 0, "lowpass highpass bandpass");

  class_dspinit(c);
  class_register(CLASS_BOX, c);
  filter_class = c;

  post("andy.filter~ - biquad filter with custom attribute setters");
}

// Object creation
void *filter_new(t_symbol *s, long argc, t_atom *argv) {
  t_filter *x = (t_filter *)object_alloc(filter_class);

  if (x) {
    dsp_setup((t_pxobject *)x, 1);
    outlet_new((t_object *)x, "signal");

    // Set default values
    x->frequency = 1000.0;
    x->q = 0.707;  // Butterworth response
    x->filter_type = 0;  // Lowpass

    // Initialize filter state
    x->x1 = x->x2 = 0.0;
    x->y1 = x->y2 = 0.0;

    x->sample_rate = sys_getsr();
    if (x->sample_rate <= 0) {
      x->sample_rate = 44100.0;
    }

    // Process attribute arguments
    attr_args_process(x, argc, argv);

    // Calculate initial coefficients
    filter_calculate_coefficients(x);
  }

  return x;
}

void filter_free(t_filter *x) {
  dsp_free((t_pxobject *)x);
}

// Custom setter for frequency attribute
t_max_err filter_frequency_set(t_filter *x, void *attr, long argc, t_atom *argv) {
  if (argc && argv) {
    double freq = atom_getfloat(argv);

    // Validation (additional to FILTER_CLIP if needed)
    if (freq < 20.0) freq = 20.0;
    if (freq > x->sample_rate * 0.48) {
      freq = x->sample_rate * 0.48;  // Keep below Nyquist with margin
    }

    x->frequency = freq;

    // Recalculate filter coefficients
    filter_calculate_coefficients(x);

    object_post((t_object *)x, "Frequency set to: %.2f Hz", freq);
  }
  return MAX_ERR_NONE;
}

// Custom setter for Q attribute
t_max_err filter_q_set(t_filter *x, void *attr, long argc, t_atom *argv) {
  if (argc && argv) {
    double q_val = atom_getfloat(argv);

    // Validation
    if (q_val < 0.1) q_val = 0.1;
    if (q_val > 20.0) q_val = 20.0;

    x->q = q_val;

    // Recalculate filter coefficients
    filter_calculate_coefficients(x);

    object_post((t_object *)x, "Q set to: %.2f", q_val);
  }
  return MAX_ERR_NONE;
}

// Custom setter for filter type attribute
t_max_err filter_type_set(t_filter *x, void *attr, long argc, t_atom *argv) {
  if (argc && argv) {
    long type = atom_getlong(argv);

    if (type < 0) type = 0;
    if (type > 2) type = 2;

    x->filter_type = type;

    // Recalculate filter coefficients
    filter_calculate_coefficients(x);

    const char *type_names[] = {"lowpass", "highpass", "bandpass"};
    object_post((t_object *)x, "Filter type: %s", type_names[type]);
  }
  return MAX_ERR_NONE;
}

// Calculate biquad filter coefficients
void filter_calculate_coefficients(t_filter *x) {
  double omega = 2.0 * M_PI * x->frequency / x->sample_rate;
  double sn = sin(omega);
  double cs = cos(omega);
  double alpha = sn / (2.0 * x->q);

  double a0, a1, a2, b0, b1, b2;

  switch (x->filter_type) {
    case 0:  // Lowpass
      b0 = (1.0 - cs) / 2.0;
      b1 = 1.0 - cs;
      b2 = (1.0 - cs) / 2.0;
      a0 = 1.0 + alpha;
      a1 = -2.0 * cs;
      a2 = 1.0 - alpha;
      break;

    case 1:  // Highpass
      b0 = (1.0 + cs) / 2.0;
      b1 = -(1.0 + cs);
      b2 = (1.0 + cs) / 2.0;
      a0 = 1.0 + alpha;
      a1 = -2.0 * cs;
      a2 = 1.0 - alpha;
      break;

    case 2:  // Bandpass
      b0 = alpha;
      b1 = 0.0;
      b2 = -alpha;
      a0 = 1.0 + alpha;
      a1 = -2.0 * cs;
      a2 = 1.0 - alpha;
      break;

    default:
      b0 = 1.0;
      b1 = 0.0;
      b2 = 0.0;
      a0 = 1.0;
      a1 = 0.0;
      a2 = 0.0;
  }

  // Normalize by a0
  x->coef_a0 = b0 / a0;
  x->coef_a1 = b1 / a0;
  x->coef_a2 = b2 / a0;
  x->coef_b1 = a1 / a0;
  x->coef_b2 = a2 / a0;
}

// DSP chain setup
void filter_dsp64(t_filter *x, t_object *dsp64, short *count,
                  double samplerate, long maxvectorsize, long flags) {
  // Update sample rate if changed
  if (samplerate != x->sample_rate) {
    x->sample_rate = samplerate;
    filter_calculate_coefficients(x);  // Recalc for new sample rate
  }

  object_method(dsp64, gensym("dsp_add64"), x, filter_perform64, 0, NULL);
}

// Audio processing (biquad filter implementation)
void filter_perform64(t_filter *x, t_object *dsp64,
                      double **ins, long numins,
                      double **outs, long numouts,
                      long sampleframes, long flags,
                      void *userparam) {
  double *in = ins[0];
  double *out = outs[0];

  // Read coefficients once (thread-safe for simple reads)
  double a0 = x->coef_a0;
  double a1 = x->coef_a1;
  double a2 = x->coef_a2;
  double b1 = x->coef_b1;
  double b2 = x->coef_b2;

  // Read state
  double x1 = x->x1;
  double x2 = x->x2;
  double y1 = x->y1;
  double y2 = x->y2;

  // Process samples
  for (long i = 0; i < sampleframes; i++) {
    double input = in[i];

    // Biquad difference equation
    double output = a0 * input + a1 * x1 + a2 * x2 - b1 * y1 - b2 * y2;

    // Update state
    x2 = x1;
    x1 = input;
    y2 = y1;
    y1 = output;

    out[i] = output;
  }

  // Store state back
  x->x1 = x1;
  x->x2 = x2;
  x->y1 = y1;
  x->y2 = y2;
}

// Assist strings
void filter_assist(t_filter *x, void *b, long m, long a, char *s) {
  if (m == ASSIST_INLET) {
    snprintf(s, 256, "(signal) Audio Input");
  } else {
    snprintf(s, 256, "(signal) Filtered Output");
  }
}
```

## How It Works

### 1. Attribute Registration with Custom Setter

```cpp
// Define attribute
CLASS_ATTR_DOUBLE(c, "frequency", 0, t_filter, frequency);

// Register custom setter (NULL = use default getter)
CLASS_ATTR_ACCESSORS(c, "frequency", NULL, filter_frequency_set);
```

### 2. Custom Setter Function

```cpp
t_max_err filter_frequency_set(t_filter *x, void *attr, long argc, t_atom *argv) {
  if (argc && argv) {
    double freq = atom_getfloat(argv);

    // 1. Validate input
    if (freq < 20.0) freq = 20.0;
    if (freq > x->sample_rate * 0.48) freq = x->sample_rate * 0.48;

    // 2. Store value
    x->frequency = freq;

    // 3. Perform side effects (recalculate coefficients)
    filter_calculate_coefficients(x);

    // 4. Optional: Log the change
    object_post((t_object *)x, "Frequency set to: %.2f Hz", freq);
  }
  return MAX_ERR_NONE;
}
```

### 3. Helper Function

```cpp
void filter_calculate_coefficients(t_filter *x) {
  // Complex math using x->frequency, x->q, x->filter_type
  // Results stored in x->coef_a0, x->coef_a1, etc.
  // Called automatically whenever any parameter changes
}
```

## Usage in Max

```
[noise~]
   ↓
[andy.filter~ @frequency 2000 @q 2.0 @type lowpass]
   ↓
[dac~]

Messages:
[frequency 500(     → Triggers filter_frequency_set()
[q 5.0(             → Triggers filter_q_set()
[type 1(            → Triggers filter_type_set() (highpass)
```

## Key Points

### Setter Function Signature

```cpp
t_max_err classname_attrname_set(
  t_classname *x,      // Your object instance
  void *attr,          // Attribute object (usually ignored)
  long argc,           // Number of arguments
  t_atom *argv         // Array of argument atoms
)
```

### Pattern

1. **Extract value** from `argv`
2. **Validate** (additional to `FILTER_CLIP` if needed)
3. **Store** in struct member
4. **Perform side effects** (calculate coefficients, resize buffers, etc.)
5. **Return** `MAX_ERR_NONE`

### Thread Safety

Custom setters run on the **main thread**, so they're safe to:
- Allocate/free memory
- Recalculate coefficients
- Update complex state

The audio thread (perform function) should **read** these values, not write them.

### When to Use Custom Setters

✅ **Use custom setters when:**
- Need to recalculate derived values (filter coefficients, phase increments)
- Need to validate beyond simple clipping
- Need to allocate/resize buffers
- Need to update multiple dependent parameters
- Need to log changes for debugging

❌ **Don't need custom setters when:**
- Just storing a simple value
- No derived state to update
- Default behavior is sufficient

## Comparison

| Aspect | Default Setter | Custom Setter |
|--------|---------------|---------------|
| **Setup** | `CLASS_ATTR_DOUBLE(...)` | + `CLASS_ATTR_ACCESSORS(...)` |
| **Action** | Store value only | Store + side effects |
| **Validation** | `FILTER_CLIP` only | Custom validation |
| **Use case** | Simple parameters | Complex parameters with dependent state |

## Advanced: Custom Getter

You can also override the getter to compute values on-demand:

```cpp
t_max_err filter_frequency_get(t_filter *x, void *attr, long *argc, t_atom **argv) {
  atom_setfloat(*argv, x->frequency);
  *argc = 1;
  return MAX_ERR_NONE;
}

// Register both getter and setter
CLASS_ATTR_ACCESSORS(c, "frequency", filter_frequency_get, filter_frequency_set);
```

Useful for:
- Computing derived values (e.g., frequency in Hz from MIDI note number)
- Lazy evaluation
- Format conversion

## Summary

Custom attribute setters let you:
1. **Validate** input beyond simple clipping
2. **Update derived state** (like filter coefficients)
3. **Maintain consistency** across dependent parameters
4. **Add logging/debugging** for parameter changes

They're essential for any non-trivial DSP external where parameters affect internal state.
