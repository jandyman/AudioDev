// rgb_led.h — the two Daisy Pod RGB LEDs as simple on/off-per-channel indicators.
//
// Platform-layer driver (shared by every project). Minimal tier: each of the 6
// channels is plain GPIO, so a LED shows one of 8 colors (incl. off). The Pod
// LEDs are common-anode / active-low, matching libDaisy's Pod driver (which is
// also on/off-only today). PWM dimming is a deliberate later tier.

#pragma once

#include <stdint.h>

typedef enum { RGB_LED1 = 0, RGB_LED2 = 1 } rgb_led_id;

// R/G/B as bit flags so colors compose; values chosen for readable combinations.
typedef enum {
  RGB_OFF     = 0x0,
  RGB_BLUE    = 0x1,
  RGB_GREEN   = 0x2,
  RGB_RED     = 0x4,
  RGB_YELLOW  = RGB_RED | RGB_GREEN,
  RGB_CYAN    = RGB_GREEN | RGB_BLUE,
  RGB_MAGENTA = RGB_RED | RGB_BLUE,
  RGB_WHITE   = RGB_RED | RGB_GREEN | RGB_BLUE,
} rgb_color;

// Enable the LED ports and drive both LEDs off. Call once at boot.
void rgb_led_init(void);

// Drive one LED to a color.
void rgb_led_set(rgb_led_id led, rgb_color color);
