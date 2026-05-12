// software_timer.h — Periodic, non-blocking timer over millis().
//
// SysTick increments a uint32_t every millisecond (see systick.cpp). A
// SoftwareTimer lets foreground code ask "has my period elapsed?" without
// blocking. The intended pattern is:
//
//   SoftwareTimer led(500);          // 500 ms period
//   while (true) {
//     if (led.expired()) {           // returns true once per period
//       gpio_toggle(...);
//     }
//     // ...other work...
//   }
//
// Two design notes that matter on a 32-bit ms counter:
//   1. expired() advances `next_fire_ms_` by exactly one period (not "= now")
//      so there's no drift. If the main loop is briefly busy and misses a
//      tick, the next call catches up to the correct phase.
//   2. The (int32_t)(now - next_fire_ms_) comparison handles wrap-around
//      correctly. The counter wraps every ~49.7 days; a naive `now >=
//      next_fire_ms_` would mis-fire across the wrap.

#ifndef DAISY_CLAUDE_SOFTWARE_TIMER_H
#define DAISY_CLAUDE_SOFTWARE_TIMER_H

#include <stdint.h>

#include "systick.h"  // millis()

class SoftwareTimer {
 public:
  // Construct and start. After construction the timer fires once `period_ms`
  // milliseconds from now.
  explicit SoftwareTimer(uint32_t period_ms)
      : period_ms_(period_ms), next_fire_ms_(millis() + period_ms) {}

  // Returns true if the current period has elapsed. When it returns true,
  // the timer rolls forward by exactly one period so the next firing is at
  // a multiple of the period — no drift even if a call is late.
  bool expired() {
    const uint32_t now = millis();
    if ((int32_t)(now - next_fire_ms_) < 0) {
      return false;
    }
    next_fire_ms_ += period_ms_;
    return true;
  }

  // Resync the "next fire" point to now + period. Use this after the timer
  // has been idle for an arbitrary time (e.g. a long init sequence) so we
  // don't fire repeatedly to catch up.
  void restart() {
    next_fire_ms_ = millis() + period_ms_;
  }

  // Change the period. Does not reschedule the next fire; call restart()
  // if you want the new period to take effect from now.
  void set_period(uint32_t period_ms) {
    period_ms_ = period_ms;
  }

  uint32_t period() const { return period_ms_; }

 private:
  uint32_t period_ms_;
  uint32_t next_fire_ms_;
};

#endif  // DAISY_CLAUDE_SOFTWARE_TIMER_H
