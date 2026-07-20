/**
 * andy.gain~ - Simple gain/volume control external for Max/MSP
 *
 * Applies a gain multiplier to an audio signal.
 * Uses modern attribute-based parameter control.
 */

#include "ext.h"
#include "ext_obex.h"
#include "z_dsp.h"

// Adding random comment to trigger git

// Structure to hold the object data
typedef struct _gain {
  t_pxobject obj;        // Max/MSP object header
  double gain;           // Current gain value (linear, not dB)
} t_gain;

// Global pointer to the class
static t_class *gain_class = NULL;

// Function prototypes
void *gain_new(t_symbol *s, long argc, t_atom *argv);
void gain_free(t_gain *x);
void gain_dsp64(t_gain *x, t_object *dsp64, short *count, double samplerate, long maxvectorsize, long flags);
void gain_perform64(t_gain *x, t_object *dsp64, double **ins, long numins, double **outs, long numouts, long sampleframes, long flags, void *userparam);
void gain_assist(t_gain *x, void *b, long m, long a, char *s);

// Initialization routine - called when Max loads the external
void ext_main(void *r) {
  t_class *c;

  c = class_new("andy.gain~",
                (method)gain_new,
                (method)gain_free,
                (long)sizeof(t_gain),
                0L,
                A_GIMME,
                0);

  class_addmethod(c, (method)gain_dsp64, "dsp64", A_CANT, 0);
  class_addmethod(c, (method)gain_assist, "assist", A_CANT, 0);

  // Register gain attribute (modern approach)
  CLASS_ATTR_DOUBLE(c, "gain", 0, t_gain, gain);
  CLASS_ATTR_FILTER_CLIP(c, "gain", 0.0, 10.0);  // Limit range 0.0 to 10.0
  CLASS_ATTR_LABEL(c, "gain", 0, "Gain");
  CLASS_ATTR_SAVE(c, "gain", 0);  // Save with patcher
  CLASS_ATTR_DEFAULT(c, "gain", 0, "1.0");  // Default value

  class_dspinit(c);
  class_register(CLASS_BOX, c);
  gain_class = c;

  post("andy.gain~ - gain control with attributes");
}

// Object creation - called when user creates an andy.gain~ object
void *gain_new(t_symbol *s, long argc, t_atom *argv) {
  t_gain *x = (t_gain *)object_alloc(gain_class);

  if (x) {
    dsp_setup((t_pxobject *)x, 1);  // One signal inlet
    outlet_new((t_object *)x, "signal");  // One signal outlet

    // Set default value (will be overridden by attributes if provided)
    x->gain = 1.0;

    // Process attribute arguments (e.g., @gain 0.5)
    attr_args_process(x, argc, argv);
  }

  return x;
}

// Object destruction
void gain_free(t_gain *x) {
  dsp_free((t_pxobject *)x);
}

// DSP chain setup - called when audio is turned on
void gain_dsp64(t_gain *x, t_object *dsp64, short *count, double samplerate, long maxvectorsize, long flags) {
  object_method(dsp64,
                gensym("dsp_add64"),
                x,
                gain_perform64,
                0,
                NULL);
}

// Audio processing function - called for each block of samples
void gain_perform64(t_gain *x, t_object *dsp64, double **ins, long numins, double **outs, long numouts, long sampleframes, long flags, void *userparam) {
  double *in = ins[0];    // Input audio buffer
  double *out = outs[0];  // Output audio buffer
  long n = sampleframes;  // Number of samples in this block
  double gain = x->gain;  // Read attribute value (thread-safe for single double)

  // Process each sample
  while (n--) {
    *out++ = *in++ * gain;
  }
}

// Assist strings (help text for inlets/outlets)
void gain_assist(t_gain *x, void *b, long m, long a, char *s) {
  if (m == ASSIST_INLET) {
    snprintf(s, 256, "(signal) Audio Input");
  } else {
    snprintf(s, 256, "(signal) Audio Output");
  }
}
