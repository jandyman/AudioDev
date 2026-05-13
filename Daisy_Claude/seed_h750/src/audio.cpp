// audio.cpp — DMA-backed stereo passthrough via SAI1 + AK4556 (Daisy Seed Rev 4)
//
// Sequence (called once from main after sai1_configure() succeeds):
//   1. PB11 pulse — AK4556 RST line. Drive high, 1 ms, low, 1 ms, high.
//                  (Rev 4 uses AK4556, not PCM3060; PB11 is codec reset.)
//   2. MPU       — marks .dma_buffers non-cacheable (D-cache coherency)
//   3. DMA       — programs Stream 0 (TX) + Stream 1 (RX), circular, no enable
//   4. SAI DMAEN — turns on DMAEN in both sub-block CR1 (must be done while
//                  SAIEN=0, which sai1_configure() guarantees)
//   5. Streams   — enable TX first so SAI_A's internal FIFO has data before
//                  BCK starts, then enable RX
//   6. NVIC      — enable DMA1_Stream1_IRQn at highest user priority (0,0)
//   7. sai1_enable() — sets SAIEN on B then A; clocks start running
//
// The IRQ handler runs on every HT (half-transfer) and TC (transfer-complete)
// of DMA Stream 1 (RX). On each event it runs process_audio() for the
// appropriate half-buffer (rx → eq → tx) and increments audio_irq_count.
//
// The IRQ does NOT touch the LED. The LED is driven by a SoftwareTimer in
// main()'s foreground loop, which means a steady blink proves the main loop
// is alive (and SysTick is ticking). audio_irq_count is left as a debugger-
// readable "is DMA still firing?" indicator.

#include <stdbool.h>
#include <stdint.h>

// stm32h750xx.h sets __FPU_PRESENT/__MPU_PRESENT and includes core_cm7.h.
#include "stm32h750xx.h"

#include "audio.h"
#include "board.h"
#include "dma.h"
#include "eq.h"
#include "gpio.h"
#include "mpu.h"
#include "params.h"
#include "sai1.h"
#include "systick.h"

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
// them while the program runs freely. Halt in CubeIDE, then inspect in the
// Expressions or Variables view.
//
// Interpretation:
//   dbg_s0_ndtr  — Stream 0 NDTR. Should count DOWN from 192 toward 0 then
//                  wrap (circular mode). If stuck at 192, TX DMA never ran.
//   dbg_s0_cr    — Stream 0 CR. Bit 0 (EN) must be 1.
//   dbg_s1_ndtr  — Stream 1 NDTR. Same counting behavior for RX.
//   dbg_sai_a_sr — SAI_A status. Bit 0 = OVRUDR (set = TX underrun happened).
//                  Bit 3:2 = FLVL (FIFO level). Bits 6 = FREQ (req level).
//   dbg_sai_b_sr — SAI_B status. Same shape; OVRUDR = RX overrun here.
//   dbg_sai_a_cr1/cr2, dbg_sai_b_cr1/cr2 — useful to confirm SAIEN, DMAEN,
//                  MUTE, FTH after the hardware has been running a while.
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
// process_audio — one half-buffer of stereo audio through the EQ chain.
//
// Data format: SAI with DS=24, SLOTSZ=32 packs the 24-bit sample into the
// LOW 24 bits of each FIFO word (right-justified). bits [31:24] are not
// guaranteed to be sign-extended, so we do it ourselves in s242f. On TX
// the SAI transmits the low 24 bits and ignores the upper 8.
// This matches libDaisy's s242f/f2s24 — see DaisyExamples/libDaisy/src/
// daisy_core.h.
// ============================================================================

// Signed 24-bit (in low 24 bits of int32) → float in [-1, 1).
// XOR-trick sign-extends bit 23 to bits [31:24] without C UB.
static inline __attribute__((always_inline)) float s242f(int32_t x) {
  x = (x ^ 0x800000) - 0x800000;
  return (float)x * (1.0f / 8388608.0f);
}

// Float → signed 24-bit (in low 24 bits of int32). Clamps to avoid the
// boundary case where x*8388608 == 8388608 wraps to -8388608 in 24-bit.
static inline __attribute__((always_inline)) int32_t f2s24(float x) {
  if (x < -0.999985f) x = -0.999985f;
  if (x >  0.999985f) x =  0.999985f;
  return (int32_t)(x * 8388608.0f);
}

