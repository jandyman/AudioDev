# Max/MSP External Development - Quick Reference

## Create New External (3 steps)

```bash
# 1. Copy template
cp -r andy.gain_tilde andy.yourmodule_tilde && cd andy.yourmodule_tilde

# 2. Edit CMakeLists.txt (change project name)
# 3. Edit yourmodule_tilde.cpp (implement DSP)
```

## Build & Test

```bash
rm -rf build && mkdir build && cd build
cmake -G Xcode ..
xcodebuild -configuration Debug
lipo -info externals/andy.yourmodule~.mxo/Contents/MacOS/andy.yourmodule~
# Must show: x86_64 arm64
```

**Remember:** Restart Max after every rebuild!

## Attribute Pattern (Simple)

```cpp
// In ext_main():
CLASS_ATTR_DOUBLE(c, "gain", 0, t_obj, gain);
CLASS_ATTR_FILTER_CLIP(c, "gain", 0.0, 10.0);
CLASS_ATTR_LABEL(c, "gain", 0, "Gain");
CLASS_ATTR_SAVE(c, "gain", 0);
CLASS_ATTR_DEFAULT(c, "gain", 0, "1.0");

// In yourmodule_new():
attr_args_process(x, argc, argv);

// In perform64():
double gain = x->gain;  // Just read it
```

## Attribute Pattern (Custom Setter)

```cpp
// In ext_main():
CLASS_ATTR_DOUBLE(c, "frequency", 0, t_obj, frequency);
CLASS_ATTR_ACCESSORS(c, "frequency", NULL, obj_frequency_set);
CLASS_ATTR_FILTER_CLIP(c, "frequency", 20.0, 20000.0);
CLASS_ATTR_SAVE(c, "frequency", 0);

// Implement setter:
t_max_err obj_frequency_set(t_obj *x, void *attr, long argc, t_atom *argv) {
  if (argc && argv) {
    x->frequency = atom_getfloat(argv);
    obj_calculate_coefficients(x);  // Recalculate derived state
  }
  return MAX_ERR_NONE;
}
```

## Attribute Types

```cpp
CLASS_ATTR_DOUBLE(c, "name", 0, t_obj, member);  // double
CLASS_ATTR_FLOAT(c, "name", 0, t_obj, member);   // float
CLASS_ATTR_LONG(c, "name", 0, t_obj, member);    // long
CLASS_ATTR_CHAR(c, "name", 0, t_obj, member);    // char
CLASS_ATTR_SYM(c, "name", 0, t_obj, member);     // t_symbol*
```

## Attribute Modifiers

```cpp
CLASS_ATTR_FILTER_CLIP(c, "name", min, max);     // Limit range
CLASS_ATTR_LABEL(c, "name", 0, "Display Name");  // Inspector label
CLASS_ATTR_SAVE(c, "name", 0);                   // Save with patcher
CLASS_ATTR_DEFAULT(c, "name", 0, "1.0");         // Default value
CLASS_ATTR_ENUM(c, "name", 0, "opt1 opt2 opt3"); // Enum values
CLASS_ATTR_CATEGORY(c, "name", 0, "Behavior");   // Inspector category
```

## Object Structure Template

```cpp
typedef struct _obj {
  t_pxobject obj;

  // Parameters (attributes)
  double frequency;
  double q;
  long mode;

  // Derived state (calculated from parameters)
  double coef_a0, coef_a1, coef_a2;
  double coef_b1, coef_b2;

  // DSP state (history)
  double x1, x2, y1, y2;

  double sample_rate;
} t_obj;
```

## Calculate Derived State Pattern

```cpp
void obj_calculate_coefficients(t_obj *x) {
  // Use x->frequency, x->q, x->mode
  // Calculate coefficients, phase increments, etc.
  // Store in x->coef_a0, x->coef_a1, etc.
}

// Call this:
// 1. After object creation
// 2. In every custom setter
// 3. When sample rate changes
```

## DSP Setup with Sample Rate Check

```cpp
void obj_dsp64(t_obj *x, t_object *dsp64, short *count,
               double samplerate, long maxvectorsize, long flags) {
  if (samplerate != x->sample_rate) {
    x->sample_rate = samplerate;
    obj_calculate_coefficients(x);  // Recalc for new SR
  }
  object_method(dsp64, gensym("dsp_add64"), x, obj_perform64, 0, NULL);
}
```

## Perform Function Pattern

