// rtt_audio.cpp — RTT command channel: non-realtime audio-block verification
// plus generic target-memory read/write (used for telemetry).
//
// Protocol (host → target):
//   CMD_AUDIO_INIT  0x10: [cmd][seq]                   disables DMA ISR, re-inits graph
//   CMD_AUDIO_BLOCK 0x11: [cmd][seq][48×4 float32 in]  one chunk in / interleaved L/R out
//   CMD_AUDIO_END   0x12: [cmd][seq]                   re-enables DMA ISR
//   CMD_READ_MEM    0x20: [cmd][seq][addr u32][len u16]            read len bytes @ addr
//   CMD_WRITE_MEM   0x21: [cmd][seq][addr u32][len u16][len bytes] write len bytes @ addr
//   CMD_SET_PARAM   0x22: [cmd][seq][nlen u8][name nlen][value f32] set graph param live
//
// Responses (target → host):
//   INIT/END/WRITE_MEM/SET_PARAM: [0x01][seq]
//   BLOCK:              [0x01][seq][48 × (L_f32, R_f32) interleaved]   = 2 + 384 bytes
//   READ_MEM:           [0x01][seq][len bytes]
//
// The CPU performs the memory access, so reads of cacheable RAM are D-cache
// coherent (unlike a debugger reading SRAM directly). The host resolves the
// telemetry symbol addresses (cycle profile struct, cycle ring, peaks, build id)
// from the .map. See docs/telemetry.md.

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
#define CMD_READ_MEM     0x20u
#define CMD_WRITE_MEM    0x21u
#define CMD_SET_PARAM    0x22u
#define RESP_ACK         0x01u
#define MAX_MEM_LEN      1000u   // fits the 1 KB RTT up-buffer with header

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

  if (cmd == CMD_READ_MEM) {
    uint8_t req[6];
    if (!read_exact(req, 6u, 500u)) return;
    uint32_t addr; uint16_t len;
    memcpy(&addr, req,      4u);
    memcpy(&len,  req + 4u, 2u);
    if (len > MAX_MEM_LEN) len = MAX_MEM_LEN;
    static uint8_t resp[2u + MAX_MEM_LEN];
    resp[0] = RESP_ACK;
    resp[1] = seq;
    memcpy(resp + 2u, (const void*)(uintptr_t)addr, len);   // CPU read → cache-coherent
    SEGGER_RTT_Write(RTT_CH, resp, 2u + len);
    return;
  }

  if (cmd == CMD_WRITE_MEM) {
    uint8_t req[6];
    if (!read_exact(req, 6u, 500u)) return;
    uint32_t addr; uint16_t len;
    memcpy(&addr, req,      4u);
    memcpy(&len,  req + 4u, 2u);
    if (len > MAX_MEM_LEN) len = MAX_MEM_LEN;
    static uint8_t data[MAX_MEM_LEN];
    if (len && !read_exact(data, len, 2000u)) return;
    memcpy((void*)(uintptr_t)addr, data, len);
    uint8_t ack[2] = {RESP_ACK, seq};
    SEGGER_RTT_Write(RTT_CH, ack, 2u);
    return;
  }

  if (cmd == CMD_SET_PARAM) {
    uint8_t nlen;
    if (!read_exact(&nlen, 1u, 500u)) return;
    static char name[256];                         // nlen is u8, so always fits
    if (nlen && !read_exact((uint8_t*)name, nlen, 500u)) return;
    name[nlen] = '\0';
    uint8_t valbuf[4];
    if (!read_exact(valbuf, 4u, 500u)) return;
    float value;
    memcpy(&value, valbuf, 4u);
    // The audio ISR reads loop_controller's pitch_ratio/derived constants; bracket
    // the live update so it can't observe a half-applied set. The store is a few
    // float ops, so the interrupt-off window is sub-microsecond.
    __disable_irq();
    audio_graph_set_param(name, value);
    __enable_irq();
    uint8_t ack[2] = {RESP_ACK, seq};
    SEGGER_RTT_Write(RTT_CH, ack, 2u);
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
