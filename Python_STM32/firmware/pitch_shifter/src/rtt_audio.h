#pragma once
#include <stdint.h>

// Call once from main() before audio starts to ensure the RTT control
// block is initialized and visible to J-Link before it scans RAM.
void rtt_audio_init(void);

// Poll for RTT audio-block commands.  Call from the foreground loop.
// No-op if no command is pending.
void rtt_audio_poll(void);
