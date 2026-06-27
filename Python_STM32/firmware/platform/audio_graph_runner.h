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

// ---- DSP profiling -------------------------------------------------------
// Cycle accounting for process_chunk, captured per audio block on BARE_METAL.
// The runner keeps a rolling ring of the last AUDIO_PROFILE_RING block costs
// (the time-series) plus these summary scalars.
#define AUDIO_PROFILE_RING 128

typedef struct {
  uint32_t last_cycles;    // process_chunk cost of the most recent block
  uint32_t max_cycles;     // worst-case block; host zeroes it via WRITE_MEM to window
  uint32_t block_count;    // total blocks processed (monotonic; also ring write pos)
} audio_profile;

// Telemetry symbols — the host reads these straight from target memory by name
// (resolved from the .map) via the RTT READ_MEM command; the CPU does the access
// so it is D-cache coherent. WRITE_MEM zeroes the peaks/max for windowed meters.
// Global (non-static) so they appear as clean symbols in the .map.
extern volatile float         audio_in_peak;
extern volatile float         audio_out_peak;
extern volatile audio_profile audio_dsp_profile;                  // BARE_METAL
extern volatile uint32_t      audio_dsp_cycle_ring[AUDIO_PROFILE_RING];  // BARE_METAL

// Enable the DWT cycle counter so audio_graph_process can time the DSP. Call
// once at boot after the core clock is up. No-op off-target (non-BARE_METAL).
void audio_graph_profile_init(void);

// Process one chunk: ins[kNumInputs] and outs[kNumOutputs], n frames each.
// Updates the input/output peak meters as a side effect, and on BARE_METAL
// records the cycle cost of the DSP (process_chunk only, not the metering).
void audio_graph_process(const float* const* ins, float* const* outs, int n);

// Set a graph parameter at runtime. `path` routes through the generated graph's
// set_param (e.g. "lc.pitch_ratio", "lpf.fc"). Called from the foreground loop;
// the caller guards against the audio ISR (the RTT handler brackets it with a
// brief interrupt disable) since the DSP block reads these values concurrently.
void audio_graph_set_param(const char* path, float value);

#ifdef __cplusplus
}
#endif
