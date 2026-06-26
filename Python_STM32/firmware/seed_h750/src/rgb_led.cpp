// rgb_led.cpp — Daisy Pod RGB LED driver (minimal on/off tier).
//
// Pin wiring is from libDaisy's daisy_pod.cpp active block (labeled "Seed Rev3
// and Rev4", matching this Pod rev3 / Seed Rev4), with the Daisy pin numbers
// resolved to STM32 ports via daisy_seed.h:
//   LED1 R/G/B = D20/D19/D18 = PC1/PA6/PA7
//   LED2 R/G/B = D17/D24/D23 = PB1/PA1/PA4
// These don't collide with anything the firmware drives (PC7 user LED, PE2..PE6
// SAI1, PB11 codec reset). The LEDs are common-anode → active LOW: drive a pin
// LOW to light its channel, HIGH to extinguish it.

#include "rgb_led.h"

#include "gpio.h"
#include "stm32h750xx.h"

namespace {

struct led_pin {
  GPIO_TypeDef* port;
  uint32_t      pin;
};

// [led][channel]: channel 0 = R, 1 = G, 2 = B.
const led_pin kPins[2][3] = {
  { {GPIOC, 1U}, {GPIOA, 6U}, {GPIOA, 7U} },   // LED1: R=PC1  G=PA6  B=PA7
  { {GPIOB, 1U}, {GPIOA, 1U}, {GPIOA, 4U} },   // LED2: R=PB1  G=PA1  B=PA4
};

// Active-low: ON means drive the pin LOW. gpio_write(port, pin, false) = LOW.
inline void drive_channel(const led_pin& p, bool on) {
  gpio_write(p.port, p.pin, !on);
}

}  // namespace

void rgb_led_init(void) {
  gpio_enable_port(GPIOA);
  gpio_enable_port(GPIOB);
  gpio_enable_port(GPIOC);
  for (int led = 0; led < 2; ++led)
    for (int ch = 0; ch < 3; ++ch) {
      gpio_set_mode(kPins[led][ch].port, kPins[led][ch].pin, GPIO_MODE_OUTPUT_PP);
      drive_channel(kPins[led][ch], false);   // off
    }
}

void rgb_led_set(rgb_led_id led, rgb_color color) {
  drive_channel(kPins[led][0], (color & RGB_RED)   != 0);
  drive_channel(kPins[led][1], (color & RGB_GREEN) != 0);
  drive_channel(kPins[led][2], (color & RGB_BLUE)  != 0);
}
