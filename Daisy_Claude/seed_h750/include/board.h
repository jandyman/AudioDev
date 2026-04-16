/* board.h — Daisy Seed Rev 7 pin assignments
 *
 * Single source of truth for pin/port mapping. Any driver or main-line code
 * that needs to know "which pin is the LED?" imports it from here. No magic
 * numbers anywhere else in the firmware.
 *
 * See docs/spec/01_hardware_overview.md for the full hardware map.
 */

#ifndef DAISY_CLAUDE_BOARD_H
#define DAISY_CLAUDE_BOARD_H

#include "stm32h750xx.h"

/* ---- User LED (Seed Rev 7) ----
 * The on-board red LED sits on PC7, active-high, with a 1 kΩ series
 * resistor to ground. Drive the pin high to light the LED. */
#define LED_USER_PORT   GPIOC
#define LED_USER_PIN    7U

#endif /* DAISY_CLAUDE_BOARD_H */
