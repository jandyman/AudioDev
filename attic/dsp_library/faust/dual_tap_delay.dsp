// Dual Tap Delay - Faust Implementation
// Single shared delay buffer with two independent read taps
// Uses 4th-order Lagrange interpolation for smooth modulation

import("stdfaust.lib");

// Maximum delay buffer size
// Fixed at 1920000 samples to support up to 10 seconds at 192kHz
// (or ~40 seconds at 48kHz, ~43 seconds at 44.1kHz)
max_delay_samples = 1920000;
max_delay_ms = 10000.0;  // Maximum useful delay in milliseconds

// Dual tap delay: 3 inputs → 2 outputs
// Input 1: audio signal to delay
// Input 2: delay time in milliseconds for tap 1 (control signal)
// Input 3: delay time in milliseconds for tap 2 (control signal)
// Output 1: tap 1 (delayed audio)
// Output 2: tap 2 (delayed audio)
//
// Both taps read from a SINGLE shared delay buffer at different positions.
// This is more memory-efficient than separate buffers per tap.

process(audio_in, delay1_ms, delay2_ms) = tap1, tap2
with {
    // Convert milliseconds to samples, clamp to valid range
    delay1_samples = delay1_ms * ma.SR / 1000.0 : max(0) : min(max_delay_samples - 1);
    delay2_samples = delay2_ms * ma.SR / 1000.0 : max(0) : min(max_delay_samples - 1);

    // Write index: continuously incrementing counter (wraps via modulo in buffer access)
    write_idx = (+(1) ~ _);

    // Shared delay buffer: single write, multiple reads
    // Pattern from Faust granulator examples - one rwtable definition, multiple read positions
    buffer(rd) = rwtable(max_delay_samples, 0.0, write_idx % max_delay_samples, audio_in, rd % max_delay_samples);

    // Read with 4th-order Lagrange interpolation for fractional delays
    // Reads 4 adjacent samples and interpolates using Lagrange polynomial
    // Sample positions: v0 at rd_pos+1, v1 at rd_pos, v2 at rd_pos-1, v3 at rd_pos-2
    // Interpolation point d is in [0,1) between v1 and v2
    read_interp(delay_samps) = v0*L0 + v1*L1 + v2*L2 + v3*L3
    with {
        rd_pos = write_idx - int(delay_samps);
        d = ma.frac(delay_samps);

        // Read 4 samples centered around interpolation point
        v0 = buffer(rd_pos + 1);
        v1 = buffer(rd_pos);
        v2 = buffer(rd_pos - 1);
        v3 = buffer(rd_pos - 2);

        // 4-point Lagrange basis polynomials
        // Points at x = -1, 0, 1, 2; interpolate at x = d where d in [0,1)
        // L_i(d) = product over j!=i of (d - x_j) / (x_i - x_j)
        L0 = (d * (d-1) * (d-2)) / ((-1)*(-2)*(-3));       // = -d(d-1)(d-2)/6
        L1 = ((d+1) * (d-1) * (d-2)) / ((1)*(-1)*(-2));    // = (d+1)(d-1)(d-2)/2
        L2 = ((d+1) * d * (d-2)) / ((2)*(1)*(-1));         // = -(d+1)d(d-2)/2
        L3 = ((d+1) * d * (d-1)) / ((3)*(2)*(1));          // = (d+1)d(d-1)/6
    };

    tap1 = read_interp(delay1_samples);
    tap2 = read_interp(delay2_samples);
};
