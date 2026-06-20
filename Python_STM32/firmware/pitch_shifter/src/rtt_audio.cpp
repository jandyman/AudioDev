// rtt_audio.cpp — non-realtime audio block verification via RTT.
//
// Protocol (host → target):
//   CMD_AUDIO_INIT  0x10: [cmd][seq]                   disables DMA ISR, re-inits graph
//   CMD_AUDIO_BLOCK 0x11: [cmd][seq][48×4 float32 in]  one chunk in / interleaved L/R out
//   CMD_AUDIO_END   0x12: [cmd][seq]                   re-enables DMA ISR
//   CMD_PEAK_READ   0x20: [cmd][seq]                   read+clear input/output peak
//
// Responses (target → host):
//   INIT/END:  [0x01][seq]
//   BLOCK:     [0x01][seq][48 × (L_f32, R_f32) interleaved]   = 2 + 384 bytes
//   PEAK_READ: [0x01][seq][in_peak f32][out_peak f32]

#include "rtt_audio.h"
#include "audio_graph_runner.h"
#include "SEGGER_RTT.h"
#include "systick.h"
#include "stm32h750xx.h"
#include <string.h>
#include <stdbool.h>
#include <stdint.h>

#define RTT_CH      0
#define BLOCK_N     48
#define BLOCK_BYTES (BLOCK_N * 4)

#define CMD_AUDIO_INIT   0x10u
#define CMD_AUDIO_BLOCK  0x11u
#define CMD_AUDIO_END    0x12u
#define CMD_PEAK_READ    0x20u
#define RESP_ACK         0x01u

static bool s_active = false;

void rtt_audio_init(void) {
  SEGGER_RTT_Init();
}

static bool read_exact(uint8_t* dst, uint32_t n, uint32_t timeout_ms) {
  uint32_t got = 0;
  uint32_t deadline = millis() + timeout_ms;
  while (got < n) {
    unsigned r = SEGGER_RTT_Read(RTT_CH, dst + got, n - got);
    if (r > 0u) {
      got += r;
    } else if (millis() > deadline) {
      return false;
    }
  }
  return true;
}

void rtt_audio_poll(void) {
  if (!SEGGER_RTT_HasData(RTT_CH)) return;

  uint8_t hdr[2];
  if (!read_exact(hdr, 2u, 500u)) return;

  uint8_t cmd = hdr[0];
  uint8_t seq = hdr[1];

  if (cmd == CMD_AUDIO_INIT) {
    NVIC_DisableIRQ(DMA1_Stream1_IRQn);
    s_active = true;
    audio_graph_init(48000);
    uint8_t ack[2] = {RESP_ACK, seq};
    SEGGER_RTT_Write(RTT_CH, ack, 2u);
    return;
  }

  if (cmd == CMD_AUDIO_END) {
    s_active = false;
    NVIC_EnableIRQ(DMA1_Stream1_IRQn);
    uint8_t ack[2] = {RESP_ACK, seq};
    SEGGER_RTT_Write(RTT_CH, ack, 2u);
    return;
  }

  if (cmd == CMD_PEAK_READ) {
    float in_peak  = 0.0f;
    float out_peak = 0.0f;
    audio_graph_peaks_read_and_clear(&in_peak, &out_peak);
    uint8_t resp[2u + 8u];
    resp[0] = RESP_ACK;
    resp[1] = seq;
    memcpy(resp + 2u,     &in_peak,  4u);
    memcpy(resp + 2u + 4u, &out_peak, 4u);
    SEGGER_RTT_Write(RTT_CH, resp, sizeof(resp));
    return;
  }

  if (cmd == CMD_AUDIO_BLOCK && s_active) {
    static uint8_t raw_in[BLOCK_BYTES];
    static float   in_f[BLOCK_N];
    static float   out_l[BLOCK_N];
    static float   out_r[BLOCK_N];
    static uint8_t resp[2u + 2u * BLOCK_BYTES];   // header + interleaved L/R

    if (!read_exact(raw_in, BLOCK_BYTES, 2000u)) return;
    memcpy(in_f, raw_in, BLOCK_BYTES);
    // Non-realtime probe path keeps the mono-in / stereo-out wire protocol,
    // routed through the generic runner (1 input, 2 outputs).
    const float* ins[1]  = { in_f };
    float*       outs[2] = { out_l, out_r };
    audio_graph_process(ins, outs, BLOCK_N);
    resp[0] = RESP_ACK;
    resp[1] = seq;
    // Interleave L/R into resp: [L0][R0][L1][R1]...
    float* out_interleaved = reinterpret_cast<float*>(resp + 2u);
    for (int i = 0; i < BLOCK_N; ++i) {
      out_interleaved[2 * i + 0] = out_l[i];
      out_interleaved[2 * i + 1] = out_r[i];
    }
    SEGGER_RTT_Write(RTT_CH, resp, sizeof(resp));
    return;
  }

  uint8_t nak[2] = {0x02u, seq};
  SEGGER_RTT_Write(RTT_CH, nak, 2u);
}
