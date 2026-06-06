#include "pitch_shifter_audio.h"
#include "pitch_shifter.h"
#include "stm32h750xx.h"
#include <math.h>

static pitch_shifter g_ps;

static volatile float g_in_peak  = 0.0f;
static volatile float g_out_peak = 0.0f;

void pitch_shifter_audio_init(int sample_rate) {
  g_ps.init(sample_rate);
  g_ps.set_param("lpf.fc", 10000.0f);
  g_ps.set_param("lc.pitch_ratio", 0.5f);
}

void pitch_shifter_audio_process(const float* in, float* out_l, float* out_r, int n) {
  float in_peak  = g_in_peak;
  float out_peak = g_out_peak;
  for (int i = 0; i < n; ++i) {
    float a = fabsf(in[i]);
    if (a > in_peak) in_peak = a;
  }
  const float* ins[]  = { in };
  float*       outs[] = { out_l, out_r };
  g_ps.process_chunk(ins, outs, n);
  for (int i = 0; i < n; ++i) {
    float a = fabsf(out_r[i]);
    if (a > out_peak) out_peak = a;
  }
  g_in_peak  = in_peak;
  g_out_peak = out_peak;
}

void pitch_shifter_peaks_read_and_clear(float* in_peak, float* out_peak) {
  uint32_t primask = __get_PRIMASK();
  __disable_irq();
  *in_peak   = g_in_peak;
  *out_peak  = g_out_peak;
  g_in_peak  = 0.0f;
  g_out_peak = 0.0f;
  __set_PRIMASK(primask);
}
