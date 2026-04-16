/* gpio.h — minimal GPIO helpers for step 1
 *
 * Only what the LED blink needs: enable a port's clock, set a pin's mode to
 * push-pull output (or generic input), and read/write/toggle the output.
 * Alternate-function routing (needed for SAI1 in step 2) is deferred.
 */

#ifndef DAISY_CLAUDE_GPIO_H
#define DAISY_CLAUDE_GPIO_H

#include <stdbool.h>
#include <stdint.h>

#include "stm32h750xx.h"

typedef enum {
    GPIO_MODE_INPUT     = 0x0U,
    GPIO_MODE_OUTPUT_PP = 0x1U,
    GPIO_MODE_ALTERNATE = 0x2U,
    GPIO_MODE_ANALOG    = 0x3U,
} gpio_mode_t;

void gpio_enable_port(GPIO_TypeDef *port);
void gpio_set_mode(GPIO_TypeDef *port, uint32_t pin, gpio_mode_t mode);
void gpio_write(GPIO_TypeDef *port, uint32_t pin, bool value);
void gpio_toggle(GPIO_TypeDef *port, uint32_t pin);
bool gpio_read(GPIO_TypeDef *port, uint32_t pin);

#endif /* DAISY_CLAUDE_GPIO_H */
