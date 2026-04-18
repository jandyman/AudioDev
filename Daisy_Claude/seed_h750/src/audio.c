// audio.c — DMA-backed stereo passthrough via SAI1 + AK4556 (Daisy Seed Rev 4)
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
// of DMA Stream 1 (RX). On each event it copies one half-buffer of RX audio
// directly into the matching half of the TX buffer — stereo passthrough with
// zero processing. It also increments audio_irq_count and toggles the LED
// every 500 calls, so the 1 Hz blink from main() is replaced by a 1 Hz blink
// that is directly driven by DMA activity.

#include <stdbool.h>
#include <stdint.h>

// stm32h750xx.h sets __FPU_PRESENT/__MPU_PRESENT and includes core_cm7.h.
#include "stm32h750xx.h"

#include "audio.h"
#include "board.h"
#include "dma.h"
#include "gpio.h"
#include "mpu.h"
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
// Passthrough callback — copies one half-buffer from RX to TX.
// `offset` is 0 for the first half (HT), AUDIO_BLOCK_FRAMES*2 for the
// second half (TC). Both buffers are non-cacheable so no cache ops needed.
// ============================================================================
static void passthrough(uint32_t offset) __attribute__((unused));
static void passthrough(uint32_t offset) {
  const uint32_t n = AUDIO_BLOCK_FRAMES * 2U;  // stereo words per half
  for (uint32_t i = 0U; i < n; ++i) {
    tx_buffer[offset + i] = rx_buffer[offset + i];
  }
}

// ============================================================================
// TX diagnostic — writes a ~440 Hz sawtooth to tx_buffer (ignores rx_buffer).
// Amplitude ≈ 1/16 full scale of the 24-bit left-justified sample: audible
// but not loud. Lets us tell whether TX + codec DAC is alive independent of
// whether the ADC is delivering any data into rx_buffer.
// ============================================================================
static int32_t tone_phase = 0;
static void tone_test(uint32_t offset) {
  // step = 440 Hz * 2^32 / 48000 ≈ 0x258D1E  (32-bit accumulator wraps)
  const int32_t step = 39370534;
  for (uint32_t i = 0U; i < AUDIO_BLOCK_FRAMES; ++i) {
    int32_t s = tone_phase >> 4;               // ~1/16 full scale
    tx_buffer[offset + 2U * i + 0U] = s;       // L
    tx_buffer[offset + 2U * i + 1U] = s;       // R
    tone_phase += step;
  }
}

// ============================================================================
// DMA1 Stream 1 ISR — paces all audio processing.
// ============================================================================
void DMA1_Stream1_IRQHandler(void) {
  uint32_t isr = DMA1->LISR;

  if (isr & DMA_LISR_HTIF1) {
    DMA1->LIFCR = DMA_LIFCR_CHTIF1;
    tone_test(0U);                        // TX diagnostic (was passthrough)
  }

  if (isr & DMA_LISR_TCIF1) {
    DMA1->LIFCR = DMA_LIFCR_CTCIF1;
    tone_test(AUDIO_BLOCK_FRAMES * 2U);   // TX diagnostic (was passthrough)
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

  // Toggle LED every 500 IRQs → ~1 Hz at 1 kHz IRQ rate.
  if (audio_irq_count % 500U == 0U) {
    gpio_toggle(LED_USER_PORT, LED_USER_PIN);
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
