// level_meter.cpp — peak→color policy for the two Pod LEDs. See level_meter.h.

#include "level_meter.h"

#include "rgb_led.h"

namespace {

// Tuning — the meter's entire policy lives here.
// Yellow is a wide "hot" band from -12 dBFS up to clip (the old meter gave it
// only -6..-1 dBFS, a 5 dB sliver); red is reserved for a REAL clip event rather
// than mere proximity, so it now means "you clipped", not "you're near clipping".
constexpr float kVuFloor   = 0.0032f;   // ~-50 dBFS → LED off
constexpr float kVuYellow  = 0.251f;    // -12 dBFS  → green below, yellow above
constexpr float kClip      = 0.999f;    // ~0 dBFS   → at the output limiter ceiling
constexpr float kVuDecay   = 0.90f;     // ~250 ms peak-hold fall at the 50 Hz rate
constexpr int   kClipHold  = 15;        // ~300 ms red hold after a clip (at 50 Hz)

rgb_color vu_color(float level, bool clipped) {
  if (clipped)           return RGB_RED;
  if (level < kVuFloor)  return RGB_OFF;
  if (level < kVuYellow) return RGB_GREEN;
  return RGB_YELLOW;
}

// Per-LED display state: a decaying peak-hold plus a clip-latch countdown so a
// momentary overload stays red for kClipHold updates instead of flashing past.
struct channel {
  float disp      = 0.0f;
  int   clip_hold = 0;

  rgb_color step(float peak) {
    disp = (peak > disp) ? peak : disp * kVuDecay;
    if (peak >= kClip) clip_hold = kClipHold;
    else if (clip_hold > 0) --clip_hold;
    return vu_color(disp, clip_hold > 0);
  }
};

channel s_in;
channel s_out;

}  // namespace

void level_meter_init(void) {
  rgb_led_init();
}

void level_meter_update(float in_peak, float out_peak) {
  rgb_led_set(RGB_LED1, s_in.step(in_peak));
  rgb_led_set(RGB_LED2, s_out.step(out_peak));
}
