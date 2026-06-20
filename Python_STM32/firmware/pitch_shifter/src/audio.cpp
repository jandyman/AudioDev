// audio.cpp — DMA-backed stereo passthrough via SAI1 + AK4556 (Daisy Seed Rev 4)
//
// Chunk-based version for the pitch_shifter graph. The DMA ISR collects
// AUDIO_BLOCK_FRAMES (48) stereo int32 samples per half-buffer, converts the
// left channel to float, calls pitch_shifter_audio_process(), and writes the
// two output channels: left = dry input, right = pitch-shifted.

#include <stdbool.h>
#include <stdint.h>

#include "stm32h750xx.h"

#include "audio.h"
#include "audio_graph_runner.h"
#include "board.h"
#include "dma.h"
#include "gpio.h"
#include "mpu.h"
#include "sai1.h"
#include "systick.h"

// The generated graph header supplies the canonical `audio_graph` type and its
// kNumInputs/kNumOutputs, used to fan the SAI's stereo frames in/out generically.
#include AUDIO_GRAPH_HEADER

// ============================================================================
// DMA buffers — must live in .dma_buffers (non-cacheable, see mpu.c).
// Each buffer holds 2 half-blocks so HT fires after the first half is
// complete and TC fires after the second. Format: interleaved L/R int32.
// ============================================================================
static int32_t tx_buffer[AUDIO_BUFFER_WORDS]
    __attribute__((section(".dma_buffers"), aligned(32)));

static int32_t rx_buffer[AUDIO_BUFFER_WORDS]
    __attribute__((section(".dma_buffers"), aligned(32)));

volatile uint32_t audio_irq_count = 0U;

// ---------------------------------------------------------------------------
// Debug snapshots — sampled from the IRQ handler so the debugger can read
// them while the program runs freely.
// ---------------------------------------------------------------------------
volatile uint32_t dbg_s0_ndtr   = 0U;
volatile uint32_t dbg_s0_cr     = 0U;
volatile uint32_t dbg_s1_ndtr   = 0U;
volatile uint32_t dbg_s1_cr     = 0U;
volatile uint32_t dbg_sai_a_sr  = 0U;
volatile uint32_t dbg_sai_b_sr  = 0U;
volatile uint32_t dbg_sai_a_cr1 = 0U;
volatile uint32_t dbg_sai_a_cr2 = 0U;
volatile uint32_t dbg_sai_b_cr1 = 0U;
volatile uint32_t dbg_sai_b_cr2 = 0U;

// ============================================================================
// Sample conversion helpers
//
// Data format: SAI with DS=24, SLOTSZ=32 packs the 24-bit sample into the
// LOW 24 bits of each FIFO word (right-justified). bits [31:24] are not
// guaranteed to be sign-extended, so we do it ourselves in s242f. On TX
// the SAI transmits the low 24 bits and ignores the upper 8.
// ============================================================================

// Signed 24-bit (in low 24 bits of int32) -> float in [-1, 1).
static inline __attribute__((always_inline)) float s242f(int32_t x) {
  x = (x ^ 0x800000) - 0x800000;
  return (float)x * (1.0f / 8388608.0f);
}

// Float -> signed 24-bit (in low 24 bits of int32). Clamps to avoid wrap.
static inline __attribute__((always_inline)) int32_t f2s24(float x) {
  if (x < -0.999985f) x = -0.999985f;
  if (x >  0.999985f) x =  0.999985f;
  return (int32_t)(x * 8388608.0f);
}

