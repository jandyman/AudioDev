// main.cpp — pitch_shifter firmware entry point.
//
// Boot sequence:
//   1. SysTick  — 1 ms timebase
//   2. PLL3     — SAI1 kernel clock (~49.167 MHz)
//   3. SAI1     — register config, SAIEN still off
//   4. pitch_shifter_audio_init() — graph init
//   5. audio_init() — MPU, DMA, PB11, SAI DMAEN, sai1_enable()
//
// Fault blink rates:
//   5 Hz  = PLL3 lock failed
//   10 Hz = SAI1 register read-back mismatch
//   2 Hz  = audio_init() returned false
//   4 Hz  = DMA armed but no IRQ within 20 ms

#include <stdbool.h>
#include <stdint.h>

#include "audio.h"
#include "audio_graph_runner.h"
#include "board.h"
#include "clock.h"
#include "gpio.h"
#include "rgb_led.h"
#include "rtt_audio.h"
#include "sai1.h"
#include "software_timer.h"
#include "systick.h"

static constexpr uint32_t kLedBlinkHalfPeriodMs = 500U;

// Image CRC published for the host telemetry handshake. At boot the firmware
// CRCs its own flash image (the exact bytes objcopy emits as pitch_shifter.bin)
// and stores the result here; the host CRCs build/pitch_shifter.bin the same way
// and compares, confirming the running binary IS this build — opt level, flags,
// toolchain and all. Lives in .bss (RAM), so it is NOT part of the CRC'd image
// (no self-reference). Non-static → clean .map symbol; the store proves liveness.
volatile uint32_t audio_image_crc = 0u;

// Image bounds from the linker script. _eidata is the end of the .data LMA =
// end of the flash image; the start is the vector table at ORIGIN(FLASH).
extern "C" uint8_t  _eidata;
extern "C" uint32_t g_pfnVectors;

// CRC-32/ISO-HDLC (poly 0xEDB88320 reflected, init/xorout 0xFFFFFFFF) — bit-for-
// bit identical to Python's zlib.crc32. Bitwise, no table; runs once at boot over
// ~24 KB (a few µs at 480 MHz), so a lookup table in flash isn't worth the bytes.
static uint32_t crc32_iso_hdlc(const uint8_t* p, uint32_t n) {
  uint32_t crc = 0xFFFFFFFFu;
  for (uint32_t i = 0u; i < n; ++i) {
    crc ^= p[i];
    for (int b = 0; b < 8; ++b) {
      uint32_t mask = 0u - (crc & 1u);          // 0x00000000 or 0xFFFFFFFF
      crc = (crc >> 1) ^ (0xEDB88320u & mask);
    }
  }
  return ~crc;
}

// ---- Pod RGB level meter ----------------------------------------------------
// LED1 = input drive, LED2 = shifted output. Color zones by peak magnitude:
// green (nominal) → yellow (hot) → red (near clip). A decaying hold per LED
// keeps transients from flickering the color and gives a soft clip-hold.
static constexpr uint32_t kMeterPeriodMs = 20U;     // 50 Hz update
static constexpr float    kVuYellow      = 0.501f;  // -6 dBFS
static constexpr float    kVuRed         = 0.891f;  // -1 dBFS
static constexpr float    kVuFloor       = 0.0032f; // ~-50 dBFS → LED off
static constexpr float    kVuDecay       = 0.90f;   // ~250 ms fall at 50 Hz

static rgb_color vu_color(float level) {
  if (level < kVuFloor)  return RGB_OFF;
  if (level < kVuYellow) return RGB_GREEN;
  if (level < kVuRed)    return RGB_YELLOW;
  return RGB_RED;
}

static void meter_update(void) {
  // Read-and-clear the running peaks atomically vs the audio ISR (it does a
  // read-modify-write of these each block). Sub-µs interrupt-off window.
  // Note: shares the peaks with the RTT peak_meter tool — whichever reads a
  // given window first claims it; harmless for a visual meter.
  __disable_irq();
  float in_pk  = audio_in_peak;   audio_in_peak  = 0.0f;
  float out_pk = audio_out_peak;  audio_out_peak = 0.0f;
  __enable_irq();

  static float in_disp = 0.0f, out_disp = 0.0f;
  in_disp  = (in_pk  > in_disp)  ? in_pk  : in_disp  * kVuDecay;
  out_disp = (out_pk > out_disp) ? out_pk : out_disp * kVuDecay;

  rgb_led_set(RGB_LED1, vu_color(in_disp));
  rgb_led_set(RGB_LED2, vu_color(out_disp));
}

static void fault_blink(uint32_t half_period_ms) {
  for (;;) {
    gpio_toggle(LED_USER_PORT, LED_USER_PIN);
    delay_ms(half_period_ms);
  }
}

extern "C" int main(void) {
  gpio_enable_port(LED_USER_PORT);
  gpio_set_mode(LED_USER_PORT, LED_USER_PIN, GPIO_MODE_OUTPUT_PP);
  gpio_write(LED_USER_PORT, LED_USER_PIN, false);
  rgb_led_init();

  systick_init();
  rtt_audio_init();
  audio_graph_init(48000);
  audio_graph_profile_init();              // DWT cycle counter for DSP timing

  // Publish the running image's CRC for the host handshake.
  const uint8_t* img     = reinterpret_cast<const uint8_t*>(&g_pfnVectors);
  const uint32_t img_len = static_cast<uint32_t>(&_eidata - img);
  audio_image_crc        = crc32_iso_hdlc(img, img_len);

  if (!configure_sai1_clock()) {
    fault_blink(100U);                  // 5 Hz — PLL3 lock failed
  }
  if (!sai1_configure()) {
    fault_blink(50U);                   // 10 Hz — SAI1 register fault
  }
  if (!audio_init()) {
    fault_blink(250U);                  // 2 Hz — DMA/MPU/enable fault
  }

  const uint32_t init_start_ms = millis();
  while (audio_irq_count == 0U && (millis() - init_start_ms) < 20U) {
    __asm volatile ("nop");
  }
  if (audio_irq_count == 0U) {
    fault_blink(125U);                  // 4 Hz — DMA silent after init
  }

  SoftwareTimer led_timer(kLedBlinkHalfPeriodMs);
  SoftwareTimer meter_timer(kMeterPeriodMs);

  for (;;) {
    rtt_audio_poll();
    if (led_timer.expired()) {
      gpio_toggle(LED_USER_PORT, LED_USER_PIN);
    }
    if (meter_timer.expired()) {
      meter_update();
    }
  }
}
