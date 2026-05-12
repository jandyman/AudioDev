// dma.c — DMA1 Stream 0 / Stream 1 for SAI1 audio
//
// On H750, DMA1 + DMA2 peripheral requests are routed through DMAMUX1.
// The old F4-style CHSEL field in DMA_SxCR is unused — we just write the
// request ID into DMAMUX1_Channel{N}->CCR. Request IDs (RM0433 Table 121):
//
//   SAI1_A = 87    (TX, memory → peripheral)
//   SAI1_B = 88    (RX, peripheral → memory)
//
// Transfer width: both PSIZE and MSIZE are 32-bit words. SAI1's data
// register is 32 bits, and the codec frame is 2 × 32-bit slots, so one
// DMA word = one audio sample. With 48 kHz stereo the DMA request rate
// is 96 kHz on each stream — well under DMA1's budget.
//
// FIFO is left in direct mode (FCR = 0): every DMA request transfers
// immediately, no burst coalescing. Simple and known-good for audio.
//
// Both streams run circular with the full buffer length. On the RX
// stream, HTIE + TCIE fire the half-done / done interrupts that pace the
// audio callback. TEIE on both streams catches a bus/config fault.

#include <stdint.h>

#include "stm32h750xx.h"

#include "dma.h"

// ---- DMAMUX request IDs for SAI1 (RM0433 §17.3 Table 121) ----
#define DMAMUX_REQ_SAI1_A   87U
#define DMAMUX_REQ_SAI1_B   88U

// ---- Clear-flag masks for DMA1 LIFCR (covers streams 0..3) ----
// Stream 0 flags live in bits 5:0 ; Stream 1 flags in bits 11:6.
#define DMA_LIFCR_CLEAR_S0  (DMA_LIFCR_CTCIF0 | DMA_LIFCR_CHTIF0 \
                           | DMA_LIFCR_CTEIF0 | DMA_LIFCR_CDMEIF0 \
                           | DMA_LIFCR_CFEIF0)
#define DMA_LIFCR_CLEAR_S1  (DMA_LIFCR_CTCIF1 | DMA_LIFCR_CHTIF1 \
                           | DMA_LIFCR_CTEIF1 | DMA_LIFCR_CDMEIF1 \
                           | DMA_LIFCR_CFEIF1)

void dma_configure_audio(int32_t *tx_buffer, int32_t *rx_buffer,
                         uint32_t nwords) {
  // --- Enable DMA1 peripheral clock (DMAMUX1 is clocked alongside the DMAs) ---
  RCC->AHB1ENR |= RCC_AHB1ENR_DMA1EN;
  (void)RCC->AHB1ENR;  // read-back to ensure write lands before DMA access

  // --- Stream 0 must be disabled before we touch its config. EN=0 is not
  // instant — the stream may take a few cycles to stop after a TX burst. ---
  DMA1_Stream0->CR &= ~DMA_SxCR_EN;
  while ((DMA1_Stream0->CR & DMA_SxCR_EN) != 0U) { /* wait */ }
  DMA1_Stream1->CR &= ~DMA_SxCR_EN;
  while ((DMA1_Stream1->CR & DMA_SxCR_EN) != 0U) { /* wait */ }

  // Clear any leftover flags (HT/TC/TE/DME/FE) so the first real event
  // after enable is a clean one. These bits are write-1-to-clear.
  DMA1->LIFCR = DMA_LIFCR_CLEAR_S0 | DMA_LIFCR_CLEAR_S1;

  // --- DMAMUX routing ---
  DMAMUX1_Channel0->CCR = DMAMUX_REQ_SAI1_A;  // DMA1 Stream 0 = SAI1_A (TX)
  DMAMUX1_Channel1->CCR = DMAMUX_REQ_SAI1_B;  // DMA1 Stream 1 = SAI1_B (RX)

  // ============================================================
  // Stream 0 — memory → SAI1_A->DR (TX)
  //   DIR    = 01  (M2P)
  //   CIRC   = 1   (wrap NDTR continuously)
  //   MINC   = 1   (walk the buffer)
  //   PINC   = 0   (DR is fixed)
  //   PSIZE  = 10  (32-bit word)
  //   MSIZE  = 10  (32-bit word)
  //   PL     = 11  (very high priority — audio must not starve)
  //   TEIE   = 1   (transfer error IRQ, just in case)
  //   HTIE/TCIE = 0 (quiet stream — the RX stream drives callbacks)
  // ============================================================
  DMA1_Stream0->PAR  = (uint32_t)&SAI1_Block_A->DR;
  DMA1_Stream0->M0AR = (uint32_t)tx_buffer;
  DMA1_Stream0->NDTR = nwords;
  DMA1_Stream0->FCR  = 0U;  // direct mode (FIFO bypass)
  DMA1_Stream0->CR   =
      (0x1U << DMA_SxCR_DIR_Pos)        // memory → peripheral
    | DMA_SxCR_CIRC                      // circular
    | DMA_SxCR_MINC                      // memory increment
    | (0x2U << DMA_SxCR_PSIZE_Pos)      // peripheral 32-bit
    | (0x2U << DMA_SxCR_MSIZE_Pos)      // memory     32-bit
    | (0x3U << DMA_SxCR_PL_Pos)         // priority very high
    | DMA_SxCR_TEIE;                     // transfer error IRQ

  // ============================================================
  // Stream 1 — SAI1_B->DR → memory (RX)
  //   DIR    = 00  (P2M)
  //   CIRC   = 1
  //   MINC   = 1, PINC = 0, PSIZE/MSIZE = 10
  //   PL     = 11
  //   HTIE   = 1   (half-transfer: first half of buffer ready)
  //   TCIE   = 1   (transfer-complete: second half ready, wrapping)
  //   TEIE   = 1
  // ============================================================
  DMA1_Stream1->PAR  = (uint32_t)&SAI1_Block_B->DR;
  DMA1_Stream1->M0AR = (uint32_t)rx_buffer;
  DMA1_Stream1->NDTR = nwords;
  DMA1_Stream1->FCR  = 0U;
  DMA1_Stream1->CR   =
      (0x0U << DMA_SxCR_DIR_Pos)        // peripheral → memory
    | DMA_SxCR_CIRC
    | DMA_SxCR_MINC
    | (0x2U << DMA_SxCR_PSIZE_Pos)
    | (0x2U << DMA_SxCR_MSIZE_Pos)
    | (0x3U << DMA_SxCR_PL_Pos)
    | DMA_SxCR_HTIE
    | DMA_SxCR_TCIE
    | DMA_SxCR_TEIE;

  // Streams stay disabled here. audio_init() turns them on in the right
  // order: TX first (so the SAI's TX FIFO is loaded before BCK starts
  // clocking data out), then RX, then SAI sub-blocks.
}
