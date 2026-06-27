// level_meter.h — platform RGB level meter for the two Daisy Pod LEDs
// (LED1 = input drive, LED2 = processed output).
//
// Driven automatically by audio_graph_runner from inside the per-block audio
// path, so every graph project gets the meter with NO per-project glue: the
// runner feeds it the windowed input/output peaks at ~50 Hz and it maps them to
// LED color with a decaying peak-hold plus a latched true-clip indicator.
// BARE_METAL only — the native pybind build has no LEDs and never links this.
//
// Color zones (peak magnitude, full scale = 1.0):
//   off     < -50 dBFS
//   green   -50 .. -12 dBFS   nominal
//   yellow  -12 dBFS .. clip  hot
//   red     latched on a real clip event (peak at the output limiter ceiling),
//           held ~300 ms so a brief overload is visible

#pragma once

// Enable the RGB LED GPIOs. Call once at boot (the runner does this).
void level_meter_init(void);

// Refresh both LEDs from the most recent window's input/output peaks. The runner
// calls this every kMeterUpdateBlocks audio blocks; it holds its own decay/clip
// state between calls. Cheap: a few floats plus ~6 GPIO writes, ~50 times/sec.
void level_meter_update(float in_peak, float out_peak);
