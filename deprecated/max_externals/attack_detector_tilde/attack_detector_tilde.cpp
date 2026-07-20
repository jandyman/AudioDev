// attack_detector~ - Faust-powered attack detector for Max/MSP
// Bass guitar transient detection with probe outputs
//
// Input:  audio signal
// Output: trigger, threshold, fast_env, slow_env, note_ended

#include "c74_msp.h"

// Include Faust architecture base classes
#include "faust_minimal.h"

// Include Faust-generated DSP class
#include "faust_attack_detector.cpp"

using namespace c74::max;

// External object structure
struct t_attack_detector {
  t_pxobject ob;
  FaustAttackDetector *faust_dsp;  // Faust DSP instance
  int sample_rate;                  // Current sample rate
};

// Function prototypes
void *attack_detector_new(t_symbol *s, long argc, t_atom *argv);
void attack_detector_free(t_attack_detector *x);
void attack_detector_dsp64(t_attack_detector *x, t_object *dsp64, short *count, double sample_rate, long max_vector_size, long flags);
void attack_detector_perform64(t_attack_detector *x, t_object *dsp64, double **ins, long numins, double **outs, long numouts, long sampleframes, long flags, void *userparam);
void attack_detector_assist(t_attack_detector *x, void *b, long m, long a, char *s);

// Global class pointer
static t_class *attack_detector_class = nullptr;

// Initialization routine called when external is loaded
void ext_main(void *r) {
  t_class *c = class_new("attack_detector~",
                         (method)attack_detector_new,
                         (method)attack_detector_free,
                         sizeof(t_attack_detector),
                         nullptr,
                         A_GIMME,
                         0);

  class_addmethod(c, (method)attack_detector_dsp64, "dsp64", A_CANT, 0);
  class_addmethod(c, (method)attack_detector_assist, "assist", A_CANT, 0);
  class_dspinit(c);

  class_register(CLASS_BOX, c);
  attack_detector_class = c;

  post("attack_detector~ v1.0 - Faust bass guitar attack detector");
}

// Object instantiation
void *attack_detector_new(t_symbol *s, long argc, t_atom *argv) {
  t_attack_detector *x = (t_attack_detector *)object_alloc(attack_detector_class);

  if (x) {
    dsp_setup((t_pxobject *)x, 1);  // 1 signal inlet (audio)
    outlet_new((t_object *)x, "signal");  // Output 1: trigger
    outlet_new((t_object *)x, "signal");  // Output 2: threshold
    outlet_new((t_object *)x, "signal");  // Output 3: fast_env
    outlet_new((t_object *)x, "signal");  // Output 4: slow_env
    outlet_new((t_object *)x, "signal");  // Output 5: note_ended

    x->faust_dsp = nullptr;  // Will be created in dsp64
    x->sample_rate = 44100;  // Default, will be updated in dsp64
  }

  return x;
}

// Object destruction
void attack_detector_free(t_attack_detector *x) {
  dsp_free((t_pxobject *)x);

  if (x->faust_dsp) {
    delete x->faust_dsp;
    x->faust_dsp = nullptr;
  }
}

// DSP chain setup (called when audio is started or sample rate changes)
void attack_detector_dsp64(t_attack_detector *x, t_object *dsp64, short *count, double sample_rate, long max_vector_size, long flags) {
  // Clean up existing Faust instance if sample rate changed
  if (x->faust_dsp && x->sample_rate != (int)sample_rate) {
    delete x->faust_dsp;
    x->faust_dsp = nullptr;
  }

  // Create new Faust DSP instance if needed
  if (!x->faust_dsp) {
    x->faust_dsp = new FaustAttackDetector();
    x->faust_dsp->init((int)sample_rate);
    x->sample_rate = (int)sample_rate;
  }

  object_method(dsp64, gensym("dsp_add64"), x, attack_detector_perform64, 0, nullptr);
}

// Audio processing callback (64-bit)
void attack_detector_perform64(t_attack_detector *x, t_object *dsp64, double **ins, long numins, double **outs, long numouts, long sampleframes, long flags, void *userparam) {
  if (!x->faust_dsp) return;

  // Get input buffer (1 input: audio)
  double *in_audio = ins[0];

  // Get output buffers (5 outputs)
  double *out_trigger = outs[0];
  double *out_threshold = outs[1];
  double *out_fast_env = outs[2];
  double *out_slow_env = outs[3];
  double *out_note_ended = outs[4];

  // Create arrays of pointers for Faust compute method
  double *faust_ins[1] = {in_audio};
  double *faust_outs[5] = {out_trigger, out_threshold, out_fast_env, out_slow_env, out_note_ended};

  // Call Faust compute method
  x->faust_dsp->compute(sampleframes, faust_ins, faust_outs);
}

// Inlet/outlet assistance (hover text)
void attack_detector_assist(t_attack_detector *x, void *b, long m, long a, char *s) {
  if (m == ASSIST_INLET) {
    switch (a) {
      case 0: sprintf(s, "(signal) Audio Input"); break;
    }
  } else {
    switch (a) {
      case 0: sprintf(s, "(signal) Attack Trigger (0/1)"); break;
      case 1: sprintf(s, "(signal) Adaptive Threshold (probe)"); break;
      case 2: sprintf(s, "(signal) Fast Envelope (probe)"); break;
      case 3: sprintf(s, "(signal) Slow Envelope (probe)"); break;
      case 4: sprintf(s, "(signal) Note Ended Flag (probe)"); break;
    }
  }
}
