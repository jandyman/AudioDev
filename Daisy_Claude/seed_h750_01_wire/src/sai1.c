// sai1.c — SAI1 bring-up for the PCM3060 codec on Daisy Seed Rev 7
//
// Target: stereo 48 kHz, 24-bit left-justified, 2 slots × 32-bit slot size,
// sub-block A = TX master (generates MCLK/BCK/FS), sub-block B = RX
// synchronous slave that shares A's clocks.
//
// Pin routing (see board.h; spec 01 §3):
//   PE2 = MCLK_A   → codec SCKI (12.288 MHz nominal)
//   PE3 = SD_B     ← codec DOUT (ADC → STM32)
//   PE4 = FS_A     → codec LRCK
//   PE5 = SCK_A    → codec BCK
//   PE6 = SD_A     → codec DIN  (STM32 → DAC)
// All five at alternate function AF6, very-high speed, no pull.
//
// Format-bit decisions (CKSTR, FSPOL, FSOFF, MCKDIV, MCKEN) are taken
// from ST's HAL SAI driver with protocol = SAI_I2S_MSBJUSTIFIED, since
// the HAL is the authoritative translation of the abstract protocol to
// the concrete register layout on H750 Rev V silicon. See the comment
// block on each register below for the derivation.
//
// This file deliberately avoids allocating handles or abstracting over
// sub-block A vs B — there's exactly one SAI1 on this chip, the two
// sub-blocks have different roles by design, and inline register writes
// are more auditable than a generic "configure one block" helper.

#include <stdbool.h>
#include <stdint.h>

#include "stm32h750xx.h"

#include "board.h"
#include "clock.h"
#include "gpio.h"
#include "sai1.h"

// ============================================================================
// CR1 field values (24-bit left-justified, 48 kHz, 2 slots)
//
// DS (data size):
//   110 = 24-bit (RM0433 §51.5.1, SAI_xCR1.DS bit field).
//   HAL macro SAI_DATASIZE_24 = DS_2 | DS_1.
//
// CKSTR (clock strobing):
//   HAL, for I2S protocols, sets ClockStrobing = FALLING_EDGE for TX and
//   RISING_EDGE for RX. Its write-path in HAL_SAI_Init then inverts the
//   polarity for the transmit branch (stm32h7xx_hal_sai.c:591-601), so
//   the bit that actually lands in CR1 is CKSTR = 1 for BOTH sub-blocks
//   in this mode. We mirror that.
//
// NODIV = 0 + MCKEN = 1 + MCKDIV = 4:
//   On H750 Rev V with MCKEN set, MCLK = SAI_kernel / MCKDIV. With
//   SAI_kernel = 49.167 MHz (PLL3P) and MCKDIV = 4 we get 12.29 MHz,
//   which is 256 × 48 kHz (≈300 ppm high; see spec 04 §10 decision #1).
//   This is exactly what HAL writes for SAI_AUDIO_FREQUENCY_48K on this
//   kernel clock and is empirically known-good from libDaisy.
// ============================================================================

#define SAI_MCKDIV_VALUE  4U

// --- Sub-block A: master TX, drives MCLK/BCK/FS ---
// Field-by-field, the bits we intend to have set in block A CR1:
//   MODE     = 00 (master TX)                  → 0
//   PRTCFG   = 00 (free protocol)              → 0
//   DS       = 110 (24-bit)                    → SAI_xCR1_DS_2 | SAI_xCR1_DS_1
//   LSBFIRST = 0 (MSB first)                   → 0
//   CKSTR    = 1 (per HAL, see block above)    → SAI_xCR1_CKSTR
//   SYNCEN   = 00 (async — we are the master)  → 0
//   MONO     = 0 (stereo)                      → 0
//   OUTDRIV  = 0 (SD driven only when SAIEN=1) → 0
//   SAIEN    = 0 (set last, after everything)  → 0
//   DMAEN    = 0 (enabled in sub-step 2b)      → 0
//   NODIV    = 0 (MCLK = kernel / MCKDIV)      → 0
//   MCKDIV   = 4                               → 4 << 20
//   OSR      = 0 (no MCLK oversampling)        → 0
//   MCKEN    = 1 (enable MCLK output on PE2)   → SAI_xCR1_MCKEN
#define SAIA_CR1_VALUE                                                     \
    ( SAI_xCR1_DS_2 | SAI_xCR1_DS_1                                        \
    | SAI_xCR1_CKSTR                                                       \
    | ((uint32_t)SAI_MCKDIV_VALUE << SAI_xCR1_MCKDIV_Pos)                  \
    | SAI_xCR1_MCKEN )

