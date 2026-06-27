// mpu.c — Cortex-M7 MPU region for DMA buffers
//
// Region 0 covers the 2 KB at the base of RAM_D1 (AXI SRAM, 0x24000000)
// that the linker allocates to .dma_buffers. Attributes:
//
//   TEX = 001, C = 0, B = 0, S = 1  → Normal, Non-cacheable, Shareable
//   AP  = 011                        → full access (priv + unpriv RW)
//   XN  = 1                          → execute never (this is data)
//   SIZE = 10                        → 2^(10+1) = 2048 bytes
//   ENABLE = 1
//
// The MPU is otherwise transparent: PRIVDEFENA = 1 in CTRL preserves the
// default memory map for every address not covered by an enabled region,
// so flash, DTCMRAM, the AHB peripherals, and the rest of AXI SRAM keep
// the same attributes they had before the MPU was turned on.
//
// Reference: ARMv7-M Architecture Reference Manual §B3.5 and CMSIS Cortex-M7
// core_cm7.h MPU_RASR / MPU_CTRL bit definitions.

#include <stdint.h>

// stm32h750xx.h sets __FPU_PRESENT/__MPU_PRESENT and then includes
// core_cm7.h. Pulling core_cm7.h in standalone would trigger its own
// #error for missing __FPU_PRESENT, so we include the device header only.
#include "stm32h750xx.h"

#include "mpu.h"

// Provided by the linker script (see .dma_buffers section). We only need
// the start symbol; the size is fixed at 2 KB to match the MPU SIZE field.
extern uint32_t _sdma_buffers;

#define MPU_REGION_DMA   0U
#define MPU_SIZE_2KB     10U   // 2 ^ (SIZE + 1) = 2048 bytes

void mpu_configure_dma_region(void) {
  // Memory barrier before touching MPU control — any pending memory
  // transactions complete under the current attributes.
  __DMB();

  MPU->CTRL = 0U;  // disable while reprogramming

  MPU->RNR  = MPU_REGION_DMA;
  MPU->RBAR = (uint32_t)&_sdma_buffers;  // 2 KB aligned (linker asserts this)
  MPU->RASR =
      (MPU_SIZE_2KB << MPU_RASR_SIZE_Pos)      // 2 KB
    | (0x1U << MPU_RASR_TEX_Pos)               // TEX = 001 → Normal mem
    | (0U   << MPU_RASR_C_Pos)                 // C = 0
    | (0U   << MPU_RASR_B_Pos)                 // B = 0   → Non-cacheable
    | (1U   << MPU_RASR_S_Pos)                 // S = 1   → Shareable
    | (0x3U << MPU_RASR_AP_Pos)                // AP = 011 → full access
    | MPU_RASR_XN_Msk                          // execute never
    | MPU_RASR_ENABLE_Msk;

  // Enable MPU. PRIVDEFENA keeps the default memory map live for any
  // address not covered by an enabled region. HFNMIENA left 0 — we do
  // not want MPU checks during HardFault / NMI.
  MPU->CTRL = MPU_CTRL_PRIVDEFENA_Msk | MPU_CTRL_ENABLE_Msk;

  __DSB();  // ensure MPU update is visible before any following access
  __ISB();  // flush the pipeline so the new attributes apply
}
