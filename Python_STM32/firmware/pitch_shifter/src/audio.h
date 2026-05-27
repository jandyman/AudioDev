#pragma once
#include <stdbool.h>
#include <stdint.h>

#define AUDIO_SAMPLE_RATE   48000.0f
#define AUDIO_BLOCK_FRAMES  48U
#define AUDIO_BUFFER_WORDS  (2U * AUDIO_BLOCK_FRAMES * 2U)

extern volatile uint32_t audio_irq_count;
bool audio_init(void);
