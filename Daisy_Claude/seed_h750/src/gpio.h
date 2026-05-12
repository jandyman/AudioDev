// gpio.h — GPIO helpers
//
// What's here:
//   - port-clock enable
//   - mode / read / write / toggle for generic digital I/O
//   - alternate-function configuration (mode=AF + AFRL/AFRH nibble +
//     output speed + pull), which SAI1 needs on PE2..PE6.

#ifndef DAISY_CLAUDE_GPIO_H
#define DAISY_CLAUDE_GPIO_H

#include <stdbool.h>
#include <stdint.h>

#include "stm32h750xx.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
  GPIO_MODE_INPUT     = 0x0U,
  GPIO_MODE_OUTPUT_PP = 0x1U,
  GPIO_MODE_ALTERNATE = 0x2U,
  GPIO_MODE_ANALOG    = 0x3U,
} gpio_mode_t;

typedef enum {
  GPIO_SPEED_LOW       = 0x0U,
  GPIO_SPEED_MEDIUM    = 0x1U,
  GPIO_SPEED_HIGH      = 0x2U,
  GPIO_SPEED_VERY_HIGH = 0x3U,
} gpio_speed_t;

typedef enum {
  GPIO_PULL_NONE = 0x0U,
  GPIO_PULL_UP   = 0x1U,
  GPIO_PULL_DOWN = 0x2U,
} gpio_pull_t;

void gpio_enable_port(GPIO_TypeDef *port);
void gpio_set_mode(GPIO_TypeDef *port, uint32_t pin, gpio_mode_t mode);
void gpio_write(GPIO_TypeDef *port, uint32_t pin, bool value);
void gpio_toggle(GPIO_TypeDef *port, uint32_t pin);
bool gpio_read(GPIO_TypeDef *port, uint32_t pin);

// Configure a pin for alternate function: writes the AFRL/AFRH nibble,
// sets OSPEEDR and PUPDR, then switches MODER to "alternate function".
// Output type stays at the default (push-pull). The port's clock must
// already be enabled via gpio_enable_port().
//
// `af` is the 4-bit alternate-function number from the STM32H750
// datasheet alternate-function table (e.g. AF6 for SAI1).
void gpio_configure_alternate(GPIO_TypeDef *port, uint32_t pin, uint32_t af,
                              gpio_speed_t speed, gpio_pull_t pull);

#ifdef __cplusplus
}  // extern "C"
#endif

#endif  // DAISY_CLAUDE_GPIO_H
