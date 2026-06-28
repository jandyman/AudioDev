# YIN Pitch Detector — Design & Implementation Plan

Standalone, reusable pitch-detection block. **Build and test it in isolation
first**, then integrate into the pitch shifter. This doc is the implementation
spec — a fresh session should be able to build from it directly.

## Why

The pitch shifter's current detector is a fixed LPF bank (60/120/240 Hz) with
per-band tall-peak interval tracking. On a descending bass line into low E it
fails systematically (validated on `test_audio/Fourth Test.wav`, see table
below): it is biased ~10–20 % high on mid-low notes and **locks to the 2nd
harmonic** (reports ~2× the true frequency) on the lowest, 2nd-harmonic-dominant
notes. That wrong period drives the loop clock at half the true period → the read
parks in waveform troughs → an audible ~80 ms amplitude dropout (~5 s into Fourth
Test).

A **YIN** estimator (de Cheveigné & Kawahara, 2002) is robust to exactly this
case — it keys on the *whole waveform repeating at the period*, not on the
fundamental sinusoid's amplitude, so a weak fundamental under a strong 2nd
harmonic doesn't fool it. YIN-on-full-rate already recovers the true F0 on every
Fourth Test note (it's the ground truth in the table below). Pitch detection is
needed in essentially every future project, so a clean, optimized YIN is a
cross-project asset worth building properly.

## Key design decisions (settled in discussion — do not relitigate)

- **Decimated, brute-force YIN — no FFT.** Decimation shrinks BOTH the window and
  the lag range, so YIN's O(W·τ) difference function gets ~factor² cheaper
  (÷16 ≈ 256× cheaper). That makes it trivially affordable (~1 M mults/s/string),
  even for the future 4-strings-on-¼-of-an-M7 case, with none of the FFT
  block-framing machinery. (FFT-accelerated YIN is possible later but not needed.)
- **Latency ≈ 2–3 cycles of the LOWEST note** (window must span the longest
  period). ~50–75 ms at 41 Hz. A fixed, known bound; fits the post-attack budget.
- **Decimation loses per-frame precision but it doesn't matter:** parabolic
  interpolation recovers sub-sample precision, and averaging successive frames
  over a sustained note drives jitter down √N. We need the *steady* period, which
  averages out clean.
- **The decimator is a deliberate, verified sub-block** — its anti-alias response
  is the one thing we measure rather than trust.
- **It belongs in C++, not Faust** (data-dependent search: first-dip-below-
  threshold, argmin, interpolation — Faust is poor at this). Same reasoning that
  put `pitch_detector` in C++. Only the decimation filter *could* be Faust.

## The algorithm

### Decimator (front end)
Anti-alias LPF + downsample by **N (power of two)**. Start at **÷16** (44100 →
2756 Hz, Nyquist 1378 Hz; covers the ~40–320 Hz bass fundamentals plus several
harmonics for a sharp difference function). Fall back to ÷8 (5512 Hz) if accuracy
needs more harmonic content — decide in test. Structure: cascade of halfband ÷2
stages (efficient) or a single windowed-sinc FIR. **Verify the magnitude response
+ alias rejection in the Python test.**

### YIN core (on the decimated ring buffer)
1. **Difference function** over lag range [τ_min, τ_max]:
   `d(τ) = Σ_j (x[j] − x[j+τ])²`. τ_max from the lowest note (~35–40 Hz),
   τ_min from the highest (~320 Hz), at the decimated rate.
2. **Cumulative mean normalized difference:**
   `d'(τ) = d(τ) / [(1/τ) Σ_{k=1..τ} d(k)]`, with `d'(0)=1`.
3. **Absolute threshold:** take the *first* τ whose dip falls below ~0.10–0.15
   (prefers the true fundamental over the half-period 2nd-harmonic dip); else the
   global min of d'. This is the octave-error fix — the crux.
4. **Parabolic interpolation** around the chosen dip → sub-sample period.
5. Output **P** (fractional samples at full rate) and an **aperiodicity /
   confidence** value = the d' value at the dip (low = confident/periodic).

Run at **control rate** (every few ms / every N chunks), not per sample.

## Block structure

Standalone C++ block + pybind module, tested whole-file in Python first.

- Owns its **decimated ring buffer** (size = window, power of two → bitmask wrap).
- **Chunk-aware from day one:** maintains decimator + ring state across chunks;
  emits P at control rate. The pybind can feed one big chunk (whole-file,
  Matlab-style) OR chunk-by-chunk (realistic) — same code path.
- **Outputs / probes:** `P` (or frequency), `confidence`, the decimated signal,
  and the `d'(τ)` curve — so we can see *why* it picks what it picks (signal-node
  probing convention).
- Conform to the project block conventions (`.graph` block def, pybind wrapper,
  thin `.make` including `../../python/graph_build.mk`). Re-read
  `docs/audio_graph_architecture.md` and use `projects/pitch_shifter/
  pitch_detector.{h,cpp}` as the C++-block template. No dynamic allocation in the
  processing path; static member arrays.
- Promote to **`dsp_cpp/`** once proven (cross-project reuse).

## Power-of-two & chunk coupling

- **Decimation factor:** power of two (halfband cascade).
- **Ring buffer length:** power of two → wrap with `idx & (N−1)` (no division).
- **Analysis window:** any length for brute-force YIN; power-of-two only matters
  if FFT-accelerating later (free hedge to keep it 2ᵏ).
- **Hard coupling:** chunk size must be a multiple of the decimation factor (whole
  decimated samples per chunk). Powers of two on both → automatic. Otherwise YIN
  is decoupled from chunk size (it owns its window); chunk size only bounds how
  often P can update.

## Test plan & targets

1. **Synthetic:** pure tones + deliberately weak-fundamental / 2H-dominant
   signals (fundamental 10 dB below 2H) at known F0 across 35–320 Hz. Verify P,
   measure error vs. decimation factor and window length, confirm the threshold
   step kills octave errors.
2. **Real:** the bass files, especially `Fourth Test.wav`. Score the BLOCK's P
   (decimated, chunked, C++) against the known true F0s below. **It must report
   the true fundamental on notes 7–8 where the filter bank locked to 2×.**
3. **Decimator:** verify magnitude response + alias rejection.
4. **Latency:** measure time-to-valid-estimate after an onset; confirm ~2–3
   lowest-note cycles.
5. Reuse / adapt `projects/pitch_shifter/pitch_detector_validate.py` (it already
   computes YIN ground truth + per-note 2H-vs-fundamental levels).

### Fourth Test.wav target table (true F0 = YIN-on-full-rate ground truth)
```
 note  onset   true   old-pd  ratio   verdict
   0   0.000   82.9    82.3   0.99    ok
   1   0.104   83.1    82.9   1.00    ok
   2   0.925   73.7    73.6   1.00    ok
   3   1.671   65.9    73.1   1.11    biased high
   4   2.422   62.2    69.4   1.12    biased high (2H-dominant)
   5   3.190   55.2    62.9   1.14    biased high (2H-dominant)
   6   3.997   49.1    57.4   1.17    biased high (2H-dominant)
   7   4.780   46.5    96.2   2.07    WRONG — 2H lock  <-- the ~5s dropout
   8   5.566   41.4    69.7   1.68    WRONG
   9   7.803   49.1    68.1   1.39    WRONG (qual 46%)
  10   7.904   49.2    60.9   1.24    biased high
  11   8.705   46.4    50.0   1.08    ok-ish
  12   9.530   41.3    49.4   1.20    biased high
```

## Integration (LATER — out of scope for the standalone block)

Once the block reports true P reliably, it can **drive the loop controller
directly**, replacing the whole peak-clock apparatus (`pd.selected_peak`, the `zc`
block, the target-latency *candidate search*). The realization (settled in
discussion): with a precise period and **small jumps**, we do NOT need splice
phase / peak locations — jumping the read by an integer multiple of P preserves
phase by periodicity, and adjacent cycles are near-identical, so the crossfade
pans between near-duplicates. So loop logic collapses to: jump by **k·P** (small
k), enforce a **≥ one-cycle lockout** between loops, claw back latency gradually
via several small jumps rather than one big one. This also structurally fixes both
the trough-parking dropout and the earlier 2-period sawtooth. But: **standalone
block first — it just outputs P. Integration is a separate step.**

## Build order

1. Scaffold `projects/yin/`: block `.h/.cpp`, `.graph` block def, pybind wrapper,
   thin `.make`, a `yin_demo.py` (whole-file + probe plots).
2. Decimator + ring buffer; verify response in Python.
3. YIN core; verify on synthetic signals.
4. Validate on Fourth Test against the table above; tune decimation factor,
   window, threshold.
5. Measure latency. Then (separate task) plan integration into the loop controller.

## References / conventions

- YIN: de Cheveigné & Kawahara, "YIN, a fundamental frequency estimator for speech
  and music," JASA 111(4), 2002.
- Project block conventions: `docs/audio_graph_architecture.md`, root + project
  `.claude/CLAUDE.md`, `projects/pitch_shifter/pitch_detector.{h,cpp}` as template.
- Build: `source ~/miniforge3/etc/profile.d/conda.sh && conda activate scipy`,
  then `make -f <graph>.make` from the project dir.
