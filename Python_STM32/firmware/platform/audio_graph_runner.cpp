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

#if defined(BARE_METAL)
#include "level_meter.h"   // platform RGB level meter (LEDs absent off-target)
#endif

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
#if defined(BARE_METAL)
  level_meter_init();          // platform owns the Pod meter; no per-project glue
#endif
}

void audio_graph_set_param(const char* path, float value) {
  g_graph.set_param(path, value);
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
  // Input level — block-local peak on channel 0, folded into the running
  // telemetry maximum (the host clears it via WRITE_MEM to window each poll).
  float in_blk = 0.0f;
  if (ins && ins[0]) {
    for (int i = 0; i < n; ++i) {
      float a = fabsf(ins[0][i]);
      if (a > in_blk) in_blk = a;
    }
  }
  if (in_blk > audio_in_peak) audio_in_peak = in_blk;

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

  // Output level — block-local peak on the last output channel (the processed
  // one — e.g. the shifted channel for the pitch shifter; dry is output 0).
  float out_blk = 0.0f;
  const float* last = outs[audio_graph::kNumOutputs - 1];
  if (last) {
    for (int i = 0; i < n; ++i) {
      float a = fabsf(last[i]);
      if (a > out_blk) out_blk = a;
    }
  }
  if (out_blk > audio_out_peak) audio_out_peak = out_blk;

#if defined(BARE_METAL)
  // Drive the Pod LEDs from here so every graph project gets the meter for free
  // with zero per-project glue. Off the update beat the only added cost is two
  // float compares to accumulate the windowed peak; the actual LED refresh runs
  // every kMeterUpdateBlocks blocks (~50 Hz at 1 ms blocks) — a handful of GPIO
  // writes ~50x/s, negligible against the audio budget. The meter keeps its own
  // window so it never disturbs the host's telemetry peaks above.
  static constexpr uint32_t kMeterUpdateBlocks = 20U;
  static float s_meter_in  = 0.0f;
  static float s_meter_out = 0.0f;
  if (in_blk  > s_meter_in)  s_meter_in  = in_blk;
  if (out_blk > s_meter_out) s_meter_out = out_blk;
  if (audio_dsp_profile.block_count % kMeterUpdateBlocks == 0U) {
    level_meter_update(s_meter_in, s_meter_out);
    s_meter_in  = 0.0f;
    s_meter_out = 0.0f;
  }
#endif
}
