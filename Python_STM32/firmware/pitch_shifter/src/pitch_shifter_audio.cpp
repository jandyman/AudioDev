#include "pitch_shifter_audio.h"
#include "pitch_shifter.h"

static pitch_shifter g_ps;

void pitch_shifter_audio_init(int sample_rate) {
  g_ps.init(sample_rate);
  g_ps.set_param("lpf.fc", 10000.0f);
  g_ps.set_param("lc.pitch_ratio", 0.5f);
}

void pitch_shifter_audio_process(const float* in, float* out, int n) {
  g_ps.process_chunk(in, out, n);
}
