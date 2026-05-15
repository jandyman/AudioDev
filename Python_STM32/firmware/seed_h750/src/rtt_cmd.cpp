// rtt_cmd.cpp — RTT command handler implementation

#include <stdint.h>
#include "SEGGER_RTT.h"
#include "rtt_protocol.h"
#include "params.h"

// Flat param_id → ParamNode pointer table, populated by rtt_cmd_init().
static ParamNode *param_table[PARAM_COUNT];

// Accumulator for partial packet reads from the RTT down ring buffer.
// RTT_CMD_MAX_LEN is the size of the longest command (CMD_SET_PARAM = 7 bytes).
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

static void process_packet(const uint8_t *pkt) {
  uint8_t cmd = pkt[0];
  uint8_t seq = pkt[1];

  switch (cmd) {
    case CMD_PING:
      send_ack(seq);
      break;

    case CMD_SET_PARAM: {
      uint8_t id = pkt[2];
      if (id >= (uint8_t)PARAM_COUNT) {
        send_nak(seq, NAK_BAD_PARAM_ID);
        break;
      }
      // Reassemble float from little-endian bytes without a cast through float*
      // (which would be UB). __builtin_memcpy is always available under -ffreestanding.
      uint32_t bits = (uint32_t)pkt[3]
                    | ((uint32_t)pkt[4] << 8U)
                    | ((uint32_t)pkt[5] << 16U)
                    | ((uint32_t)pkt[6] << 24U);
      float val;
      __builtin_memcpy(&val, &bits, sizeof(val));

      param_table[id]->value = val;
      params_dirty_flag.flags |= PARAMS_DIRTY_BIT_DIRTY;
      send_ack(seq);
      break;
    }

    case CMD_GET_PARAM: {
      uint8_t id = pkt[2];
      if (id >= (uint8_t)PARAM_COUNT) {
        send_nak(seq, NAK_BAD_PARAM_ID);
        break;
      }
      float val = param_table[id]->value;
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
  param_table[PARAM_EQ_LEFT_SHELF_GAIN]  = eq_params[0].shelf_gain;
  param_table[PARAM_EQ_LEFT_SHELF_FC]    = eq_params[0].shelf_fc;
  param_table[PARAM_EQ_LEFT_LP_FC]       = eq_params[0].lp_fc;
  param_table[PARAM_EQ_RIGHT_SHELF_GAIN] = eq_params[1].shelf_gain;
  param_table[PARAM_EQ_RIGHT_SHELF_FC]   = eq_params[1].shelf_fc;
  param_table[PARAM_EQ_RIGHT_LP_FC]      = eq_params[1].lp_fc;
}

extern "C" void rtt_cmd_poll(void) {
  // Drain RTT down buffer into local accumulator.
  unsigned n = SEGGER_RTT_Read(RTT_CMD_CHANNEL,
                               rx_buf + rx_len,
                               (unsigned)(sizeof(rx_buf) - rx_len));
  rx_len += (uint32_t)n;

  if (rx_len == 0U) return;

  uint8_t cmd = rx_buf[0];
  uint32_t expected = cmd_expected_len(cmd);

  if (expected == 0U) {
    // Unknown command — discard accumulator and NAK.
    uint8_t seq = (rx_len >= 2U) ? rx_buf[1] : 0x00U;
    send_nak(seq, NAK_BAD_CMD);
    rx_len = 0U;
    return;
  }

  if (rx_len < expected) return;  // partial packet — wait for more bytes

  process_packet(rx_buf);

  // Slide any bytes beyond the current packet to the front of the buffer.
  // Under the ACK/NAK synchronous protocol the host waits for a response
  // before sending the next command, so excess bytes are not expected, but
  // this keeps the accumulator correct if they do arrive back-to-back.
  uint32_t excess = rx_len - expected;
  for (uint32_t i = 0U; i < excess; i++) {
    rx_buf[i] = rx_buf[expected + i];
  }
  rx_len = excess;
}
