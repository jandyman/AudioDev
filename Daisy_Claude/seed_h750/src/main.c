// main.c — Daisy_Claude step 1 (blink + PLL3 + SAI1 pin/register bring-up)
//
// At this point:
//   - Reset_Handler has done .data copy / .bss zero.
//   - SystemInit has enabled FPU + caches, set VTOR, and brought the clock
//     tree up to 480 MHz (HCLK = 240 MHz) via configure_clocks().
//
// From main(), we bring up SysTick, then PLL3 (SAI1 kernel clock), then
// SAI1 itself (sub-block A master TX + sub-block B sync-slave RX, no DMA
// yet). None of the SAI1 I/O pins are on the Seed header so we can't
// scope them; instead the LED blink rate encodes the furthest point we
// successfully reached:
//
//   1 Hz  = PLL3 locked AND SAI1 register read-back clean (full success)
//   5 Hz  = PLL3 failed to lock within ~5 ms (clock tree fault)
//   10 Hz = PLL3 OK but SAI1 register config failed verification
//
// LED off / stuck = earlier code path hung (startup or configure_clocks).

#include <stdbool.h>

#include "board.h"
#include "clock.h"
#include "gpio.h"
#include "sai1.h"
#include "systick.h"

int main(void) {
  gpio_enable_port(LED_USER_PORT);
  gpio_set_mode(LED_USER_PORT, LED_USER_PIN, GPIO_MODE_OUTPUT_PP);
  gpio_write(LED_USER_PORT, LED_USER_PIN, false);

  systick_init();

  uint32_t half_period_ms;
  if (!configure_sai1_clock()) {
    half_period_ms = 100U;           // 5 Hz — PLL3 fault
  } else if (!sai1_configure()) {
    half_period_ms = 50U;            // 10 Hz — SAI1 config fault
  } else {
    half_period_ms = 500U;           // 1 Hz — all good
  }

  for (;;) {
    gpio_toggle(LED_USER_PORT, LED_USER_PIN);
    delay_ms(half_period_ms);
  }
}