static void process_audio(uint32_t offset) {
  // If the foreground has staged new coefficients (READY = bit 1), commit
  // them into the live filters and clear both flags so the host can write
  // again. apply_new_coefficients() only touches the BiquadCoeffs fields —
  // delay-line state in each filter is preserved, so there is no click.
  if (params_dirty_flag.flags & PARAMS_DIRTY_BIT_READY) {
    eq_apply_new_coefficients();
    params_dirty_flag.flags = 0U;
  }

  for (uint32_t i = 0U; i < AUDIO_BLOCK_FRAMES; ++i) {
    const uint32_t base = offset + i * 2U;

    float l = s242f(rx_buffer[base]);
    float r = s242f(rx_buffer[base + 1]);

    l = eq_ch[0].process(l);
    r = eq_ch[1].process(r);

    tx_buffer[base]     = f2s24(l);
    tx_buffer[base + 1] = f2s24(r);
  }
}

// ============================================================================
// DMA1 Stream 1 ISR — paces all audio processing.
//
// extern "C" so the symbol the linker resolves matches the weak alias in
// startup_stm32h750.s (which expects unmangled C names). Without this, the
// IRQ would silently dispatch to Default_Handler and audio would never run.
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

  // Transfer error — clear the flag. The LED will freeze (IRQs stop) if
  // DMA halts on error, which is a visible fault indication.
  if (isr & DMA_LISR_TEIF1) {
    DMA1->LIFCR = DMA_LIFCR_CTEIF1;
  }

  ++audio_irq_count;

  // Snapshot every 100 IRQs (~100 ms) so a debugger halt gives a fresh read.
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
  // --- 1. Pulse AK4556 RST on PB11 (Daisy Seed Rev 4, not Rev 7!) ---
  // libDaisy Ak4556::Init sequence: drive high, 1 ms, low, 1 ms, high.
  // Reset is released BEFORE the SAI clocks start; the AK4556 latches onto
  // BCK/LRCK when they come up.
  //
  // NOTE: the project comments/spec still say "PCM3060 / Rev 7 / DE_B".
  // That was wrong — this board is Rev 4 with an AK4556 codec. PB11 is
  // the codec RESET line (active low), and the previous `gpio_write(..,false)`
  // here was holding the codec in reset — which is why no audio flowed.
  gpio_enable_port(GPIOB);
  gpio_set_mode(GPIOB, 11U, GPIO_MODE_OUTPUT_PP);
  gpio_write(GPIOB, 11U, true);
  delay_ms(1U);
  gpio_write(GPIOB, 11U, false);
  delay_ms(1U);
  gpio_write(GPIOB, 11U, true);

  // --- 2. MPU: mark .dma_buffers non-cacheable ---
  mpu_configure_dma_region();

  // --- 3. DMA: program both streams (not enabled yet) ---
  dma_configure_audio(tx_buffer, rx_buffer, AUDIO_BUFFER_WORDS);

  // --- 4. SAI DMAEN: set before SAIEN (RM0433 §51.4.14) ---
  SAI1_Block_A->CR1 |= SAI_xCR1_DMAEN;
  SAI1_Block_B->CR1 |= SAI_xCR1_DMAEN;

  // --- 5. Enable DMA streams ---
  // TX first so SAI_A's internal FIFO is loaded with zeros before SAIEN
  // starts BCK. This prevents a garbage burst on the codec's DIN line.
  DMA1_Stream0->CR |= DMA_SxCR_EN;
  DMA1_Stream1->CR |= DMA_SxCR_EN;

  // --- 6. NVIC: DMA1_Stream1_IRQn, pre-emption priority 0, sub-priority 0 ---
  // Priority group default (PRIGROUP=0) on H7 gives 4 pre-emption bits.
  // Priority 0 is the highest available to non-fault exceptions.
  NVIC_SetPriority(DMA1_Stream1_IRQn, 0U);
  NVIC_EnableIRQ(DMA1_Stream1_IRQn);

  // --- 7. Start the clocks ---
  return sai1_enable();
}
