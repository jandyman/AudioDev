#pragma once
#ifdef __cplusplus
extern "C" {
#endif
void pitch_shifter_audio_init(int sample_rate);
void pitch_shifter_audio_process(const float* in, float* out, int n);
#ifdef __cplusplus
}
#endif
