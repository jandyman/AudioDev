// split_chorus~ - Max MSP External
// Dual band chorus effect: lows bypass, highs with random modulation
// Wraps SplitChorus from dsp_library

#include "../../dsp_library/cpp/include/split_chorus.h"
#include "ext.h"
#include "ext_obex.h"
#include "z_dsp.h"
#include <vector>

// Max object structure
typedef struct _split_chorus_tilde {
    t_pxobject obj;
    SplitChorus* processor;
} t_split_chorus_tilde;

// Global class pointer
static t_class *split_chorus_tilde_class = NULL;

// Function prototypes
void *split_chorus_tilde_new(t_symbol *s, long argc, t_atom *argv);
void split_chorus_tilde_free(t_split_chorus_tilde *x);
void split_chorus_tilde_assist(t_split_chorus_tilde *x, void *b, long m, long a, char *s);
void split_chorus_tilde_dsp64(t_split_chorus_tilde *x, t_object *dsp64, short *count, double samplerate, long maxvectorsize, long flags);
void split_chorus_tilde_perform64(t_split_chorus_tilde *x, t_object *dsp64, double **ins, long numins, double **outs, long numouts, long sampleframes, long flags, void *userparam);

// Parameter setters
void split_chorus_tilde_crossover(t_split_chorus_tilde *x, double f);
void split_chorus_tilde_delay(t_split_chorus_tilde *x, double f);
void split_chorus_tilde_rate(t_split_chorus_tilde *x, double f);
void split_chorus_tilde_depth(t_split_chorus_tilde *x, double f);
void split_chorus_tilde_wet(t_split_chorus_tilde *x, double f);

// Main entry point
extern "C" void ext_main(void *r) {
    t_class *c = class_new("split_chorus~",
                          (method)split_chorus_tilde_new,
                          (method)split_chorus_tilde_free,
                          sizeof(t_split_chorus_tilde),
                          NULL,
                          A_GIMME,
                          0);

    class_addmethod(c, (method)split_chorus_tilde_dsp64, "dsp64", A_CANT, 0);
    class_addmethod(c, (method)split_chorus_tilde_assist, "assist", A_CANT, 0);

    // Add parameter methods
    class_addmethod(c, (method)split_chorus_tilde_crossover, "crossover", A_FLOAT, 0);
    class_addmethod(c, (method)split_chorus_tilde_delay, "delay", A_FLOAT, 0);
    class_addmethod(c, (method)split_chorus_tilde_rate, "rate", A_FLOAT, 0);
    class_addmethod(c, (method)split_chorus_tilde_depth, "depth", A_FLOAT, 0);
    class_addmethod(c, (method)split_chorus_tilde_wet, "wet", A_FLOAT, 0);

    class_dspinit(c);
    class_register(CLASS_BOX, c);
    split_chorus_tilde_class = c;

    post("split_chorus~ v1.0 - Dual band chorus (dsp_library)");
}

// Object creation
void *split_chorus_tilde_new(t_symbol *s, long argc, t_atom *argv) {
    t_split_chorus_tilde *x = (t_split_chorus_tilde *)object_alloc(split_chorus_tilde_class);

    if (x) {
        dsp_setup((t_pxobject *)x, 1);  // 1 inlet
        outlet_new(x, "signal");         // 1 outlet

        // Create processor
        x->processor = new SplitChorus();

        // Initialize with default sample rate (will be updated in dsp64)
        x->processor->init(44100);

        post("split_chorus~: created (crossover=%.1f Hz, delay=%.1f ms, rate=%.1f Hz, depth=%.2f, wet=%.2f)",
             x->processor->get_param("crossover"),
             x->processor->get_param("delay"),
             x->processor->get_param("rate"),
             x->processor->get_param("depth"),
             x->processor->get_param("wet"));
    }

    return x;
}

// Object destruction
void split_chorus_tilde_free(t_split_chorus_tilde *x) {
    dsp_free((t_pxobject *)x);
    if (x->processor) {
        delete x->processor;
        x->processor = NULL;
    }
}

// Assist strings (inlet/outlet descriptions)
void split_chorus_tilde_assist(t_split_chorus_tilde *x, void *b, long m, long a, char *s) {
    if (m == ASSIST_INLET) {
        sprintf(s, "(signal) Audio input");
    } else {
        sprintf(s, "(signal) Chorused output");
    }
}

// DSP setup
void split_chorus_tilde_dsp64(t_split_chorus_tilde *x, t_object *dsp64, short *count, double samplerate, long maxvectorsize, long flags) {
    // Update processor sample rate
    x->processor->init((int)samplerate);

    object_method(dsp64, gensym("dsp_add64"), x, split_chorus_tilde_perform64, 0, NULL);
}

// Audio processing (perform routine)
void split_chorus_tilde_perform64(t_split_chorus_tilde *x, t_object *dsp64, double **ins, long numins, double **outs, long numouts, long sampleframes, long flags, void *userparam) {
    double *in = ins[0];
    double *out = outs[0];

    // Convert Max double buffers to float vectors
    std::vector<float> input_vec(sampleframes);
    for (long i = 0; i < sampleframes; i++) {
        input_vec[i] = (float)in[i];
    }

    // Process
    std::vector<std::vector<float>> inputs = {input_vec};
    std::vector<std::vector<float>> outputs(1);
    outputs[0].resize(sampleframes);

    x->processor->process(inputs, outputs);

    // Convert back to Max double buffers
    for (long i = 0; i < sampleframes; i++) {
        out[i] = (double)outputs[0][i];
    }
}

// Parameter setters
void split_chorus_tilde_crossover(t_split_chorus_tilde *x, double f) {
    x->processor->set_param("crossover", (float)f);
}

void split_chorus_tilde_delay(t_split_chorus_tilde *x, double f) {
    x->processor->set_param("delay", (float)f);
}

void split_chorus_tilde_rate(t_split_chorus_tilde *x, double f) {
    x->processor->set_param("rate", (float)f);
}

void split_chorus_tilde_depth(t_split_chorus_tilde *x, double f) {
    x->processor->set_param("depth", (float)f);
}

void split_chorus_tilde_wet(t_split_chorus_tilde *x, double f) {
    x->processor->set_param("wet", (float)f);
}
