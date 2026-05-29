#pragma once
#ifdef __cplusplus
extern "C" {
#endif
void pitch_shifter_audio_init(int sample_rate);
void pitch_shifter_audio_process(const float* in, float* out, int n);

// Read peak |x| seen since the last call, then clear back to zero.
// Safe to call from foreground while audio runs (briefly disables IRQs).
void pitch_shifter_peaks_read_and_clear(float* in_peak, float* out_peak);
#ifdef __cplusplus
}
#endif
