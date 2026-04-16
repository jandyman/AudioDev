// main.c — Daisy_Claude step 1, part 1 (blink)
//
// At this point:
//   - Reset_Handler has done .data copy / .bss zero.
//   - SystemInit has enabled FPU + caches, set VTOR, and brought the clock
//     tree up to 480 MHz (HCLK = 240 MHz).
// All that's left is to set up the LED pin, start SysTick, and blink.
//
// The whole point of step 1 is to prove the bring-up works. If you see the
// LED toggling at ~1 Hz, every earlier piece of machinery — the startup
// file, linker script, clock config, VTOR, SysTick ISR — is doing its job.

#include "board.h"
#include "gpio.h"
#include "systick.h"

int main(void) {
  gpio_enable_port(LED_USER_PORT);
  gpio_set_mode(LED_USER_PORT, LED_USER_PIN, GPIO_MODE_OUTPUT_PP);
  gpio_write(LED_USER_PORT, LED_USER_PIN, false);

  systick_init();

  for (;;) {
    gpio_toggle(LED_USER_PORT, LED_USER_PIN);
    delay_ms(500U);
  }
}
