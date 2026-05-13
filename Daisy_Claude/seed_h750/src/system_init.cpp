// system_init.cpp — Cortex-M7 core bring-up for STM32H750
//
// Called from Reset_Handler (startup_stm32h750.s) after .data copy and .bss
// zero, before main(). Gets the core out of its reset-default state and into
// "full speed, caches on, vector table wired up" condition.
//
// Sequence:
//   1. Enable the FPU so C code can use float/double safely.
//   2. Point VTOR at our vector table in flash (0x08000000).
//   3. Invalidate and enable I-cache and D-cache.
//   4. Configure the clock tree → 480 MHz SYSCLK (delegated to clock.c).
//
// No return value — falls through to Reset_Handler which then calls main().

#include "stm32h750xx.h"
#include "core_cm7.h"

#include "clock.h"

// Linker-script symbol: start of the vector table in flash (0x08000000).
// extern "C" so g_pfnVectors stays unmangled — the symbol is defined in
// startup_stm32h750.s, which only emits C names.
extern "C" uint32_t g_pfnVectors;

// extern "C" so the linker matches the bl-from-startup target. The .s file
// emits `bl SystemInit`, expecting a C symbol of that exact name.
extern "C" void SystemInit(void) {
  // --- 1. FPU: grant CP10/CP11 full access (privileged + user) ---
  // Cortex-M7 TRM §7.3.3 (CPACR). Bits [23:20] = 0b1111 → full access.
  // Must be done before any FP instruction executes, otherwise a
  // NOCP UsageFault fires on first use.
  SCB->CPACR |= ((3UL << 20U) | (3UL << 22U));
  __DSB();
  __ISB();

  // --- 2. VTOR: relocate vector table to our .isr_vector address ---
  // After reset, VTOR = 0; on boot from flash the core happens to see our
  // vectors at 0x08000000 via the alias at 0x00000000, but writing VTOR
  // explicitly is the right thing to do and matches what a debugger
  // expects. RM0433 §B3.2.5.
  SCB->VTOR = (uint32_t)&g_pfnVectors;
  __DSB();

  // --- 3. Caches: invalidate, then enable ---
  // Cortex-M7 TRM §5 / core_cm7.h. The CMSIS helpers do the DSB/ISB and
  // cache-line loops for us; we just call them in the right order.
  SCB_EnableICache();
  SCB_EnableDCache();

  // --- 4. Clock tree: HSE 16 MHz → PLL1 → 480 MHz SYSCLK ---
  configure_clocks();
}
