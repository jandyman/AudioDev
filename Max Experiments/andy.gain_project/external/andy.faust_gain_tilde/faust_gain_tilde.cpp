// andy.faust_gain~ - Faust-powered gain external for Max/MSP
// Matches andy.gain~ interface but uses Faust for DSP processing

#include "c74_msp.h"

// Include Faust architecture base classes
#include "faust_minimal.h"

// Include Faust-generated DSP class
#include "faust_gain.cpp"

using namespace c74::max;

// External object structure
struct t_faust_gain {
  t_pxobject ob;
  double gain;              // Gain parameter (0.0 to 10.0)
  FaustGain *faust_dsp;     // Faust DSP instance
  MapUI *faust_ui;          // Faust UI for parameter access
  int sample_rate;          // Current sample rate
};

// Function prototypes
void *faust_gain_new(t_symbol *s, long argc, t_atom *argv);
void faust_gain_free(t_faust_gain *x);
void faust_gain_dsp64(t_faust_gain *x, t_object *dsp64, short *count, double sample_rate, long max_vector_size, long flags);
void faust_gain_perform64(t_faust_gain *x, t_object *dsp64, double **ins, long numins, double **outs, long numouts, long sampleframes, long flags, void *userparam);
void faust_gain_assist(t_faust_gain *x, void *b, long m, long a, char *s);
t_max_err faust_gain_gain_set(t_faust_gain *x, void *attr, long argc, t_atom *argv);

// Global class pointer
static t_class *faust_gain_class = nullptr;

// Initialization routine called when external is loaded
void ext_main(void *r) {
  t_class *c = class_new("andy.faust_gain~",
                         (method)faust_gain_new,
                         (method)faust_gain_free,
                         sizeof(t_faust_gain),
                         nullptr,
                         A_GIMME,
                         0);

  class_addmethod(c, (method)faust_gain_dsp64, "dsp64", A_CANT, 0);
  class_addmethod(c, (method)faust_gain_assist, "assist", A_CANT, 0);
  class_dspinit(c);

  // Attribute: gain (range 0.0 to 10.0, default 1.0)
  CLASS_ATTR_DOUBLE(c, "gain", 0, t_faust_gain, gain);
  CLASS_ATTR_FILTER_CLIP(c, "gain", 0.0, 10.0);
  CLASS_ATTR_LABEL(c, "gain", 0, "Gain");
  CLASS_ATTR_SAVE(c, "gain", 0);
  CLASS_ATTR_DEFAULT(c, "gain", 0, "1.0");
  CLASS_ATTR_ACCESSORS(c, "gain", NULL, faust_gain_gain_set);

  class_register(CLASS_BOX, c);
  faust_gain_class = c;

  post("andy.faust_gain~ v1.0 - Faust-powered gain external");
}

// Object instantiation
void *faust_gain_new(t_symbol *s, long argc, t_atom *argv) {
  t_faust_gain *x = (t_faust_gain *)object_alloc(faust_gain_class);

  if (x) {
    dsp_setup((t_pxobject *)x, 1);  // 1 signal inlet
    outlet_new((t_object *)x, "signal");  // 1 signal outlet

    x->gain = 1.0;  // Default unity gain
    x->faust_dsp = nullptr;  // Will be created in dsp64
    x->faust_ui = nullptr;   // Will be created in dsp64
    x->sample_rate = 44100;  // Default, will be updated in dsp64

    attr_args_process(x, argc, argv);
  }

  return x;
}

// Object destruction
void faust_gain_free(t_faust_gain *x) {
  dsp_free((t_pxobject *)x);

  if (x->faust_dsp) {
    delete x->faust_dsp;
    x->faust_dsp = nullptr;
  }

  if (x->faust_ui) {
    delete x->faust_ui;
    x->faust_ui = nullptr;
  }
}

// DSP chain setup (called when audio is started or sample rate changes)
void faust_gain_dsp64(t_faust_gain *x, t_object *dsp64, short *count, double sample_rate, long max_vector_size, long flags) {
  // Clean up existing Faust instances if sample rate changed
  if (x->faust_dsp && x->sample_rate != (int)sample_rate) {
    delete x->faust_dsp;
    x->faust_dsp = nullptr;
    delete x->faust_ui;
    x->faust_ui = nullptr;
  }

  // Create new Faust DSP instance if needed
  if (!x->faust_dsp) {
    x->faust_dsp = new FaustGain();
    x->faust_ui = new MapUI();

    // Build UI to get parameter pointers
    x->faust_dsp->buildUserInterface(x->faust_ui);

    // Initialize DSP
    x->faust_dsp->init((int)sample_rate);
    x->sample_rate = (int)sample_rate;

    // Set initial gain value through UI
    x->faust_ui->setParamValue("gain", x->gain);
  }

  object_method(dsp64, gensym("dsp_add64"), x, faust_gain_perform64, 0, nullptr);
}

// Audio processing callback (64-bit)
void faust_gain_perform64(t_faust_gain *x, t_object *dsp64, double **ins, long numins, double **outs, long numouts, long sampleframes, long flags, void *userparam) {
  if (!x->faust_dsp) return;

  // Get input and output buffers
  double *in = ins[0];
  double *out = outs[0];

  // Call Faust compute method
  // Faust compute signature: compute(int count, FAUSTFLOAT** inputs, FAUSTFLOAT** outputs)
  x->faust_dsp->compute(sampleframes, &in, &out);
}

// Inlet/outlet assistance (hover text)
void faust_gain_assist(t_faust_gain *x, void *b, long m, long a, char *s) {
  if (m == ASSIST_INLET) {
    sprintf(s, "(signal) Audio Input");
  } else {
    sprintf(s, "(signal) Audio Output");
  }
}

// Custom setter for gain attribute
t_max_err faust_gain_gain_set(t_faust_gain *x, void *attr, long argc, t_atom *argv) {
  if (argc && argv) {
    x->gain = atom_getfloat(argv);

    // Update Faust DSP parameter through UI
    if (x->faust_ui) {
      x->faust_ui->setParamValue("gain", x->gain);
    }
  }
  return MAX_ERR_NONE;
}
