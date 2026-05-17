#!/usr/bin/env python3
# rtt_params.py — RTT-based parameter control for Daisy_Claude
#
# Requires: pip install pylink-square
#
# No CLI argument parsing — this script is run and debugged directly from
# PyCharm. Edit the calls at the bottom of main() to try different parameters.
# A CLI wrapper can be added later if scripting from the shell becomes useful,
# but for interactive lab work PyCharm's run/debug cycle is faster.
#
# Protocol is defined in src/rtt_protocol.h. What this script does NOT do:
#   - No reconnect loop. If the J-Link isn't attached, the script exits.
#   - No retry beyond one ACK timeout. Intermittent failures are unusual on
#     a bench SWD link; multiple retries would just mask real bugs.
#   - No session keepalive. RTT has no connection concept — the J-Link
#     polls continuously regardless of whether this script is running.
#   These omissions are intentional; the eventual Bluetooth transport will
#   need its own connection management and should not inherit this script's
#   simplicity as a constraint.
#
# Param IDs (must match rtt_protocol.h):
#   0  eq[0].hi_shelf.gain   dB    (-24 .. +24)
#   1  eq[0].hi_shelf.fc     Hz    (1000 .. 20000)
#   2  eq[0].lp.fc           Hz    (20 .. 20000)
#   3  eq[1].hi_shelf.gain   dB    (-24 .. +24)
#   4  eq[1].hi_shelf.fc     Hz    (1000 .. 20000)
#   5  eq[1].lp.fc           Hz    (20 .. 20000)

import struct
import time
import sys

try:
    import pylink
except ImportError:
    sys.exit("pylink-square not installed — run: pip install pylink-square")

# --- Protocol constants (mirror rtt_protocol.h) ---
RTT_CMD_CHANNEL  = 0
CMD_PING         = 0x01
CMD_SET_PARAM    = 0x02
RESP_ACK         = 0x01
RESP_NAK         = 0x02
NAK_BAD_CMD      = 0x01
NAK_BAD_PARAM_ID = 0x02
PARAM_COUNT      = 6

ACK_TIMEOUT_S    = 0.15   # 150 ms — generous for SWD; firmware loop is fast
ACK_POLL_S       = 0.005  # poll every 5 ms while waiting

PARAM_NAMES = [
    "eq[0].hi_shelf.gain (dB)",
    "eq[0].hi_shelf.fc (Hz)",
    "eq[0].lp.fc (Hz)",
    "eq[1].hi_shelf.gain (dB)",
    "eq[1].hi_shelf.fc (Hz)",
    "eq[1].lp.fc (Hz)",
]


def connect(device: str = "STM32H750IB") -> pylink.JLink:
    jlink = pylink.JLink()
    jlink.open()
    jlink.set_tif(pylink.enums.JLinkInterfaces.SWD)
    jlink.connect(device)
    jlink.rtt_start()
    time.sleep(0.1)  # let J-Link scan RAM for the RTT control block
    return jlink


def wait_for_response(jlink: pylink.JLink, expected_seq: int, n_bytes: int = 3):
    """Read n_bytes from up channel; return as bytes, or None on timeout."""
    deadline = time.monotonic() + ACK_TIMEOUT_S
    buf = []
    while time.monotonic() < deadline:
        chunk = jlink.rtt_read(RTT_CMD_CHANNEL, n_bytes - len(buf))
        buf.extend(chunk)
        if len(buf) >= n_bytes:
            return bytes(buf[:n_bytes])
        time.sleep(ACK_POLL_S)
    return None


def ping(jlink: pylink.JLink, seq: int = 1) -> bool:
    pkt = bytes([CMD_PING, seq & 0xFF])
    jlink.rtt_write(RTT_CMD_CHANNEL, list(pkt))
    resp = wait_for_response(jlink, seq)
    if resp is None:
        print(f"PING: timeout (no response within {ACK_TIMEOUT_S*1000:.0f} ms)")
        return False
    if resp[0] == RESP_ACK and resp[1] == (seq & 0xFF):
        print("PING: OK")
        return True
    print(f"PING: unexpected response {resp.hex()}")
    return False


def set_param(jlink: pylink.JLink, param_id: int, value: float, seq: int = 1) -> bool:
    if param_id < 0 or param_id >= PARAM_COUNT:
        print(f"set_param: param_id {param_id} out of range (0..{PARAM_COUNT-1})")
        return False

    val_bytes = struct.pack("<f", value)  # little-endian float, ARM native
    pkt = bytes([CMD_SET_PARAM, seq & 0xFF, param_id & 0xFF]) + val_bytes
    jlink.rtt_write(RTT_CMD_CHANNEL, list(pkt))

    resp = wait_for_response(jlink, seq)
    if resp is None:
        print(f"SET {PARAM_NAMES[param_id]} = {value}: timeout")
        return False
    if resp[0] == RESP_ACK and resp[1] == (seq & 0xFF):
        print(f"SET {PARAM_NAMES[param_id]} = {value}: OK")
        return True
    if resp[0] == RESP_NAK:
        reason = {NAK_BAD_CMD: "BAD_CMD", NAK_BAD_PARAM_ID: "BAD_PARAM_ID"}.get(resp[2], f"0x{resp[2]:02x}")
        print(f"SET {PARAM_NAMES[param_id]} = {value}: NAK ({reason})")
        return False
    print(f"SET {PARAM_NAMES[param_id]} = {value}: unexpected response {resp.hex()}")
    return False


def main():
    jlink = connect()
    try:
        ping(jlink)
        set_param(jlink, param_id=2, value=6000.0)  # left lp.fc = 6000 Hz
    finally:
        jlink.rtt_stop()
        jlink.close()


if __name__ == "__main__":
    main()
