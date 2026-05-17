# Python_STM32 — Python Layer

All Python for this project lives here. Open this folder as your PyCharm project
root and configure the interpreter to `miniforge3/envs/scipy`.

## Layout

- `tests/` — all scripts: native pybind11, RTT-to-hardware, and cross-comparison
- `bindings/` — pybind11 `.cpp` binding files
- `build/` — Makefiles and compiled `.so` output
- `lib/` — shared utilities (signal generators, analysis helpers) as they accumulate

## Running scripts

All scripts are run directly from PyCharm. Configurable parameters live as named
variables at the bottom of each script. No CLI arguments.

Scripts prefixed `rtt_` require hardware connected via J-Link:

- JLinkGDBServer running: `JLinkGDBServer -device STM32H750IB -if SWD -speed 4000`
  (or launch via STM32CubeIDE's debug session — the RTT port opens automatically)
- `rtt_params.py` only: also needs `pip install pylink-square` (uses J-Link SDK directly, not TCP)

## Building the native pybind11 module

From the `build/` directory in PyCharm's terminal:

```bash
make -f eq.make
```

---

## rtt_wire_test.py

Verifies the `CMD_AUDIO_BLOCK` round-trip with firmware in wire (passthrough) mode.
Sends 200 random `int32` stereo blocks, checks that every returned sample is
bit-identical to what was sent, and reports per-block timing.

**Run from PyCharm** (edit variables at the bottom of the `if __name__` block):
```
host     = 'localhost'
port     = 19021
n_blocks = 200
seed     = 42
```

**Expected output:**
```
[connect] SEGGER J-Link GDB Server ...
[connect] PING ok (attempt 1)
[connect] block size = 48 frames

sending 200 random blocks ...

PASS  200/200 blocks correct
timing  312.4 ms total  |  1.56 ms/block  (1.6x real-time budget of 1.0 ms)
```

The timing line shows the RTT round-trip overhead per block and how it compares
to the 1 ms real-time budget (48 frames × 1/48000 s). Typical measured overhead
with USB-SWD is ~14× real-time — fine for correctness testing, not for playback.

---

## rtt_testbench.py

Processes audio through the STM32 DSP graph block by block and compares or saves
the output. The `RTTTestbench` class wraps connect/disconnect, block send/receive,
and parameter get/set.

Primary use: send a known input through both the native pybind11 build and the
STM32 firmware, then diff the outputs. If they match, the firmware graph is
correct. See `Daisy_Claude/CLAUDE.md` → "Remote DSP Testing Strategy" for the
full rationale.

**Edit variables at the bottom** to choose input file, parameters, and comparison mode.

---

## rtt_params.py

Sets and reads EQ parameters on the running firmware via SEGGER RTT. Uses the
`pylink-square` SDK (direct J-Link API, not TCP) — no JLinkGDBServer needed,
but the J-Link must be connected via SWD.

**Edit the `main()` calls** at the bottom to choose which parameters to read or write.

Param IDs (must match `rtt_protocol.h`):

| ID | Parameter              | Range            |
|----|------------------------|------------------|
| 0  | eq[0].hi_shelf.gain    | −24 .. +24 dB    |
| 1  | eq[0].hi_shelf.fc      | 1000 .. 20000 Hz |
| 2  | eq[0].lp.fc            | 20 .. 20000 Hz   |
| 3  | eq[1].hi_shelf.gain    | −24 .. +24 dB    |
| 4  | eq[1].hi_shelf.fc      | 1000 .. 20000 Hz |
| 5  | eq[1].lp.fc            | 20 .. 20000 Hz   |

---

## Protocol overview

Binary protocol over RTT channel 0, exposed as a raw TCP stream by JLinkGDBServer.
See `firmware/seed_h750/src/rtt_protocol.h` for the authoritative definition.

| Command          | Opcode | Host → STM32               | STM32 → Host              |
|------------------|--------|----------------------------|---------------------------|
| CMD_PING         | 0x01   | `[01][seq]`                | `[01][seq][00]`           |
| CMD_SET_PARAM    | 0x02   | `[02][seq][id][f32 LE]`    | `[01][seq][00]`           |
| CMD_GET_PARAM    | 0x03   | `[03][seq][id]`            | `[01][seq][00][f32 LE]`   |
| CMD_GET_BLOCK_SIZE | 0x04 | `[04][seq]`                | `[01][seq][00][u32 LE]`   |
| CMD_AUDIO_BLOCK  | 0x06   | `[06][seq][N×int32 LE]`    | `[01][seq][00][N×int32 LE]` |

All responses are `[RESP_ACK=0x01][seq][0x00]` on success or `[RESP_NAK=0x02][seq][reason]` on error.
