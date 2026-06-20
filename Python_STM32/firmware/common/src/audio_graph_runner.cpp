// audio_graph_runner.cpp — graph-agnostic runner shared by all firmware projects.
// Names the pipeline only through the generated header's `audio_graph` alias;
// the header is selected per project with -DAUDIO_GRAPH_HEADER="<graph>.h".
#include "audio_graph_runner.h"

#ifndef AUDIO_GRAPH_HEADER
#error "define AUDIO_GRAPH_HEADER, e.g. -DAUDIO_GRAPH_HEADER=\"pitch_shifter.h\""
#endif
#include AUDIO_GRAPH_HEADER

#include "stm32h750xx.h"   // __get_PRIMASK / __disable_irq / __set_PRIMASK
#include <math.h>

static audio_graph    g_graph;
static volatile float g_in_peak  = 0.0f;
static volatile float g_out_peak = 0.0f;

void audio_graph_init(int sample_rate) {
  g_graph.init(sample_rate);
}

void audio_graph_process(const float* const* ins, float* const* outs, int n) {
  // Input meter on channel 0.
  float in_peak = g_in_peak;
  if (ins && ins[0]) {
    for (int i = 0; i < n; ++i) {
      float a = fabsf(ins[0][i]);
      if (a > in_peak) in_peak = a;
    }
  }

  g_graph.process_chunk(ins, outs, n);

  // Output meter on the last output channel (the processed one — e.g. the
  // shifted channel for the pitch shifter, whose dry channel is output 0).
  float out_peak = g_out_peak;
  const float* last = outs[audio_graph::kNumOutputs - 1];
  if (last) {
    for (int i = 0; i < n; ++i) {
      float a = fabsf(last[i]);
      if (a > out_peak) out_peak = a;
    }
  }

  g_in_peak  = in_peak;
  g_out_peak = out_peak;
}

void audio_graph_peaks_read_and_clear(float* in_peak, float* out_peak) {
  uint32_t primask = __get_PRIMASK();
  __disable_irq();
  *in_peak  = g_in_peak;
  *out_peak = g_out_peak;
  g_in_peak  = 0.0f;
  g_out_peak = 0.0f;
  __set_PRIMASK(primask);
}
