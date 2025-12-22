# Coding Style Guide

## Overview

All Max external projects use **K&R (Kernighan & Ritchie) / Google C++ Style** for consistency and readability.

## Key Style Rules

### Indentation
- **2 spaces** per indent level (no tabs)
- Continuation lines: align with opening delimiter or indent +4 spaces

### Braces
- **Opening brace on same line** as function/control statement (K&R style)
- Closing brace on its own line, aligned with statement start

```cpp
// Correct
void my_function() {
  if (condition) {
    do_something();
  } else {
    do_something_else();
  }
}

// Wrong (Allman/BSD style - don't use)
void my_function()
{
  if (condition)
  {
    do_something();
  }
}
```

### Line Length
- **Prefer 80 characters max**, 100 characters hard limit
- Break long function calls across multiple lines

### Naming Conventions

Follow Max SDK conventions:

```cpp
// Types: lowercase with underscores
typedef struct _gain {
  t_pxobject obj;
  double gain_value;
} t_gain;

// Functions: lowercase with underscores
void gain_dsp64(t_gain *x, ...);
void *gain_new(t_symbol *s, long argc, t_atom *argv);

// Constants/Macros: UPPERCASE
#define MAX_BUFFER_SIZE 512

// Local variables: lowercase with underscores
double sample_rate = 44100.0;
long vector_size = 64;
```

### Comments

```cpp
// Single-line comments for brief explanations
double gain = x->gain_value;  // Get current gain value

/**
 * Multi-line comments for function documentation
 * Use Doxygen-style when documenting APIs
 */
void gain_perform64(t_gain *x, ...) {
  // Implementation
}

// Section separators
//============================================================
// DSP Processing Functions
//============================================================
```

### Whitespace

```cpp
// Spaces around binary operators
x = a + b;
result = (value * 2) + offset;

// No space before semicolon
do_something();

// Space after comma in argument lists
function(arg1, arg2, arg3);

// No space inside parentheses
if (x == 5) {  // not: if ( x == 5 )

// Blank line between function definitions
void function1() {
  // ...
}

void function2() {
  // ...
}
```

### Pointers and References

```cpp
// Pointer * attached to type (Google style)
double *buffer;
t_gain *x;

// When declaring multiple variables, split to separate lines
double *in;
double *out;

// Not: double *in, *out;  (confusing)
```

### Control Flow

```cpp
// Always use braces, even for single-line bodies
if (condition) {
  single_statement();
}

// Not: if (condition) single_statement();

// For loops: space after 'for', spaces around semicolons
for (long i = 0; i < count; i++) {
  process(i);
}

// While loops
while (n--) {
  *out++ = *in++ * gain;
}
```

### Function Definitions

```cpp
// Return type on same line as function name
void gain_free(t_gain *x) {
  dsp_free((t_pxobject *)x);
}

// Long parameter lists: break after opening paren, align or indent +4
void gain_perform64(
    t_gain *x,
    t_object *dsp64,
    double **ins,
    long numins,
    double **outs,
    long numouts,
    long sampleframes,
    long flags,
    void *userparam) {
  // Implementation
}
```

### Max-Specific Conventions

```cpp
// Object structure: leading underscore, typedef to t_
typedef struct _gain {
  t_pxobject obj;        // ALWAYS first member
  double gain_value;     // Instance variables
} t_gain;

// Class registration: use lowercase with tilde
class_new("andy.gain~", ...);

// Use object_post for debugging, post for global messages
object_post((t_object *)x, "Object-specific message");
post("Global message");

// Use snprintf, never sprintf (security)
snprintf(buffer, sizeof(buffer), "Value: %f", value);
```

## Example: Well-Formatted Function

```cpp
// DSP processing function - called for each block of samples
void gain_perform64(
    t_gain *x,
    t_object *dsp64,
    double **ins,
    long numins,
    double **outs,
    long numouts,
    long sampleframes,
    long flags,
    void *userparam) {

  double *in = ins[0];    // Input audio buffer
  double *out = outs[0];  // Output audio buffer
  long n = sampleframes;  // Number of samples in this block
  double gain = x->gain_value;

  // Process each sample
  while (n--) {
    *out++ = *in++ * gain;
  }
}
```

## Editor Configuration

### VS Code (.vscode/settings.json)
```json
{
  "editor.tabSize": 2,
  "editor.insertSpaces": true,
  "editor.detectIndentation": false,
  "C_Cpp.clang_format_fallbackStyle": "{ BasedOnStyle: Google, IndentWidth: 2, ColumnLimit: 100 }"
}
```

### Xcode
1. Preferences → Text Editing → Indentation
2. Prefer indent using: **Spaces**
3. Tab width: **2 spaces**
4. Indent width: **2 spaces**

### .clang-format (Optional)
```yaml
BasedOnStyle: Google
IndentWidth: 2
ColumnLimit: 100
PointerAlignment: Left
```

## Why K&R Style?

- **Concise**: Opening braces don't waste vertical space
- **Readable**: Clear visual hierarchy
- **Standard**: Used by Google, Linux kernel (variants), Max SDK examples
- **Consistent**: One brace style throughout

## Common Pitfalls to Avoid

```cpp
// DON'T: Use sprintf (security risk)
sprintf(buffer, "Value: %f", value);

// DO: Use snprintf with size
snprintf(buffer, sizeof(buffer), "Value: %f", value);

// DON'T: Forget braces on single-line if
if (x) do_something();

// DO: Always use braces
if (x) {
  do_something();
}

// DON'T: Multiple declarations in one line
double *in, *out, gain;

// DO: Separate lines for clarity
double *in;
double *out;
double gain;
```

## Reference

- Google C++ Style Guide: https://google.github.io/styleguide/cppguide.html
- K&R: "The C Programming Language" by Kernighan & Ritchie
- Max SDK: Check `max-sdk/source/audio/` examples for Max-specific conventions
