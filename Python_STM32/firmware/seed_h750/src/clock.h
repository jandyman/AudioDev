// clock.h — clock tree configuration for STM32H750 on Daisy Seed Rev 7
//
// See spec 01 §2 and spec 02 §7 for the target clock topology:
//   HSE 16 MHz → PLL1 (M=4, N=240, P=2) → SYSCLK 480 MHz
//   HCLK = 240 MHz, APB1/2/3/4 = 120 MHz (timer clocks 240 MHz)

#ifndef DAISY_CLAUDE_CLOCK_H
#define DAISY_CLAUDE_CLOCK_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// Target bus frequencies after configure_clocks() runs.
#define SYSCLK_HZ  480000000U
#define HCLK_HZ    240000000U
#define APB1_HZ    120000000U
#define APB2_HZ    120000000U
#define APB3_HZ    120000000U
#define APB4_HZ    120000000U

// SAI1 kernel clock (PLL3P) after configure_sai1_clock() runs.
// Target: 12.288 MHz MCLK = 256 × 48 kHz. Kernel at 49.167 MHz then divided
// by SAI_MCKDIV=2 (→ /4) yields 12.2917 MHz. Actual error from 12.288 MHz
// is ~300 ppm — inaudible, accepted per spec 04 §10 decision #1.
#define SAI1_KERNEL_HZ  49166667U

// Configure PWR, FLASH, PLL1, and the AHB/APB dividers so SYSCLK = 480 MHz.
// Called exactly once, from SystemInit() before main(). Blocks until every
// ready/lock bit is set; spins forever on failure so a debugger can catch
// the problem at the exact step that failed.
void configure_clocks(void);

// Configure PLL3 to drive the SAI1 kernel clock and select PLL3P as the
// SAI1SEL source. Must be called AFTER configure_clocks() (needs HSE on)
// AND AFTER systick_init() (uses millis() for the lock-wait timeout).
//
// Returns true on PLL3 lock, false if the lock bit never set within ~5 ms.
// Unlike configure_clocks(), this does not spin forever on failure — main()
// uses the return value to pick a fault blink pattern so the failure mode
// is visible without a debugger attached.
bool configure_sai1_clock(void);

// Exported for anyone (SysTick, timers, UART...) that needs to know the
// current SYSCLK/HCLK. Populated by configure_clocks().
extern uint32_t g_sysclk_hz;
extern uint32_t g_hclk_hz;

#ifdef __cplusplus
}  // extern "C"
#endif

#endif  // DAISY_CLAUDE_CLOCK_H
