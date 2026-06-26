# Firmware Telemetry — generic memory read/write over RTT

How the host reads firmware state (DSP cycle costs, peaks, …) while audio runs.
Deliberately minimal: two generic RTT commands + symbol resolution from the
`.map`. No registry, no per-stat protocol code.

## The two commands (`rtt_audio.cpp`)

```
CMD_READ_MEM  0x20: [cmd][seq][addr u32][len u16]            → [ACK][seq][len bytes]
CMD_WRITE_MEM 0x21: [cmd][seq][addr u32][len u16][len bytes] → [ACK][seq]
```

The firmware's foreground RTT poll loop services these by `memcpy`ing its own
memory. **The CPU performs the access, so reads of cacheable RAM are D-cache
coherent** — the key reason this is CPU-mediated rather than the host reading
SRAM directly over J-Link (which the param tree only gets away with because it
lives in non-cached DTCM). Length is capped at `MAX_MEM_LEN` (1000 B) to fit the
1 KB RTT up-buffer.

`WRITE_MEM` is used to zero a peak/max for windowed meters ("value since last
poll"), and is available for runtime parameter writes later.

## Telemetry symbols (`audio_graph_runner.cpp`)

Global (non-`static`) so they appear as clean symbols in the `.map`:

| symbol | type | meaning |
|---|---|---|
| `audio_in_peak` / `audio_out_peak` | `float` | running peak \|x\|; host zeroes to window |
| `audio_dsp_profile` | `{u32 last, u32 max, u32 block_count}` | per-block DSP cycle cost (DWT) |
| `audio_dsp_cycle_ring` | `u32[128]` | per-block cost time-series (circular; head = `block_count`) |
| `audio_image_crc` | `u32` | CRC-32 of the firmware's own flash image, computed at boot (handshake + liveness) |

`audio_dsp_profile` / `audio_dsp_cycle_ring` are `BARE_METAL`-only (DWT is absent
off-target). The cycle counters are written in `audio_graph_process` around
`process_chunk`; peaks are metered there too.

## Host (`firmware/tools/mem.py`)

`Mem(jlink, map_file)` resolves a symbol from the `.map` (`sym(name)`) and
read/writes target memory via the commands (`read`, `write`, `read_u32`,
`read_f32`, `read_u32_array`, `zero_u32`). Uses `pylink` over RTT — no halt.

The host knows the struct layouts from the code (e.g. `audio_dsp_profile` is
three `u32`s). That coupling is made safe by the image-CRC handshake.

## Image-CRC handshake

`check_image_crc(mem, bin_file)` reads `audio_image_crc` from the target and
compares it to a CRC of the local `build/<graph>.bin`:

- `0` → firmware not booted past init (or not running) — liveness fail.
- `!= bin CRC` → the running firmware is a different binary than this `.map`/`.bin`
  → wrong addresses; **abort** ("reflash or rebuild").
- `==` → safe: the running firmware IS this build, so the `.map` addresses are valid.

The id is a **CRC of the actual binary image**, not a source fingerprint. At boot
the firmware CRCs its own flash image — exactly the bytes `objcopy` emits as
`<graph>.bin`, the range `[ORIGIN(FLASH), _eidata)` from the linker script — using
CRC-32/ISO-HDLC (`crc32_iso_hdlc()` in `main.cpp`, bit-for-bit identical to Python's
`zlib.crc32`). The result lives in `.bss` (RAM), so it is not part of the CRC'd
image — no self-reference. The host CRCs `<graph>.bin` the same way and compares.

Because the id is the binary itself, it tracks **everything** that changes the
binary — source, compiler flags, optimization level, toolchain version — and is
idempotent: rerunning `make` with no changes yields the same binary, same CRC, no
spurious mismatch. There is no compiled-in `build_id.h` and no `.buildid` sidecar;
the `.bin` is the single artifact the host needs. (The opt level is fixed in the
Makefile's `OPT`; because every object depends on `$(MAKEFILE_LIST)`, editing it
forces a full rebuild and the CRC follows.)

## Tools

- `cycle_timeseries.py` — reads `audio_dsp_cycle_ring`, plots per-block cost vs the
  1 ms / 480k-cycle deadline; derives baseline / YIN burst / period.
- `cycle_meter.py` — live `last`/`max` % of budget (zeroes `max` each poll).
- `peak_meter.py` — live in/out dBFS (zeroes peaks each poll).

## Why no registry (and when we'd add one)

A self-describing registry (names/types/offsets enumerated over the wire) would
let a host with **no `.map`** discover and read gauges — the right thing when
firmware ships to third parties. Until then it's complexity we don't need: with
the `.map` as the source of truth and the build-ID handshake guarding it, generic
`READ_MEM` already makes "expose a new stat" a one-line change (add the global,
read it by symbol). Revisit the registry at the release/self-describing phase.
