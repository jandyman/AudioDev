// gpio.c — GPIO helpers for step 1
//
// GPIO ports on STM32H750 live on the AHB4 bus. The port clock enables are
// in RCC_AHB4ENR, one bit per port starting with GPIOA at bit 0.
//
// Each port's MODER register holds 2 bits per pin:
//   00 = input, 01 = output, 10 = alternate function, 11 = analog.
//
// For fast atomic output changes we use BSRR (bit-set/reset), which lets us
// raise or lower any pin without a read-modify-write. See RM0433 §8.4.7.

#include "gpio.h"
#include "stm32h750xx.h"

void gpio_enable_port(GPIO_TypeDef *port) {
  // Map each port base to its RCC_AHB4ENR bit. An if/else chain keeps the
  // mapping local and trivially auditable; the port pointers are not all
  // constant expressions so a switch is not an option.
  uint32_t bit = 0;
  if      (port == GPIOA) bit = RCC_AHB4ENR_GPIOAEN;
  else if (port == GPIOB) bit = RCC_AHB4ENR_GPIOBEN;
  else if (port == GPIOC) bit = RCC_AHB4ENR_GPIOCEN;
  else if (port == GPIOD) bit = RCC_AHB4ENR_GPIODEN;
  else if (port == GPIOE) bit = RCC_AHB4ENR_GPIOEEN;
  else if (port == GPIOF) bit = RCC_AHB4ENR_GPIOFEN;
  else if (port == GPIOG) bit = RCC_AHB4ENR_GPIOGEN;
  else if (port == GPIOH) bit = RCC_AHB4ENR_GPIOHEN;
  else if (port == GPIOJ) bit = RCC_AHB4ENR_GPIOJEN;
  else if (port == GPIOK) bit = RCC_AHB4ENR_GPIOKEN;
  else return;

  RCC->AHB4ENR |= bit;
  // read-back to make sure the clock is live before the next access
  (void)RCC->AHB4ENR;
}

void gpio_set_mode(GPIO_TypeDef *port, uint32_t pin, gpio_mode_t mode) {
  const uint32_t shift = pin * 2U;
  const uint32_t mask  = 0x3U << shift;
  port->MODER = (port->MODER & ~mask) | ((uint32_t)mode << shift);
}

void gpio_write(GPIO_TypeDef *port, uint32_t pin, bool value) {
  // BSRR lower half sets the pin, upper half resets it. Single write,
  // no read-modify-write, no interrupt race.
  if (value) {
    port->BSRR = (1U << pin);
  } else {
    port->BSRR = (1U << (pin + 16U));
  }
}

void gpio_toggle(GPIO_TypeDef *port, uint32_t pin) {
  // ODR is writable, and for a one-liner toggle the XOR is clean enough.
  port->ODR ^= (1U << pin);
}

bool gpio_read(GPIO_TypeDef *port, uint32_t pin) {
  return ((port->IDR >> pin) & 1U) != 0U;
}

void gpio_configure_alternate(GPIO_TypeDef *port, uint32_t pin, uint32_t af,
                              gpio_speed_t speed, gpio_pull_t pull) {
  // ---- AFRL (pins 0..7) / AFRH (pins 8..15): 4 bits per pin ----
  // Pick the right array slot and shift within it; the low nibble of `af`
  // is the AF number from the STM32H750 alternate-function table.
  const uint32_t af_shift = (pin & 0x7U) * 4U;
  const uint32_t af_mask  = 0xFU << af_shift;
  const uint32_t af_word  = (pin >> 3U) & 0x1U;   // 0 = AFRL, 1 = AFRH
  port->AFR[af_word] = (port->AFR[af_word] & ~af_mask)
                     | ((af & 0xFU) << af_shift);

  // ---- OSPEEDR / PUPDR: 2 bits per pin ----
  const uint32_t two_bit_shift = pin * 2U;
  const uint32_t two_bit_mask  = 0x3U << two_bit_shift;
  port->OSPEEDR = (port->OSPEEDR & ~two_bit_mask)
                | ((uint32_t)speed << two_bit_shift);
  port->PUPDR   = (port->PUPDR   & ~two_bit_mask)
                | ((uint32_t)pull  << two_bit_shift);

  // ---- MODER last: switch the pin from GPIO to AF driver. Doing this
  // after AFRx means the pin never spends a cycle routed to the wrong AF.
  gpio_set_mode(port, pin, GPIO_MODE_ALTERNATE);
}
