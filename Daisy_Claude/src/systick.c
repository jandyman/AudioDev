/* systick.c — 1 ms SysTick on STM32H750
 *
 * SysTick is a 24-bit down-counter inside the Cortex-M7 core (not a
 * STM32-specific peripheral). We drive it from the processor clock
 * directly (SysTick_CTRL_CLKSOURCE_Msk = 1, i.e. HCLK, NOT HCLK/8). With
 * HCLK = 240 MHz, a 1 ms tick needs LOAD = 240_000 - 1, which fits
 * comfortably in 24 bits (max ~16.7 M).
 *
 * The CMSIS SysTick->LOAD register is 24 bits wide; values above 0xFFFFFF
 * truncate silently, so we assert at init that our reload fits.
 */

#include "stm32h750xx.h"
#include "core_cm7.h"

#include "systick.h"
#include "clock.h"

static volatile uint32_t g_ticks_ms = 0;

void systick_init(void)
{
    const uint32_t ticks = g_hclk_hz / 1000U; /* 240_000 at 240 MHz */
    /* SysTick_Config() sets LOAD, clears VAL, selects processor clock,
     * enables the tick interrupt, enables the counter, and programs the
     * NVIC SysTick priority (group 0, sub 0xFF — lowest urgency in the
     * default NVIC layout). It returns nonzero if (ticks - 1) > 0xFFFFFF. */
    if (SysTick_Config(ticks) != 0U) {
        /* Reload doesn't fit in 24 bits — clock tree probably wrong. */
        while (1) { }
    }
}

void SysTick_Handler(void)
{
    g_ticks_ms++;
}

uint32_t millis(void)
{
    return g_ticks_ms;
}

void delay_ms(uint32_t ms)
{
    const uint32_t start = g_ticks_ms;
    while ((g_ticks_ms - start) < ms) {
        /* wait for SysTick ISR */
    }
}
