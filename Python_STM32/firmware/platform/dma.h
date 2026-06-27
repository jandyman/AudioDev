// dma.h — DMA1 configuration for SAI1 audio
//
// Two streams, both circular, one int32 word per transfer:
//   Stream 0: memory → SAI1_A->DR  (TX, DMAMUX request 87)
//   Stream 1: SAI1_B->DR → memory  (RX, DMAMUX request 88)
//
// HT and TC interrupts are enabled on Stream 1 only. Stream 0 runs silent —
// because the two streams share the same BCK/FS (sub-block B is synchronous
// slave to A), they stay in lockstep and one IRQ source is sufficient.

#ifndef DAISY_CLAUDE_DMA_H
#define DAISY_CLAUDE_DMA_H

#include <stdint.h>

// Program both DMA streams + their DMAMUX routing. The streams are left
// DISABLED; the caller (audio_init) sets DMAEN on the SAI sub-blocks and
// then enables the streams in the right order.
//
// `tx_buffer` / `rx_buffer` must live in the linker's .dma_buffers section
// (non-cacheable). `nwords` is the total int32 word count of each buffer
// (both halves combined); the DMA will circularly walk that length and
// HT/TC will fire at the mid and end points.
void dma_configure_audio(int32_t *tx_buffer, int32_t *rx_buffer,
                         uint32_t nwords);

#endif  // DAISY_CLAUDE_DMA_H
