# Param Update

IRQ-safe parameter-update patterns — the foreground/ISR handshake that lets the
main loop change DSP parameters while the audio interrupt runs, without locks,
flags, or clicks. Shared C++ helper (header-only, not a graph block); the glue
between [eq_design](../src/eq_design.md) and [biquad](../src/biquad.md).

## `AtomicParam<T>`

General-purpose. The foreground calls `apply(s)` to atomically replace `live`; the
ISR reads `live` directly — no flag checks, no branches. The critical section is a
struct copy with IRQ disabled (~20 cycles). Use when `T` is small and replacing
the whole struct (state included) on every update is acceptable.

## `FilterChannel`

Biquad-specific. Owns a `BiquadCascade` (coefficients + delay state); the ISR
calls `cascade.process(x)` directly. The foreground updates via:

- `update(c)` — replace coefficients, **preserve delay state** (no click). For
  `fc`/gain/`Q` changes at constant order.
- `update_with_reset(c)` — replace coefficients **and zero the delay lines**. For
  order changes (at most one block of glitch).

## Platform

IRQ disable/enable is inline `CPSID`/`CPSIE` on Cortex-M7 (`__ARM_ARCH_7EM__`);
inline asm avoids a CMSIS header dependency inside the template body. On the
native macOS (pybind) build it compiles to no-ops — single-threaded, so the copy
needs no IRQ primitives. Same source, both targets.
