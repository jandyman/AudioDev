// main.cpp — Daisy_Claude entry point: bring up the clock tree, audio path,
// EQ, and parameter tree, then run a non-blocking foreground loop.
//
// Boot sequence after Reset_Handler / SystemInit / configure_clocks() and
// global-constructor iteration:
//   1. SysTick — 1 ms timebase
//   2. PLL3    — SAI1 kernel clock (~49.167 MHz)
//   3. SAI1    — register config, SAIEN still off
//   4. audio_init() — MPU, DMA, PB11, SAI DMAEN, sai1_enable()
//
// Fault paths (caught during init, blink forever with a distinct rate):
//   5 Hz  = PLL3 lock failed
//   10 Hz = SAI1 register read-back mismatch
//   2 Hz  = audio_init() returned false
//   4 Hz  = DMA armed but no IRQ within 20 ms after audio_init() returned
//
// Success path: the foreground loop runs the LED at 1 Hz via SoftwareTimer
// (proves the main loop is alive and SysTick is ticking) and recomputes EQ
// coefficients whenever the host sets params_dirty bit 0 (DIRTY).

#include <stdbool.h>
#include <stdint.h>

#include "audio.h"
#include "board.h"
#include "clock.h"
#include "eq.h"
#include "gpio.h"
#include "params.h"
#include "rtt_cmd.h"
#include "sai1.h"
#include "software_timer.h"
#include "systick.h"

// LED blink half-period. Toggle every N ms → blink rate is 1/(2N) Hz.
static constexpr uint32_t kLedBlinkHalfPeriodMs = 500U;  // 1 Hz blink

// Spin forever blinking the LED at the given half-period. Used only on fatal
// init faults — we never need to return. delay_ms is fine here because the
// system is already wedged at this point; nothing else needs the CPU.
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
  params_init();
  eq_init();
  rtt_cmd_init();  // must follow params_init() — reads eq_params[]

  // --- init chain: each step has its own fault blink rate ---
  if (!configure_sai1_clock()) {
    fault_blink(100U);                  // 5 Hz — PLL3 lock failed
  }
  if (!sai1_configure()) {
    fault_blink(50U);                   // 10 Hz — SAI1 register fault
  }
  if (!audio_init()) {
    fault_blink(250U);                  // 2 Hz — DMA/MPU/enable fault
  }

  // --- confirm DMA actually fires (audio_init returns before the first IRQ) ---
  // 20 ms is generous: at 48 kHz / 48 frames per half-buffer, HT fires every
  // 1 ms. If we don't see one in 20 ms the DMA is wedged.
  const uint32_t init_start_ms = millis();
  while (audio_irq_count == 0U && (millis() - init_start_ms) < 20U) {
    __asm volatile ("nop");
  }
  if (audio_irq_count == 0U) {
    fault_blink(125U);                  // 4 Hz — DMA silent after init
  }

  // --- foreground loop: LED heartbeat + parameter update handshake ---
  // The LED proves the main loop is alive (and SysTick is ticking). The
  // parameter handshake protocol is:
  //   host:        write param value → set params_dirty bit 0 (DIRTY)
  //   foreground:  see DIRTY → clear it → recompute → set bit 1 (READY)
  //   audio ISR:   see READY → apply new coefficients → clear all flags
  //
  // Clearing DIRTY *before* recompute is what makes this correct under host
  // writes-during-compute: any write that lands during recompute will set
  // DIRTY again, and the next loop iteration picks it up. If we cleared
  // DIRTY after compute (or not at all, as in the prior version), a write
  // arriving mid-compute would be applied and then immediately cleared by
  // the ISR's "clear all flags" step, silently losing the latest value.
  SoftwareTimer led_timer(kLedBlinkHalfPeriodMs);

  for (;;) {
    if (led_timer.expired()) {
      gpio_toggle(LED_USER_PORT, LED_USER_PIN);
    }

    rtt_cmd_poll();

    if (params_dirty_flag.flags & PARAMS_DIRTY_BIT_DIRTY) {
      params_dirty_flag.flags &= ~PARAMS_DIRTY_BIT_DIRTY;
      eq_recompute_from_params();
      params_dirty_flag.flags |= PARAMS_DIRTY_BIT_READY;
    }
  }
}
