// Dual Tap Delay - Faust Implementation
// Single delay buffer with two independent read taps
// Uses high-quality interpolation for smooth modulation

import("stdfaust.lib");

// Maximum delay buffer size in milliseconds
max_delay_ms = 1000.0;  // 1 second buffer

// Convert max delay to samples at current sample rate
max_delay_samples = int(max_delay_ms * ma.SR / 1000.0);

// Dual tap delay: 3 inputs → 2 outputs
// Input 1: audio signal to delay
// Input 2: delay time in milliseconds for tap 1 (control signal)
// Input 3: delay time in milliseconds for tap 2 (control signal)
// Output 1: tap 1 (delayed audio)
// Output 2: tap 2 (delayed audio)
//
// Note: Both taps read from the SAME delay buffer, just at different positions
process(audio_in, delay1_ms, delay2_ms) = tap1, tap2
with {
    // Convert milliseconds to samples, clamp to valid range
    delay1_samples = delay1_ms * ma.SR / 1000.0 : max(0) : min(max_delay_samples);
    delay2_samples = delay2_ms * ma.SR / 1000.0 : max(0) : min(max_delay_samples);

    // Single delay buffer with two independent read taps
    // de.sdelay(maxDelay, interpolation, delayTime, input)
    // interpolation = 512 gives 9th order Lagrange interpolation (very smooth)
    // This is much better than Max's default linear interpolation
    tap1 = de.sdelay(max_delay_samples, 512, delay1_samples, audio_in);
    tap2 = de.sdelay(max_delay_samples, 512, delay2_samples, audio_in);
};
