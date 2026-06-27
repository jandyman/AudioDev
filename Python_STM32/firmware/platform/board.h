// board.h — Daisy Seed Rev 7 pin assignments
//
// Single source of truth for pin/port mapping. Any driver or main-line code
// that needs to know "which pin is the LED?" imports it from here. No magic
// numbers anywhere else in the firmware.
//
// See docs/spec/01_hardware_overview.md for the full hardware map.

#ifndef DAISY_CLAUDE_BOARD_H
#define DAISY_CLAUDE_BOARD_H

#include "stm32h750xx.h"

// ---- User LED (Seed Rev 7) ----
// The on-board red LED sits on PC7, active-high, with a 1 kΩ series
// resistor to ground. Drive the pin high to light the LED.
#define LED_USER_PORT  GPIOC
#define LED_USER_PIN   7U

// ---- SAI1 → PCM3060 codec (Seed Rev 7 internal traces) ----
// All five SAI1 signals are routed internally on the Seed between the
// STM32H750 and the PCM3060; they are NOT brought out to the 2x20 header
// and cannot be scoped externally. STM32 side is port E, AF6. See spec 01
// §3 and the STM32H750 alternate-function table.
//
// Sub-block A = TX master  (STM32 → DAC DIN)
// Sub-block B = RX slave   (ADC DOUT → STM32), synchronous with A
#define SAI1_PORT        GPIOE
#define SAI1_MCLK_A_PIN  2U   // master clock to codec SCKI1/SCKI2 (12.288 MHz)
#define SAI1_SD_B_PIN    3U   // ADC DOUT  → STM32   (sub-block B data in)
#define SAI1_FS_A_PIN    4U   // frame sync (LRCK1/LRCK2)
#define SAI1_SCK_A_PIN   5U   // bit clock (BCK1/BCK2)
#define SAI1_SD_A_PIN    6U   // STM32 → DAC DIN     (sub-block A data out)
#define SAI1_AF          6U   // alternate function number on H750 for SAI1

#endif  // DAISY_CLAUDE_BOARD_H
