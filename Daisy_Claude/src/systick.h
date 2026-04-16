/* systick.h — 1 ms SysTick-based timebase */

#ifndef DAISY_CLAUDE_SYSTICK_H
#define DAISY_CLAUDE_SYSTICK_H

#include <stdint.h>

/* Configure SysTick to fire every 1 ms. Must be called after the clock tree
 * is up (i.e. after configure_clocks()), because it uses g_hclk_hz to
 * compute the reload value. */
void systick_init(void);

/* Monotonic milliseconds since systick_init(). Wraps after ~49.7 days. */
uint32_t millis(void);

/* Busy-wait for the given number of milliseconds. Fine for step 1. */
void delay_ms(uint32_t ms);

#endif /* DAISY_CLAUDE_SYSTICK_H */