// ============================================================================
// process_audio — one half-buffer through the graph, channel-agnostic.
//
// The SAI carries 2 interleaved channels; the graph declares kNumInputs /
// kNumOutputs. We fan the SAI's left channel into graph input 0 (and further
// SAI channels into further inputs if the graph has them), run the chunk, then
// write graph outputs back to the 2 SAI channels (output 0 -> L, 1 -> R; a
// 1-output graph is duplicated to both). For the pitch shifter: 1 in, 2 out
// (out0 = dry L, out1 = shifted R) — identical to before, now derived.
// ============================================================================
static void process_audio(uint32_t offset) {
  constexpr int NI = audio_graph::kNumInputs;
  constexpr int NO = audio_graph::kNumOutputs;
  constexpr int SAI_CH = 2;

  float inbuf[NI][AUDIO_BLOCK_FRAMES];
  float outbuf[NO][AUDIO_BLOCK_FRAMES];
  const float* ins[NI];
  float*       outs[NO];
  for (int c = 0; c < NI; ++c) ins[c]  = inbuf[c];
  for (int c = 0; c < NO; ++c) outs[c] = outbuf[c];

  for (uint32_t i = 0U; i < AUDIO_BLOCK_FRAMES; ++i)
    for (int c = 0; c < NI; ++c)
      inbuf[c][i] = s242f(rx_buffer[offset + i * 2U + (c < SAI_CH ? c : 0)]);

  audio_graph_process(ins, outs, AUDIO_BLOCK_FRAMES);

  for (uint32_t i = 0U; i < AUDIO_BLOCK_FRAMES; ++i)
    for (int ch = 0; ch < SAI_CH; ++ch) {
      int g = (ch < NO) ? ch : NO - 1;   // fewer graph outs -> duplicate last
      tx_buffer[offset + i * 2U + ch] = f2s24(outbuf[g][i]);
    }
}

// ============================================================================
// DMA1 Stream 1 ISR — paces all audio processing.
// ============================================================================
extern "C" void DMA1_Stream1_IRQHandler(void) {
  uint32_t isr = DMA1->LISR;

  if (isr & DMA_LISR_HTIF1) {
    DMA1->LIFCR = DMA_LIFCR_CHTIF1;
    process_audio(0U);
  }

  if (isr & DMA_LISR_TCIF1) {
    DMA1->LIFCR = DMA_LIFCR_CTCIF1;
    process_audio(AUDIO_BLOCK_FRAMES * 2U);
  }

  if (isr & DMA_LISR_TEIF1) {
    DMA1->LIFCR = DMA_LIFCR_CTEIF1;
  }

  ++audio_irq_count;

  if (audio_irq_count % 100U == 0U) {
    dbg_s0_ndtr   = DMA1_Stream0->NDTR;
    dbg_s0_cr     = DMA1_Stream0->CR;
    dbg_s1_ndtr   = DMA1_Stream1->NDTR;
    dbg_s1_cr     = DMA1_Stream1->CR;
    dbg_sai_a_sr  = SAI1_Block_A->SR;
    dbg_sai_b_sr  = SAI1_Block_B->SR;
    dbg_sai_a_cr1 = SAI1_Block_A->CR1;
    dbg_sai_a_cr2 = SAI1_Block_A->CR2;
    dbg_sai_b_cr1 = SAI1_Block_B->CR1;
    dbg_sai_b_cr2 = SAI1_Block_B->CR2;
  }
}

// ============================================================================
// audio_init — arms everything and starts the clocks.
// ============================================================================
bool audio_init(void) {
  // Pulse AK4556 RST on PB11 (Daisy Seed Rev 4).
  gpio_enable_port(GPIOB);
  gpio_set_mode(GPIOB, 11U, GPIO_MODE_OUTPUT_PP);
  gpio_write(GPIOB, 11U, true);
  delay_ms(1U);
  gpio_write(GPIOB, 11U, false);
  delay_ms(1U);
  gpio_write(GPIOB, 11U, true);

  mpu_configure_dma_region();
  dma_configure_audio(tx_buffer, rx_buffer, AUDIO_BUFFER_WORDS);

  SAI1_Block_A->CR1 |= SAI_xCR1_DMAEN;
  SAI1_Block_B->CR1 |= SAI_xCR1_DMAEN;

  DMA1_Stream0->CR |= DMA_SxCR_EN;
  DMA1_Stream1->CR |= DMA_SxCR_EN;

  NVIC_SetPriority(DMA1_Stream1_IRQn, 0U);
  NVIC_EnableIRQ(DMA1_Stream1_IRQn);

  return sai1_enable();
}
