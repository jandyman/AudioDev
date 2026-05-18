// rtt_protocol.h — binary command protocol over SEGGER RTT channel 0
//
// Transport model: RTT gives two independent byte streams. J-Link polls
// the target's ring buffers via SWD without halting the CPU. The firmware
// reads commands from the down buffer (host→target) and writes responses
// to the up buffer (target→host) in the foreground loop.
//
// Down packet format (host → target):
//   CMD_PING:      [cmd=0x01][seq]                               2 bytes
//   CMD_SET_PARAM: [cmd=0x02][seq][param_id][f0][f1][f2][f3]    7 bytes
//   CMD_GET_PARAM: [cmd=0x03][seq][param_id]                     3 bytes
//
//   f0..f3 are the float value in little-endian byte order (ARM native).
//
// Up packet format (target → host):
//   RESP_ACK: [resp=0x01][seq][0x00]    3 bytes
//   RESP_NAK: [resp=0x02][seq][reason]  3 bytes
//
//   For CMD_GET_PARAM, ACK carries the value appended:
//   [resp=0x01][seq][0x00][f0][f1][f2][f3]  7 bytes
//
// Param ID encoding (PARAM_COUNT = 50):
//   param_id = channel*25 + stage*5 + field
//     channel: 0=L, 1=R
//     stage:   0=LP, 1=HP, 2=LS, 3=HS, 4=BP
//     field:   0=enabled, 1=fc_hz, 2=order, 3=gain_db, 4=q
//
// The firmware decomposes the flat id via integer arithmetic; the host
// encodes via the same formula. No named enum needed on either side.

#ifndef RTT_PROTOCOL_H
#define RTT_PROTOCOL_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define RTT_CMD_CHANNEL   0U

// Command IDs (host → target)
#define CMD_PING          0x01U
#define CMD_SET_PARAM     0x02U
#define CMD_GET_PARAM     0x03U

// Response IDs (target → host)
#define RESP_ACK          0x01U
#define RESP_NAK          0x02U

// NAK reason codes
#define NAK_BAD_CMD       0x01U
#define NAK_BAD_PARAM_ID  0x02U

// Packet lengths in bytes
#define CMD_PING_LEN       2U
#define CMD_SET_PARAM_LEN  7U
#define CMD_GET_PARAM_LEN  3U
#define RESP_LEN           3U
#define RESP_GET_LEN       7U

#define RTT_CMD_MAX_LEN    CMD_SET_PARAM_LEN

// 2 channels × 5 stages × 5 fields = 50
#define PARAM_COUNT        50U

#ifdef __cplusplus
}
#endif

#endif // RTT_PROTOCOL_H
