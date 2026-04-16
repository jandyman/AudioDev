/* clock.h — clock tree configuration for STM32H750 on Daisy Seed Rev 7
 *
 * See spec 01 §2 and spec 02 §7 for the target clock topology:
 *   HSE 16 MHz → PLL1 (M=4, N=240, P=2) → SYSCLK 480 MHz
 *   HCLK = 240 MHz, APB1/2/3/4 = 120 MHz (timer clocks 240 MHz)
 */

#ifndef DAISY_CLAUDE_CLOCK_H
#define DAISY_CLAUDE_CLOCK_H

#include <stdint.h>

/* Target bus frequencies after configure_clocks() runs. */
#define SYSCLK_HZ   480000000U
#define HCLK_HZ     240000000U
#define APB1_HZ     120000000U
#define APB2_HZ     120000000U
#define APB3_HZ     120000000U
#define APB4_HZ     120000000U

/* Configure PWR, FLASH, PLL1, and the AHB/APB dividers so SYSCLK = 480 MHz.
 * Called exactly once, from SystemInit() before main(). Blocks until every
 * ready/lock bit is set; spins forever on failure so a debugger can catch
 * the problem at the exact step that failed. */
void configure_clocks(void);

/* Exported for anyone (SysTick, timers, UART...) that needs to know the
 * current SYSCLK/HCLK. Populated by configure_clocks(). */
extern uint32_t g_sysclk_hz;
extern uint32_t g_hclk_hz;

#endif /* DAISY_CLAUDE_CLOCK_H */
