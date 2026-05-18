// param_update.h — IRQ-safe parameter update patterns.
//
// AtomicParam<T>
//   General-purpose: foreground calls apply() to atomically replace `live`.
//   ISR reads `live` directly — no flag checks, no branches.
//   The critical section is a struct copy with IRQ disabled (~20 cycles).
//   Use when T is small and replacing the full struct (including any state)
//   on every update is acceptable.
//
// FilterChannel
//   Biquad-specific: foreground calls update() (preserve delay state, no click)
//   or update_with_reset() (zero delay state, for order changes).
//   ISR calls cascade.process(x) directly — no overhead.
//
// Platform: IRQ disable/enable uses CMSIS __disable_irq()/__enable_irq() on
// Cortex-M7 targets. Native macOS build is single-threaded; the copy is done
// without IRQ primitives.

#pragma once
#include "biquad.h"

// Cortex-M7 (arm-none-eabi) guard. Excludes macOS ARM (AArch64 != ARMv7E-M).
#if defined(__ARM_ARCH_7EM__)
#  define PARAM_DISABLE_IRQ()  __disable_irq()
#  define PARAM_ENABLE_IRQ()   __enable_irq()
#else
#  define PARAM_DISABLE_IRQ()  do {} while(0)
#  define PARAM_ENABLE_IRQ()   do {} while(0)
#endif

// ---- AtomicParam<T> -------------------------------------------------------

template<typename T>
struct AtomicParam {
  T live{};

  // Foreground: replace live atomically. ISR reads live directly.
  void apply(const T& s) {
    PARAM_DISABLE_IRQ();
    live = s;
    PARAM_ENABLE_IRQ();
  }
};

// ---- FilterChannel --------------------------------------------------------

// Owns a BiquadCascade (coefficients + delay state). ISR calls process()
// directly on the cascade. Foreground updates via update() or update_with_reset().
struct FilterChannel {
  BiquadCascade cascade;

  // Update coefficients only — delay state preserved (no click).
  // Use for fc / gain / Q changes when order is unchanged.
  void update(const CascadeCoeffs& c) {
    PARAM_DISABLE_IRQ();
    cascade.set_coeffs(c);
    PARAM_ENABLE_IRQ();
  }

  // Update coefficients AND zero all delay lines.
  // Use when order changes — causes at most one block of glitch.
  void update_with_reset(const CascadeCoeffs& c) {
    PARAM_DISABLE_IRQ();
    cascade.set_coeffs_and_reset(c);
    PARAM_ENABLE_IRQ();
  }
};