// --- Sub-block B: synchronous slave RX ---
//   MODE     = 11 (slave RX)                   → SAI_xCR1_MODE_1 | _MODE_0
//   SYNCEN   = 01 (sync with A, internal)      → SAI_xCR1_SYNCEN_0
//   DS/CKSTR = same as A
//   NODIV/MCKDIV/MCKEN = 0 (B never drives MCLK; it's a slave)
#define SAIB_CR1_VALUE                                                     \
    ( SAI_xCR1_MODE_1 | SAI_xCR1_MODE_0                                    \
    | SAI_xCR1_DS_2 | SAI_xCR1_DS_1                                        \
    | SAI_xCR1_CKSTR                                                       \
    | SAI_xCR1_SYNCEN_0 )

// --- FRCR (both sub-blocks, same frame format) ---
//   FRL   = 63 → 64-bit frame (two 32-bit slots)
//   FSALL = 31 → FS pulse is 32 bits wide (half-frame)
//   FSDEF = 1  → FS signals channel identification (stereo)
//   FSPOL = 1  → FS active high (LJ: LRCK high = left channel)
//   FSOFF = 0  → MSB on same cycle as FS edge (no 1-bit offset, LJ spec)
// Values are stored as (length - 1) in the register.
#define SAI_FRCR_VALUE                                                     \
    ( (63U << SAI_xFRCR_FRL_Pos)                                           \
    | (31U << SAI_xFRCR_FSALL_Pos)                                         \
    | SAI_xFRCR_FSDEF                                                      \
    | SAI_xFRCR_FSPOL )

// --- SLOTR (both sub-blocks, same slot layout) ---
//   FBOFF   = 0    → first data bit at offset 0 in the slot
//   SLOTSZ  = 10   → 32-bit slots (24-bit data MSB-aligned inside)
//   NBSLOT  = 1    → 2 slots total (stored as value - 1)
//   SLOTEN  = 0xFFFF → both active slots + all reserved slots enabled
//            (matches HAL's SAI_SLOTACTIVE_ALL; extra bits are no-ops
//             with NBSLOT=2 and are the documented HAL behavior)
#define SAI_SLOTR_VALUE                                                    \
    ( SAI_xSLOTR_SLOTSZ_1                                                  \
    | (1U << SAI_xSLOTR_NBSLOT_Pos)                                        \
    | (0xFFFFU << SAI_xSLOTR_SLOTEN_Pos) )

// ============================================================================
// GPIO: route PE2..PE6 to AF6 (SAI1). Very-high speed because BCK/MCLK
// can swing at ~12 MHz and we want clean edges. No pull — the codec pins
// are either driven (MCLK/BCK/FS/SD_A) or always driven by the codec
// (SD_B), so internal pulls would only fight the driver or waste power.
// ============================================================================
static void sai1_configure_pins(void) {
  gpio_enable_port(SAI1_PORT);

  gpio_configure_alternate(SAI1_PORT, SAI1_MCLK_A_PIN, SAI1_AF,
                           GPIO_SPEED_VERY_HIGH, GPIO_PULL_NONE);
  gpio_configure_alternate(SAI1_PORT, SAI1_SD_B_PIN,   SAI1_AF,
                           GPIO_SPEED_VERY_HIGH, GPIO_PULL_NONE);
  gpio_configure_alternate(SAI1_PORT, SAI1_FS_A_PIN,   SAI1_AF,
                           GPIO_SPEED_VERY_HIGH, GPIO_PULL_NONE);
  gpio_configure_alternate(SAI1_PORT, SAI1_SCK_A_PIN,  SAI1_AF,
                           GPIO_SPEED_VERY_HIGH, GPIO_PULL_NONE);
  gpio_configure_alternate(SAI1_PORT, SAI1_SD_A_PIN,   SAI1_AF,
                           GPIO_SPEED_VERY_HIGH, GPIO_PULL_NONE);
}

