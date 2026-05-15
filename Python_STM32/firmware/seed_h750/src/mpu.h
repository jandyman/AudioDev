// mpu.h — Cortex-M7 MPU configuration
//
// The only reason the MPU exists in this project is the D-cache / DMA
// coherency problem on Cortex-M7: when the CPU writes a TX buffer and
// then tells DMA to send it, the write may still be in the D-cache line
// and the DMA will read stale memory. The fix used here is to place all
// DMA-visible buffers in a region of AXI SRAM that the MPU has marked
// Non-cacheable. The rest of the address space keeps its default (which
// for AXI SRAM includes the D-cache) via PRIVDEFENA.

#ifndef DAISY_CLAUDE_MPU_H
#define DAISY_CLAUDE_MPU_H

#ifdef __cplusplus
extern "C" {
#endif

// Disable the MPU, program region 0 to cover the linker's .dma_buffers
// section (base = ORIGIN(RAM_D1), size = 2 KB) as Normal / Non-cacheable
// / Shareable / XN / full access, then re-enable the MPU with the default
// map preserved (PRIVDEFENA=1) so everything else behaves as before.
//
// Safe to call with the D-cache already on; callers that have touched
// RAM_D1 before calling should clean + invalidate first, but at current
// use (first boot, nothing in RAM_D1 yet) that's not necessary.
void mpu_configure_dma_region(void);

#ifdef __cplusplus
}  // extern "C"
#endif

#endif  // DAISY_CLAUDE_MPU_H
