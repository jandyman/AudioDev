// audio_graph_runner.cpp — graph-agnostic runner shared by all firmware projects.
// Names the pipeline only through the generated header's `audio_graph` alias;
// the header is selected per project with -DAUDIO_GRAPH_HEADER="<graph>.h".
#include "audio_graph_runner.h"

#ifndef AUDIO_GRAPH_HEADER
#error "define AUDIO_GRAPH_HEADER, e.g. -DAUDIO_GRAPH_HEADER=\"pitch_shifter.h\""
#endif
#include AUDIO_GRAPH_HEADER

#include "stm32h750xx.h"   // DWT / CoreDebug
#include <math.h>

static audio_graph g_graph;

// Telemetry — global (non-static) so the host resolves them by symbol from the
// .map and reads them with the RTT READ_MEM command (CPU does the access, so it
// is D-cache coherent). Peaks are running maxima; the host zeroes them via
// WRITE_MEM to window "peak since last poll".
volatile float audio_in_peak  = 0.0f;
volatile float audio_out_peak = 0.0f;

// DWT cycle profiling of the DSP. Counts at the core clock (480 MHz on the H750);
// the host converts to time / %budget. BARE_METAL only — the DWT is a Cortex-M
// debug unit absent from the native build. audio_dsp_cycle_ring is the per-block
// cost time-series; audio_dsp_profile the summary scalars.
#if defined(BARE_METAL)
volatile audio_profile audio_dsp_profile = {0u, 0u, 0u};
volatile uint32_t      audio_dsp_cycle_ring[AUDIO_PROFILE_RING] = {0u};
#endif

void audio_graph_init(int sample_rate) {
  g_graph.init(sample_rate);
}

void audio_graph_profile_init(void) {
#if defined(BARE_METAL)
  CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
  DWT->LAR = 0xC5ACCE55u;                 // unlock DWT (gated on some M7 silicon)
  DWT->CYCCNT = 0u;
  DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;
#endif
}

void audio_graph_process(const float* const* ins, float* const* outs, int n) {
  // Input meter on channel 0.
  float in_peak = audio_in_peak;
  if (ins && ins[0]) {
    for (int i = 0; i < n; ++i) {
      float a = fabsf(ins[0][i]);
      if (a > in_peak) in_peak = a;
    }
  }

#if defined(BARE_METAL)
  uint32_t cyc0 = DWT->CYCCNT;
#endif
  g_graph.process_chunk(ins, outs, n);
#if defined(BARE_METAL)
  uint32_t dt = DWT->CYCCNT - cyc0;       // wraps cleanly mod 2^32 at 480 MHz (~8.9 s)
  uint32_t idx = audio_dsp_profile.block_count % AUDIO_PROFILE_RING;
  audio_dsp_cycle_ring[idx]     = dt;
  audio_dsp_profile.last_cycles = dt;
  if (dt > audio_dsp_profile.max_cycles) audio_dsp_profile.max_cycles = dt;
  audio_dsp_profile.block_count++;
#endif

  // Output meter on the last output channel (the processed one — e.g. the
  // shifted channel for the pitch shifter, whose dry channel is output 0).
  float out_peak = audio_out_peak;
  const float* last = outs[audio_graph::kNumOutputs - 1];
  if (last) {
    for (int i = 0; i < n; ++i) {
      float a = fabsf(last[i]);
      if (a > out_peak) out_peak = a;
    }
  }

  audio_in_peak  = in_peak;
  audio_out_peak = out_peak;
}
