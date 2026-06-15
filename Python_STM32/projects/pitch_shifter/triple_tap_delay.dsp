/* @block
(define-block triple_tap_delay
 (inputs audio_in delay1_ms delay2_ms delay3_ms)
 (outputs tap1 tap2 tap3))
*/

// Triple tap delay — one shared delay buffer, three independent fractional read
// taps (4th-order Lagrange interpolation). Doc: triple_tap_delay.md.

import("stdfaust.lib");

// Maximum delay buffer size (300 ms at 48 kHz).
max_delay_samples = 14400;
max_delay_ms = 300.0;

process(audio_in, delay1_ms, delay2_ms, delay3_ms) = tap1, tap2, tap3
with {
    // Convert milliseconds to samples, clamp to valid range
    delay1_samples = delay1_ms * ma.SR / 1000.0 : max(0) : min(max_delay_samples - 1);
    delay2_samples = delay2_ms * ma.SR / 1000.0 : max(0) : min(max_delay_samples - 1);
    delay3_samples = delay3_ms * ma.SR / 1000.0 : max(0) : min(max_delay_samples - 1);

    // Write index: continuously incrementing counter (wraps via modulo in buffer access)
    write_idx = (+(1) ~ _);

    // Shared delay buffer: single write, multiple reads
    buffer(rd) = rwtable(max_delay_samples, 0.0, write_idx % max_delay_samples, audio_in, rd % max_delay_samples);

    // Read with 4th-order Lagrange interpolation for fractional delays.
    // Sample positions: v0 at rd_pos+1, v1 at rd_pos, v2 at rd_pos-1, v3 at rd_pos-2.
    // Interpolation point d is in [0,1) between v1 and v2.
    read_interp(delay_samps) = v0*L0 + v1*L1 + v2*L2 + v3*L3
    with {
        rd_pos = write_idx - int(delay_samps);
        d = ma.frac(delay_samps);

        v0 = buffer(rd_pos + 1);
        v1 = buffer(rd_pos);
        v2 = buffer(rd_pos - 1);
        v3 = buffer(rd_pos - 2);

        // 4-point Lagrange basis polynomials at x = -1, 0, 1, 2; evaluated at x = d.
        L0 = (d * (d-1) * (d-2)) / ((-1)*(-2)*(-3));       // = -d(d-1)(d-2)/6
        L1 = ((d+1) * (d-1) * (d-2)) / ((1)*(-1)*(-2));    // = (d+1)(d-1)(d-2)/2
        L2 = ((d+1) * d * (d-2)) / ((2)*(1)*(-1));         // = -(d+1)d(d-2)/2
        L3 = ((d+1) * d * (d-1)) / ((3)*(2)*(1));          // = (d+1)d(d-1)/6
    };

    tap1 = read_interp(delay1_samples);
    tap2 = read_interp(delay2_samples);
    tap3 = read_interp(delay3_samples);
};
