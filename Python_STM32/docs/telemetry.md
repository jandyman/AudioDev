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
| `audio_build_id` | `u32` | source-fingerprint, published at boot (handshake + liveness) |

`audio_dsp_profile` / `audio_dsp_cycle_ring` are `BARE_METAL`-only (DWT is absent
off-target). The cycle counters are written in `audio_graph_process` around
`process_chunk`; peaks are metered there too.

## Host (`firmware/tools/mem.py`)

`Mem(jlink, map_file)` resolves a symbol from the `.map` (`sym(name)`) and
read/writes target memory via the commands (`read`, `write`, `read_u32`,
`read_f32`, `read_u32_array`, `zero_u32`). Uses `pylink` over RTT — no halt.

The host knows the struct layouts from the code (e.g. `audio_dsp_profile` is
three `u32`s). That coupling is made safe by the build-ID handshake.

## Build-ID handshake

`check_build_id(mem, buildid_file)` reads `audio_build_id` from the target and
compares it to the `.buildid` sidecar emitted next to the `.map`:

- `0` → firmware not booted past init (or not running) — liveness fail.
- `!= sidecar` → the `.map` is from a different build → wrong addresses; **abort**
  ("reflash or rebuild").
- `==` → safe: the running firmware matches the `.map` the host is resolving from.

The build id is a **source fingerprint** computed in the Makefile: a 32-bit hash
of `HEAD` + uncommitted diff + new untracked source names, scoped to the firmware
source trees (so test-audio/output churn doesn't move it). It is emitted to
`build/build_id.h` (compiled in) and `build/<graph>.buildid` (the sidecar), which
are always produced together with the `.map`.

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
