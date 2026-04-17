// sai1.h — SAI1 configuration for the PCM3060 codec
//
// See spec 04 §5. Sub-block A is the TX master (drives MCLK/BCK/FS and
// sends data to the DAC); sub-block B is a synchronous slave that shares
// A's clocks and receives ADC data. Frame is 2 slots × 32 bits, 24-bit
// left-justified audio, 48 kHz.
//
// This header is deliberately thin: the entire public API is one call.

#ifndef DAISY_CLAUDE_SAI1_H
#define DAISY_CLAUDE_SAI1_H

#include <stdbool.h>

// Route PE2..PE6 to AF6, enable the SAI1 peripheral clock, program both
// sub-blocks for 48 kHz / 24-bit LJ / stereo, and enable them (B first,
// then A). DMA is not configured here — that belongs to sub-step 2b. With
// DMA off, sub-block A will underrun continuously, but its master clocks
// still run cleanly on PE2/PE4/PE5, which is what we need to bring the
// codec out of its internal reset for later steps.
//
// Must be called after configure_sai1_clock() has returned true (PLL3P is
// the SAI1 kernel source).
//
// Returns true on success. Returns false if any register read-back does
// not match the value just written — a signal that either CMSIS macros
// are wrong for this device or a bus fault has silently dropped a write.
bool sai1_configure(void);

#endif  // DAISY_CLAUDE_SAI1_H