```cpp
void obj_perform64(t_obj *x, t_object *dsp64,
                   double **ins, long numins,
                   double **outs, long numouts,
                   long sampleframes, long flags,
                   void *userparam) {
  double *in = ins[0];
  double *out = outs[0];

  // Read parameters/coefficients ONCE
  double coef = x->coef_a0;
  double state = x->y1;

  // Process block
  for (long i = 0; i < sampleframes; i++) {
    double input = in[i];
    double output = input * coef + state;  // Your DSP here
    state = output;
    out[i] = output;
  }

  // Store state back
  x->y1 = state;
}
```

## Common Patterns

### Frequency → Phase Increment
```cpp
x->phase_increment = 2.0 * M_PI * x->frequency / x->sample_rate;
```

### Milliseconds → Samples
```cpp
x->delay_samples = (long)(x->delay_ms * x->sample_rate / 1000.0);
```

### dB → Linear
```cpp
x->gain_linear = pow(10.0, x->gain_db / 20.0);
```

### Clamp/Wrap
```cpp
// Clamp
if (value < min) value = min;
if (value > max) value = max;

// Wrap
while (phase >= 2.0 * M_PI) phase -= 2.0 * M_PI;
```

## Usage in Max

```
[andy.yourmodule~ @param1 0.5 @param2 1000]  ← Create with attributes

[param1 0.75(    → Set parameter
[getparam1(      → Get current value
Cmd+I            → Open Inspector for visual control
```

## Memory Management

```cpp
// Allocate
x->buffer = (double *)sysmem_newptrclear(size * sizeof(double));

// Free (in yourmodule_free)
if (x->buffer) {
  sysmem_freeptr(x->buffer);
}
```

## Debug Logging

```cpp
object_post((t_object *)x, "Debug: value = %f", value);  // To Max console
post("Global message");  // To Max console (no object)
```

## Thread Safety

✅ **Safe (atomic on modern CPUs):**
- Reading single `double`, `float`, `long`, `int`
- Writing from one thread, reading from another

⚠️ **Not safe (needs synchronization):**
- Complex structures
- Multiple dependent values
- Pointers being reallocated

**Solution:** Use custom setters (main thread) to prepare state, perform function (audio thread) just reads.

## File Locations

```
.claude/
├── CLAUDE.md                        ← Main instructions (read first)
├── DSP_EXTERNAL_TEMPLATE.md         ← Copy/paste template
├── MAX_PROCESSING_MODELS.md         ← Deep dive on Max architecture
├── ATTRIBUTE_SETTERS_EXAMPLE.md     ← Biquad filter example
└── QUICK_REFERENCE.md               ← This file

andy.gain_tilde/
├── gain_tilde.cpp                   ← Simple attribute example
└── CMakeLists.txt                   ← Build config (copy this)

objects/
└── andy.gain~.mxo                   ← Built external (shared location)
```

## Checklist for New External

- [ ] Copy template folder
- [ ] Update CMakeLists.txt (project name)
- [ ] Define object structure
- [ ] Register attributes in ext_main()
- [ ] Implement custom setters (if needed)
- [ ] Write calculate_coefficients() helper
- [ ] Implement perform64() DSP
- [ ] Test: build, verify universal binary
- [ ] Test: restart Max, create object
- [ ] Test: attribute control (messages + inspector)
- [ ] Test: save/load patcher
- [ ] Test: audio processing
- [ ] Document in PROJECT_OVERVIEW.md

## Build Errors

**"Undefined symbols"** → Missing Max SDK include path in CMakeLists.txt
**"Architecture mismatch"** → Set `CMAKE_OSX_ARCHITECTURES "x86_64;arm64"`
**"Object won't load"** → Restart Max (aggressive caching)
**"Attribute not found"** → Check spelling in `CLASS_ATTR_*` and struct member

## Performance Tips

✅ **Do:**
- Read parameters once at start of perform function
- Process samples in tight inner loop
- Use local variables (compiler optimization)
- Cache frequently used calculations

❌ **Don't:**
- Read attributes repeatedly in inner loop
- Call functions in inner loop (inline them)
- Use locks in perform function
- Allocate memory in perform function

## Documentation

See full documentation:
- `DSP_EXTERNAL_TEMPLATE.md` - Complete template
- `MAX_PROCESSING_MODELS.md` - Architecture deep dive
- `ATTRIBUTE_SETTERS_EXAMPLE.md` - Filter example

**Workflow:** Use AI to generate boilerplate, focus on DSP algorithm.
