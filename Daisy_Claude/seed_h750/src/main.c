// main.c — Daisy_Claude step 2 (DMA audio passthrough)
//
// Boot sequence after Reset_Handler / SystemInit / configure_clocks():
//   1. SysTick — 1 ms timebase
//   2. PLL3    — SAI1 kernel clock (~49.167 MHz)
//   3. SAI1    — register config, SAIEN still off
//   4. audio_init() — MPU, DMA, PB11, SAI DMAEN, sai1_enable()
//
// LED blink rate (driven by DMA IRQ once audio_init succeeds):
//   ~1 Hz (IRQ-driven) = DMA running, audio flowing  (success)
//   5 Hz  (delay_ms)   = PLL3 fault
//   10 Hz (delay_ms)   = SAI1 register fault
//   2 Hz  (delay_ms)   = audio_init() fault
//   frozen after ~20 ms = audio_init succeeded but DMA never fired
//
// LED off / stuck before any blink = startup or configure_clocks hung.

#include <stdbool.h>
#include <stdint.h>

#include "audio.h"
#include "board.h"
#include "clock.h"
#include "eq.h"
#include "gpio.h"
#include "params.h"
#include "sai1.h"
#include "systick.h"

int main(void) {
  gpio_enable_port(LED_USER_PORT);
  gpio_set_mode(LED_USER_PORT, LED_USER_PIN, GPIO_MODE_OUTPUT_PP);
  gpio_write(LED_USER_PORT, LED_USER_PIN, false);

  systick_init();
  params_init();
  eq_init();

  // Fault path: blink at given half-period forever using delay_ms.
  // Only reached if something in the init chain fails.
  uint32_t fault_half_ms = 0U;

  if (!configure_sai1_clock()) {
    fault_half_ms = 100U;             // 5 Hz — PLL3 fault
  } else if (!sai1_configure()) {
    fault_half_ms = 50U;              // 10 Hz — SAI1 register fault
  } else if (!audio_init()) {
    fault_half_ms = 250U;             // 2 Hz — DMA/MPU/enable fault
  }

  if (fault_half_ms != 0U) {
    for (;;) {
      gpio_toggle(LED_USER_PORT, LED_USER_PIN);
      delay_ms(fault_half_ms);
    }
  }

  // Success path: DMA is running; IRQ handler toggles the LED every 500
  // callbacks (~1 Hz). Wait up to ~20 ms for the first IRQ to confirm
  // the DMA is actually firing. If it never fires, blink fast.
  const uint32_t start = millis();
  while (audio_irq_count == 0U) {
    if ((millis() - start) >= 20U) {
      // DMA armed but silent — distinct fault rate so we can tell it
      // apart from a clean PLL3 fault (5 Hz) or SAI1 fault (10 Hz).
      for (;;) {
        gpio_toggle(LED_USER_PORT, LED_USER_PIN);
        delay_ms(125U);               // 4 Hz — DMA silent after init
      }
    }
  }

  // DMA is running. Spin (not WFI) — WFI clock-gates the core and causes
  // the debugger to report a garbage PC on Cortex-M7. Power management later.
  for (;;) {
    __asm volatile ("nop");
  }
}
