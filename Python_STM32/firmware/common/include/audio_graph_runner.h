#pragma once
// Generic graph runner — the single graph-aware glue shared by ALL firmware
// projects. Holds the one audio_graph instance and bridges the board audio
// engine to it, naming the pipeline only through the generated header's
// `audio_graph` alias (the header is chosen per project via -DAUDIO_GRAPH_HEADER).
//
// Peak metering lives HERE so it is written once, not re-implemented per project.
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

void audio_graph_init(int sample_rate);

// Process one chunk: ins[kNumInputs] and outs[kNumOutputs], n frames each.
// Updates the input/output peak meters as a side effect.
void audio_graph_process(const float* const* ins, float* const* outs, int n);

// Peak |x| since the last call (input channel 0 / last output channel), then
// clear to zero. Briefly disables IRQs; safe from foreground while audio runs.
void audio_graph_peaks_read_and_clear(float* in_peak, float* out_peak);

#ifdef __cplusplus
}
#endif
