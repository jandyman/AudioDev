// rtt_cmd.h — RTT command handler
//
// Call rtt_cmd_init() once after params_init(), then call rtt_cmd_poll()
// on every foreground loop iteration.

#ifndef RTT_CMD_H
#define RTT_CMD_H

#ifdef __cplusplus
extern "C" {
#endif

// Initialise the SEGGER RTT library and build the flat param_id → ParamNode
// lookup table. Must be called after params_init().
void rtt_cmd_init(void);

// Read any pending bytes from the RTT down channel, accumulate into a packet,
// and process one complete command per call. Sends ACK or NAK on the up channel.
void rtt_cmd_poll(void);

#ifdef __cplusplus
}
#endif

#endif // RTT_CMD_H
