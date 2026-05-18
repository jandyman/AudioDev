// audio.h — DMA-driven audio passthrough for the PCM3060 codec
//
// Owns the TX/RX DMA buffers and the DMA1_Stream1 IRQ handler. The IRQ
// fires at half-transfer and transfer-complete, giving a ~1 ms callback
// at 48 kHz with 48-frame blocks. The callback does stereo passthrough
// (rx → tx) — the first proof that audio is flowing end-to-end.
//
// Verification: audio_irq_count is incremented on every callback. At
// ~1 kHz rate, the LED toggles every 500 counts, producing a 1 Hz blink
// that is directly driven by DMA activity (not by delay_ms).

#ifndef DAISY_CLAUDE_AUDIO_H
#define DAISY_CLAUDE_AUDIO_H

#include <stdbool.h>
#include <stdint.h>

// Sample rate in Hz — must match the PLL3 / MCKDIV configuration in sai1.c.
#define AUDIO_SAMPLE_RATE  48000.0f

// Number of stereo frames per half-buffer (one callback's worth of audio).
#define AUDIO_BLOCK_FRAMES  48U

// Total int32 words in each buffer: 2 halves × AUDIO_BLOCK_FRAMES × 2 ch.
#define AUDIO_BUFFER_WORDS  (2U * AUDIO_BLOCK_FRAMES * 2U)  // 192

// Monotonic count of audio callback invocations. Wraps at UINT32_MAX.
// Read from main() to verify DMA is alive.
extern volatile uint32_t audio_irq_count;

// Set PB11 low (PCM3060 deemphasis disable), configure MPU non-cacheable
// region, program DMA1, set SAI1 DMAEN, arm DMA streams, register the
// NVIC IRQ, and call sai1_enable() to start the clocks.
//
// Returns true on success. Returns false if the SAI sub-blocks fail to
// report SAIEN=1 after enable (sai1_enable() returned false).
bool audio_init(void);

#endif  // DAISY_CLAUDE_AUDIO_H
