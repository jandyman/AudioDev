// main.c — Daisy_Claude step 1 (blink + PLL3 bring-up)
//
// At this point:
//   - Reset_Handler has done .data copy / .bss zero.
//   - SystemInit has enabled FPU + caches, set VTOR, and brought the clock
//     tree up to 480 MHz (HCLK = 240 MHz) via configure_clocks().
//
// After that, main() brings up SysTick and then PLL3 (the SAI1 kernel clock
// source, needed by the upcoming audio sub-steps). Since PE2 (MCLK) is an
// internal trace on the Seed and cannot be scoped externally, we turn the
// LED itself into the PLL3-status indicator:
//
//   1 Hz blink  = PLL3 locked, clock tree fully up
//   5 Hz blink  = PLL3 failed to lock within ~5 ms
//
// Both the normal and fault paths blink, so "LED off" or "LED stuck on"
// still unambiguously means "earlier code path hung" — we're not losing
// the Part 1 bring-up signal.

#include <stdbool.h>

#include "board.h"
#include "clock.h"
#include "gpio.h"
#include "systick.h"

int main(void) {
  gpio_enable_port(LED_USER_PORT);
  gpio_set_mode(LED_USER_PORT, LED_USER_PIN, GPIO_MODE_OUTPUT_PP);
  gpio_write(LED_USER_PORT, LED_USER_PIN, false);

  systick_init();

  const bool pll3_ok = configure_sai1_clock();
  const uint32_t half_period_ms = pll3_ok ? 500U : 100U;

  for (;;) {
    gpio_toggle(LED_USER_PORT, LED_USER_PIN);
    delay_ms(half_period_ms);
  }
}
