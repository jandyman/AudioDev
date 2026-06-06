#pragma once
#ifdef __cplusplus
extern "C" {
#endif
void pitch_shifter_audio_init(int sample_rate);
// Stereo output: out_l = dry (raw input passthrough), out_r = pitch-shifted.
// Matches the graph's two declared output ports (audio_out_l, audio_out_r).
void pitch_shifter_audio_process(const float* in, float* out_l, float* out_r, int n);

// Read peak |x| seen since the last call, then clear back to zero.
// Safe to call from foreground while audio runs (briefly disables IRQs).
// out_peak measures the shifted (right) channel.
void pitch_shifter_peaks_read_and_clear(float* in_peak, float* out_peak);
#ifdef __cplusplus
}
#endif
