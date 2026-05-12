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

  // Success path: DMA is running. Wait up to ~20 ms for the first IRQ to confirm
  // the DMA is actually firing. If it never fires, we have a hardware fault.
  const uint32_t start = millis();
  while (audio_irq_count == 0U && (millis() - start) < 20U) {
    __asm volatile ("nop");  // Spin, waiting for first interrupt
  }

  if (audio_irq_count == 0U) {
    // Timeout: DMA never fired. Blink fast with distinct rate to diagnose.
    for (;;) {
      gpio_toggle(LED_USER_PORT, LED_USER_PIN);
      delay_ms(125U);               // 4 Hz — DMA silent after init
    }
  }

  // Main loop: DMA is running and confirmed working.
  // LED blink is driven by the ISR (toggles every 500 callbacks, ~1 Hz).
  // Parameter updates are checked here in the background.
  // TODO: Add low-power mode (WFI) and interrupts to wake up.
  while (true) {
    // Check if host has written parameters; if so, recompute coefficients
    if (params_dirty_flag.flags & PARAMS_DIRTY_BIT_DIRTY) {
      eq_recompute_from_params();
      params_dirty_flag.flags |= PARAMS_DIRTY_BIT_READY;
    }
    __asm volatile ("nop");  // Not WFI yet (causes debugger PC issues)
  }
}
