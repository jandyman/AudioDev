# Profiling Discipline — STM32 capability assessment

How we establish *measured* (not estimated) cycle costs for the pitch shifter and
future algorithms. The instrument is the telemetry harness (see `telemetry.md`);
this doc is the methodology that uses it.

Status: seeded from the first measurement pass. Steps 1–2 below are pending; the
methodology (steps 3+) is the starting point to flesh out.

## Why measure, not estimate

Analytical cycle estimates have proven unreliable (the first YIN estimate was
~3× low, almost entirely the `-Og` penalty, and was quoted without the
optimization caveat). Cost is governed by optimization level, the FMA pipeline,
cache behaviour, memory layout, and data-dependent paths — none analytically
tractable, and none that compose across changes. So:

- Estimates are for **rough early ballparks only**, always flagged low-confidence.
- The DWT cycle profiler is nearly free (a couple of instructions per block), so
  it stays **wired in permanently** as a budget smoke-detector.
- Capability is a **profile with cliffs** (e.g. the YIN burst), answered on demand
  as the design moves — not a single calibrated number.

## Build configurations (not mixed-level)

Two whole-image configs via the Makefile `OPT` override — never per-file `-O`
mixing (that fights whole-program / Faust optimization):

- **Debug:** `-Og -g3` (default) — step the control/orchestration code.
- **Ship / measure:** `-O3 -g3` (`make OPT='-O3 -g3'`) — what ships *and* what we
  profile. Measuring at `-Og` would mislead planning; measure at ship level.

## First numbers (baseline, `-Og`, pending clock verification)

- Peak ~44% of the 1 ms / 480k-cycle budget (~211k cyc), every ~5 ms = the YIN
  brute-force search firing.
- Baseline ~20% (~96k cyc) = everything else (decimator FIR + LPF + attack +
  delay + mixer + loop_controller). The decimator FIR is the prime suspect.
- Caveat: the % assumes 480 MHz. Verify empirically — `process_audio` is
  DMA-paced at exactly 1 ms/block, so the CYCCNT delta between two blocks *is*
  core_clock ÷ 1000 (~480k → 480 MHz; ~400k → throttled, free headroom in VOS).

## Per-stage attribution (the breakdown technique)

Faust is **not** an obstacle: it optimizes *within* each block (separate `.dsp` →
separate generated `.cpp`); it does not optimize across our blocks. Boundaries are
erased only if the C++ compiler inlines them — and for our **chunk-based loop
blocks the boundaries survive anyway**, because each block loops over the buffer
and the next block reads its output (a true memory dependency the compiler can't
fuse across). A `volatile` CYCCNT read between blocks is therefore nearly
perturbation-free.

Two methods, used together:

1. **In-place boundary bracketing** (cheap, in-context): `graph_compiler` emits a
   CYCCNT read between each block call in the generated `process_chunk`,
   accumulating per-stage costs into an array exposed as one more telemetry
   symbol. Gives the baseline split under real cache conditions.
2. **Block-isolation micro-benchmark** (clean cross-check): loop one block over a
   buffer N times at `-O3` on-target, read DWT, divide. Observer-effect-free.
   The architecture already supports this — blocks are standalone units
   (`projects/yin/` built this way).

**Validity test:** sum of per-stage ≈ measured whole-pipeline cost. Agreement →
attribution is real; whole > sum → the gap is cross-block cache/interaction cost.

## Burstiness handling (deferred — decide only after `-O3` numbers)

If the burst still matters after `-O3`:

- **Incremental YIN, sliced by sample-position** (preferred): spread the search
  over the next N samples of processing rather than per-48-sample-block. Keyed to
  sample count, native (one big chunk) and STM32 (48/block) run identical slices
  at identical sample indices → bit-exact parity preserved (`rtt_verify` still
  passes); only P-latency shifts a few ms (negligible vs the ~50 ms YIN settle).
  Single-context, no scheduler. Flattens 44% spike → ~25% flat.
- **RTC scheduler / threading** (reserve): fully decouples the search but makes
  P-availability scheduler-latency-dependent, which breaks native parity unless
  that latency is *modelled deterministically* in the native build — the
  generalized hard problem. Justify only when soft-real-time work accumulates.

## Next steps

1. Diagnose & fix the `-O3` whole-image boot fault (bisect with temporary
   per-file `-O3` to localize the TU, then root-cause — likely strict-aliasing in
   generated/DSP code; first probe `-O2 -fno-strict-aliasing`). Required for ship
   *and* honest measurement.
2. Re-measure peak + baseline at `-O3`, clock verified; quantify the gain vs `-Og`.
3. Flesh out per-stage attribution (the `graph_compiler` probe), then decide the
   burst question on measured `-O3` numbers.
