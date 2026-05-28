// main.cpp — pitch_shifter firmware entry point.
//
// Boot sequence:
//   1. SysTick  — 1 ms timebase
//   2. PLL3     — SAI1 kernel clock (~49.167 MHz)
//   3. SAI1     — register config, SAIEN still off
//   4. pitch_shifter_audio_init() — graph init
//   5. audio_init() — MPU, DMA, PB11, SAI DMAEN, sai1_enable()
//
// Fault blink rates:
//   5 Hz  = PLL3 lock failed
//   10 Hz = SAI1 register read-back mismatch
//   2 Hz  = audio_init() returned false
//   4 Hz  = DMA armed but no IRQ within 20 ms

#include <stdbool.h>
#include <stdint.h>

#include "audio.h"
#include "board.h"
#include "clock.h"
#include "gpio.h"
#include "pitch_shifter_audio.h"
#include "rtt_audio.h"
#include "sai1.h"
#include "software_timer.h"
#include "systick.h"

static constexpr uint32_t kLedBlinkHalfPeriodMs = 500U;

static void fault_blink(uint32_t half_period_ms) {
  for (;;) {
    gpio_toggle(LED_USER_PORT, LED_USER_PIN);
    delay_ms(half_period_ms);
  }
}

extern "C" int main(void) {
  gpio_enable_port(LED_USER_PORT);
  gpio_set_mode(LED_USER_PORT, LED_USER_PIN, GPIO_MODE_OUTPUT_PP);
  gpio_write(LED_USER_PORT, LED_USER_PIN, false);

  systick_init();
  rtt_audio_init();
  pitch_shifter_audio_init(48000);

  if (!configure_sai1_clock()) {
    fault_blink(100U);                  // 5 Hz — PLL3 lock failed
  }
  if (!sai1_configure()) {
    fault_blink(50U);                   // 10 Hz — SAI1 register fault
  }
  if (!audio_init()) {
    fault_blink(250U);                  // 2 Hz — DMA/MPU/enable fault
  }

  const uint32_t init_start_ms = millis();
  while (audio_irq_count == 0U && (millis() - init_start_ms) < 20U) {
    __asm volatile ("nop");
  }
  if (audio_irq_count == 0U) {
    fault_blink(125U);                  // 4 Hz — DMA silent after init
  }

  SoftwareTimer led_timer(kLedBlinkHalfPeriodMs);

  for (;;) {
    rtt_audio_poll();
    if (led_timer.expired()) {
      gpio_toggle(LED_USER_PORT, LED_USER_PIN);
    }
  }
}
