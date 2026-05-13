// rtt_protocol.h — binary command protocol over SEGGER RTT channel 0
//
// Transport model: RTT gives two independent byte streams. J-Link polls
// the target's ring buffers in the background via SWD without halting the CPU.
// The firmware reads commands from the down buffer (host→target) and writes
// responses to the up buffer (target→host) in the foreground loop.
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
// Protocol scope — what this deliberately does NOT include:
//   - Keepalive / heartbeat. RTT has no connection concept; the J-Link always
//     polls. There is no disconnect event to detect or handle.
//   - Session state. The firmware processes commands identically at powerup
//     or after 10 minutes of silence.
//   - Sequence number validation on the firmware side. seq is echoed in
//     responses so the host can correlate ACKs when pipelining. The firmware
//     does not check ordering or detect duplicates.
//   - Retransmit. Python retries once on ACK timeout, then gives up.
//   - Checksums or framing guards. This is a closed, trusted lab-bench tool.
//   - None of the above applies to the eventual Bluetooth transport, which
//     will need its own security and reliability layer. The command/ACK
//     structure here is shaped to map cleanly onto BLE UART or a GATT
//     characteristic when that transport is added.

#ifndef RTT_PROTOCOL_H
#define RTT_PROTOCOL_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define RTT_CMD_CHANNEL   0U   // same RTT channel for both up and down

// Command IDs (host → target)
#define CMD_PING          0x01U
#define CMD_SET_PARAM     0x02U
#define CMD_GET_PARAM     0x03U   // reserved — not yet implemented in firmware

// Response IDs (target → host)
#define RESP_ACK          0x01U
#define RESP_NAK          0x02U

// NAK reason codes
#define NAK_BAD_CMD       0x01U   // unrecognised command byte
#define NAK_BAD_PARAM_ID  0x02U   // param_id >= PARAM_COUNT

// Packet lengths in bytes
#define CMD_PING_LEN       2U
#define CMD_SET_PARAM_LEN  7U
#define CMD_GET_PARAM_LEN  3U
#define RESP_LEN           3U    // all normal ACK/NAK responses
#define RESP_GET_LEN       7U    // ACK to CMD_GET_PARAM (includes float)

// Maximum command length — used to size the firmware accumulator buffer.
#define RTT_CMD_MAX_LEN    CMD_SET_PARAM_LEN

// Flat parameter IDs — must match the EQ parameter tree in params.h.
// The ordering is fixed; adding a new parameter always appends to avoid
// breaking the host-side mapping.
typedef enum {
  PARAM_EQ_LEFT_SHELF_GAIN  = 0,
  PARAM_EQ_LEFT_SHELF_FC    = 1,
  PARAM_EQ_LEFT_LP_FC       = 2,
  PARAM_EQ_RIGHT_SHELF_GAIN = 3,
  PARAM_EQ_RIGHT_SHELF_FC   = 4,
  PARAM_EQ_RIGHT_LP_FC      = 5,
  PARAM_COUNT               = 6,
} ParamId;

#ifdef __cplusplus
}
#endif

#endif // RTT_PROTOCOL_H