// ============================================================================
// Peripheral bring-up. Read-back verifies each important register after
// the write, so a silently-dropped write (or a CMSIS macro with the wrong
// bit layout for this silicon) turns into a visible fault at the LED.
// ============================================================================
bool sai1_configure(void) {
  sai1_configure_pins();

  // --- Enable SAI1 peripheral clock on APB2 ---
  RCC->APB2ENR |= RCC_APB2ENR_SAI1EN;
  (void)RCC->APB2ENR;  // read-back to ensure the write lands before any SAI access
  if ((RCC->APB2ENR & RCC_APB2ENR_SAI1EN) == 0U) {
    return false;
  }

  // --- Both sub-blocks must be disabled while we configure them ---
  SAI1_Block_A->CR1 &= ~SAI_xCR1_SAIEN;
  SAI1_Block_B->CR1 &= ~SAI_xCR1_SAIEN;
  while ((SAI1_Block_A->CR1 & SAI_xCR1_SAIEN) != 0U) { /* wait */ }
  while ((SAI1_Block_B->CR1 & SAI_xCR1_SAIEN) != 0U) { /* wait */ }

  // --- Sub-block A (TX master) ---
  SAI1_Block_A->CR1   = SAIA_CR1_VALUE;
  SAI1_Block_A->CR2   = 0U;                 // FIFO threshold=empty, no companding
  SAI1_Block_A->FRCR  = SAI_FRCR_VALUE;
  SAI1_Block_A->SLOTR = SAI_SLOTR_VALUE;

  // --- Sub-block B (RX sync slave) ---
  SAI1_Block_B->CR1   = SAIB_CR1_VALUE;
  SAI1_Block_B->CR2   = 0U;
  SAI1_Block_B->FRCR  = SAI_FRCR_VALUE;
  SAI1_Block_B->SLOTR = SAI_SLOTR_VALUE;

  // --- Read-back verification. Masks strip the SAIEN bit (which is still
  // 0 at this point on purpose) so we only compare the fields we wrote.
  if ((SAI1_Block_A->CR1   & ~SAI_xCR1_SAIEN) != SAIA_CR1_VALUE)   return false;
  if ((SAI1_Block_B->CR1   & ~SAI_xCR1_SAIEN) != SAIB_CR1_VALUE)   return false;
  if (SAI1_Block_A->FRCR  != SAI_FRCR_VALUE)  return false;
  if (SAI1_Block_B->FRCR  != SAI_FRCR_VALUE)  return false;
  if (SAI1_Block_A->SLOTR != SAI_SLOTR_VALUE) return false;
  if (SAI1_Block_B->SLOTR != SAI_SLOTR_VALUE) return false;

  return true;
}

// ============================================================================
// sai1_enable — arm both sub-blocks. Separated from sai1_configure() so that
// DMA can be configured (DMAEN set on both sub-blocks, DMA streams armed)
// between "registers programmed" and "clocks actually running". Enabling B
// first ensures it latches A's clocks from the very first frame.
// ============================================================================
bool sai1_enable(void) {
  SAI1_Block_B->CR1 |= SAI_xCR1_SAIEN;
  SAI1_Block_A->CR1 |= SAI_xCR1_SAIEN;

  if ((SAI1_Block_A->CR1 & SAI_xCR1_SAIEN) == 0U) return false;
  if ((SAI1_Block_B->CR1 & SAI_xCR1_SAIEN) == 0U) return false;

  return true;
}
