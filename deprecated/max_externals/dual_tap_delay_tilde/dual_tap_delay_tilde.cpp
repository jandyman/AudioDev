// dual_tap_delay~ - Faust-powered dual tap delay for Max/MSP
// Single delay buffer with two independent read taps
// High-quality interpolation (9th order Lagrange)

#include "c74_msp.h"

// Include Faust architecture base classes
#include "faust_minimal.h"

// Include Faust-generated DSP class
#include "faust_dual_tap_delay.cpp"

using namespace c74::max;

// External object structure
struct t_dual_tap_delay {
  t_pxobject ob;
  FaustDualTapDelay *faust_dsp;  // Faust DSP instance
  int sample_rate;                // Current sample rate
};

// Function prototypes
void *dual_tap_delay_new(t_symbol *s, long argc, t_atom *argv);
void dual_tap_delay_free(t_dual_tap_delay *x);
void dual_tap_delay_dsp64(t_dual_tap_delay *x, t_object *dsp64, short *count, double sample_rate, long max_vector_size, long flags);
void dual_tap_delay_perform64(t_dual_tap_delay *x, t_object *dsp64, double **ins, long numins, double **outs, long numouts, long sampleframes, long flags, void *userparam);
void dual_tap_delay_assist(t_dual_tap_delay *x, void *b, long m, long a, char *s);

// Global class pointer
static t_class *dual_tap_delay_class = nullptr;

// Initialization routine called when external is loaded
void ext_main(void *r) {
  t_class *c = class_new("dual_tap_delay~",
                         (method)dual_tap_delay_new,
                         (method)dual_tap_delay_free,
                         sizeof(t_dual_tap_delay),
                         nullptr,
                         A_GIMME,
                         0);

  class_addmethod(c, (method)dual_tap_delay_dsp64, "dsp64", A_CANT, 0);
  class_addmethod(c, (method)dual_tap_delay_assist, "assist", A_CANT, 0);
  class_dspinit(c);

  class_register(CLASS_BOX, c);
  dual_tap_delay_class = c;

  post("dual_tap_delay~ v1.0 - Faust dual tap delay (9th order interpolation)");
}

// Object instantiation
void *dual_tap_delay_new(t_symbol *s, long argc, t_atom *argv) {
  t_dual_tap_delay *x = (t_dual_tap_delay *)object_alloc(dual_tap_delay_class);

  if (x) {
    dsp_setup((t_pxobject *)x, 3);  // 3 signal inlets (audio, delay1, delay2)
    outlet_new((t_object *)x, "signal");  // Signal outlet 1 (tap1)
    outlet_new((t_object *)x, "signal");  // Signal outlet 2 (tap2)

    x->faust_dsp = nullptr;  // Will be created in dsp64
    x->sample_rate = 44100;  // Default, will be updated in dsp64
  }

  return x;
}

// Object destruction
void dual_tap_delay_free(t_dual_tap_delay *x) {
  dsp_free((t_pxobject *)x);

  if (x->faust_dsp) {
    delete x->faust_dsp;
    x->faust_dsp = nullptr;
  }
}

// DSP chain setup (called when audio is started or sample rate changes)
void dual_tap_delay_dsp64(t_dual_tap_delay *x, t_object *dsp64, short *count, double sample_rate, long max_vector_size, long flags) {
  // Clean up existing Faust instance if sample rate changed
  if (x->faust_dsp && x->sample_rate != (int)sample_rate) {
    delete x->faust_dsp;
    x->faust_dsp = nullptr;
  }

  // Create new Faust DSP instance if needed
  if (!x->faust_dsp) {
    x->faust_dsp = new FaustDualTapDelay();

    // Initialize DSP
    x->faust_dsp->init((int)sample_rate);
    x->sample_rate = (int)sample_rate;
  }

  object_method(dsp64, gensym("dsp_add64"), x, dual_tap_delay_perform64, 0, nullptr);
}

// Audio processing callback (64-bit)
void dual_tap_delay_perform64(t_dual_tap_delay *x, t_object *dsp64, double **ins, long numins, double **outs, long numouts, long sampleframes, long flags, void *userparam) {
  if (!x->faust_dsp) return;

  // Get input buffers (3 inputs: audio, delay1_ms, delay2_ms)
  double *in_audio = ins[0];
  double *in_delay1 = ins[1];
  double *in_delay2 = ins[2];

  // Get output buffers (2 outputs: tap1, tap2)
  double *out_tap1 = outs[0];
  double *out_tap2 = outs[1];

  // Create arrays of pointers for Faust compute method
  double *faust_ins[3] = {in_audio, in_delay1, in_delay2};
  double *faust_outs[2] = {out_tap1, out_tap2};

  // Call Faust compute method
  // Faust compute signature: compute(int count, FAUSTFLOAT** inputs, FAUSTFLOAT** outputs)
  x->faust_dsp->compute(sampleframes, faust_ins, faust_outs);
}

// Inlet/outlet assistance (hover text)
void dual_tap_delay_assist(t_dual_tap_delay *x, void *b, long m, long a, char *s) {
  if (m == ASSIST_INLET) {
    switch (a) {
      case 0: sprintf(s, "(signal) Audio Input"); break;
      case 1: sprintf(s, "(signal) Delay Time 1 (ms)"); break;
      case 2: sprintf(s, "(signal) Delay Time 2 (ms)"); break;
    }
  } else {
    switch (a) {
      case 0: sprintf(s, "(signal) Tap 1 Output"); break;
      case 1: sprintf(s, "(signal) Tap 2 Output"); break;
    }
  }
}
