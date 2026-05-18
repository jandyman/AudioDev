// rtt_cmd.cpp — RTT command handler implementation

#include <stdint.h>
#include "SEGGER_RTT.h"
#include "rtt_protocol.h"
#include "params.h"
#include "eq_gen.h"

static uint8_t rx_buf[RTT_CMD_MAX_LEN];
static uint32_t rx_len = 0U;

static uint32_t cmd_expected_len(uint8_t cmd) {
  switch (cmd) {
    case CMD_PING:      return CMD_PING_LEN;
    case CMD_SET_PARAM: return CMD_SET_PARAM_LEN;
    case CMD_GET_PARAM: return CMD_GET_PARAM_LEN;
    default:            return 0U;
  }
}

static void send_ack(uint8_t seq) {
  uint8_t resp[RESP_LEN] = {RESP_ACK, seq, 0x00U};
  SEGGER_RTT_Write(RTT_CMD_CHANNEL, resp, RESP_LEN);
}

static void send_nak(uint8_t seq, uint8_t reason) {
  uint8_t resp[RESP_LEN] = {RESP_NAK, seq, reason};
  SEGGER_RTT_Write(RTT_CMD_CHANNEL, resp, RESP_LEN);
}

// Decompose a flat param_id into [ch][stage][field].
// id = channel*25 + stage*5 + field  (PARAM_COUNT = 50)
static inline int param_ch(uint8_t id)    { return id / (N_GEN_EQ_STAGES * N_GEN_EQ_FIELDS); }
static inline int param_stage(uint8_t id) { return (id / N_GEN_EQ_FIELDS) % N_GEN_EQ_STAGES; }
static inline int param_field(uint8_t id) { return id % N_GEN_EQ_FIELDS; }

static void process_packet(const uint8_t *pkt) {
  uint8_t cmd = pkt[0];
  uint8_t seq = pkt[1];

  switch (cmd) {
    case CMD_PING:
      send_ack(seq);
      break;

    case CMD_SET_PARAM: {
      uint8_t id = pkt[2];
      if (id >= (uint8_t)PARAM_COUNT) { send_nak(seq, NAK_BAD_PARAM_ID); break; }

      // Reassemble float from LE bytes without UB cast through float*.
      uint32_t bits = (uint32_t)pkt[3]
                    | ((uint32_t)pkt[4] << 8U)
                    | ((uint32_t)pkt[5] << 16U)
                    | ((uint32_t)pkt[6] << 24U);
      float val;
      __builtin_memcpy(&val, &bits, sizeof(val));

      int ch    = param_ch(id);
      int stage = param_stage(id);
      int field = param_field(id);

      gen_eq_params[ch][stage][field].value = val;

      // Order and enabled changes require delay-line reset to avoid stale state.
      bool reset = (field == FIELD_ORDER || field == FIELD_ENABLED);
      eq_gen_recompute(ch, stage, reset);

      send_ack(seq);
      break;
    }

    case CMD_GET_PARAM: {
      uint8_t id = pkt[2];
      if (id >= (uint8_t)PARAM_COUNT) { send_nak(seq, NAK_BAD_PARAM_ID); break; }

      int ch    = param_ch(id);
      int stage = param_stage(id);
      int field = param_field(id);

      float val = gen_eq_params[ch][stage][field].value;
      uint32_t bits;
      __builtin_memcpy(&bits, &val, sizeof(bits));
      uint8_t resp[RESP_GET_LEN] = {
        RESP_ACK, seq, 0x00U,
        (uint8_t)( bits         & 0xFFU),
        (uint8_t)((bits >>  8U) & 0xFFU),
        (uint8_t)((bits >> 16U) & 0xFFU),
        (uint8_t)((bits >> 24U) & 0xFFU),
      };
      SEGGER_RTT_Write(RTT_CMD_CHANNEL, resp, RESP_GET_LEN);
      break;
    }

    default:
      send_nak(seq, NAK_BAD_CMD);
      break;
  }
}

extern "C" void rtt_cmd_init(void) {
  SEGGER_RTT_Init();
}

extern "C" void rtt_cmd_poll(void) {
  unsigned n = SEGGER_RTT_Read(RTT_CMD_CHANNEL,
                               rx_buf + rx_len,
                               (unsigned)(sizeof(rx_buf) - rx_len));
  rx_len += (uint32_t)n;

  if (rx_len == 0U) return;

  uint8_t cmd = rx_buf[0];
  uint32_t expected = cmd_expected_len(cmd);

  if (expected == 0U) {
    uint8_t seq = (rx_len >= 2U) ? rx_buf[1] : 0x00U;
    send_nak(seq, NAK_BAD_CMD);
    rx_len = 0U;
    return;
  }

  if (rx_len < expected) return;

  process_packet(rx_buf);

  uint32_t excess = rx_len - expected;
  for (uint32_t i = 0U; i < excess; i++) {
    rx_buf[i] = rx_buf[expected + i];
  }
  rx_len = excess;
}
