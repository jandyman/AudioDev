# OpenOCD Setup Recipe — Remote Parameter Inspection

This is the complete workflow discovered for running param_walker.py and inspecting the parameter tree on the running firmware.

## Hardware Setup

- Daisy Seed Rev 4 with STM32H750IBK6
- Daisy Pod Rev 5 (optional, for audio I/O)
- ST-Link debugger (built into the Daisy Pod, or standalone)

## Software Requirements

1. **Firmware built:** `eq/build/eq.elf` (and corresponding `eq.map`)
2. **OpenOCD installed:** `brew install openocd` (or STM32CubeIDE's bundled openocd)
3. **Python 3.12+** in the scipy conda environment

## Workflow

### 1. Build and Flash the Firmware

```bash
cd firmware/eq
make clean && make
# Flash via CubeIDE or command-line
```

### 2. Start OpenOCD (in a separate terminal)

```bash
openocd -f interface/stlink.cfg -f target/stm32h7x.cfg
```

You should see output like:
```
Info : Listening on port 6666 for tcl connections
Info : Listening on port 4444 for telnet connections
Info : clock speed 1800 kHz
```

**Key point:** OpenOCD will connect to the ST-Link and stay running. It doesn't need the CubeIDE debugger; in fact, CubeIDE's debugger will **conflict** if running at the same time (both try to claim the USB device). So:
- ✅ Start OpenOCD in terminal, leave running
- ❌ Do NOT start CubeIDE debugger (they conflict)
- ✅ Firmware runs normally on the target

### 3. Run param_walker.py

From PyCharm or CLI:

```bash
# From PyCharm: tools/ folder open as project, hit play button
# Or from CLI:
python3 tools/param_walker.py
```

The script will:
1. Find `param_anchor` in the .map file (0x20000024)
2. Connect to OpenOCD telnet on localhost:4444
3. **Check if CPU is halted; if so, resume it** (so audio isn't interrupted)
4. Read the parameter tree from DTCMRAM
5. Display the hierarchy and current values
6. Keep the target running (no halt/resume cycle)

### 4. Firmware Stays Running

Unlike the CubeIDE debugger (which pauses execution), param_walker reads memory while the firmware is live and the audio is flowing. This is safe because:
- DTCMRAM bypasses the D-cache (no coherency issues)
- Parameter reads are atomic (one 32-bit word at a time)
- The ISR can safely run while reads happen

## Troubleshooting

**"Connection refused on localhost:4444"**
- Is OpenOCD running? Check the terminal where you started it.
- Did CubeIDE's debugger claim the USB device? Stop the CubeIDE debug session first.

**"Target was halted"**
- param_walker detects this and automatically resumes the firmware.
- If you manually halted it in OpenOCD telnet, just type `resume` and hit enter.

**Audio glitches or pauses**
- The script shouldn't interfere (it doesn't halt the CPU), but if it does, it's likely a socket timeout issue. See below.

**Script hangs or times out**
- The telnet socket timeout handling is still under development.
- From PyCharm, you can step through to debug. Set a breakpoint in `_cmd()` to see what's happening.
- From CLI, Ctrl+C to exit. OpenOCD stays running (safe).

## Under the Hood

**Why OpenOCD telnet instead of GDB remote?**
- STM32CubeIDE's embedded OpenOCD doesn't expose GDB port (3333) properly.
- The telnet interface (4444) is more reliable and easier to debug.

**Why not use CubeIDE's debugger?**
- CubeIDE claims the USB device exclusively. OpenOCD can't run at the same time.
- We want non-invasive memory inspection while audio flows.

**Why DTCMRAM?**
- Directly-attached TCM (Tightly Coupled Memory) on the Cortex-M7.
- Bypasses the L1 D-cache, so host memory reads are immediately visible.
- No cache invalidation needed.

## Future Enhancements

- [ ] Improve socket timeout handling (current bottleneck)
- [ ] Add optional `--halt` flag if you want to stop the CPU
- [ ] Add parameter write support (not yet tested)
- [ ] Build macOS SwiftUI app on top of this working protocol

## References

- OpenOCD manual: http://openocd.org/doc/html/
- STM32H750 reference manual (RM0433)
- Daisy Seed pinout and schematics in `hardware/seed/`
