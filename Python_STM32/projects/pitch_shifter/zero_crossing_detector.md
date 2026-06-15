Detects positive-going zero crossings in the input, filtered to reject
noise-floor and harmonic crossings. A crossing qualifies when all of:

1. the signal goes negative → non-negative (positive-going only),
2. the short-term amplitude envelope exceeds a minimum threshold, and
3. a minimum time has elapsed since the last qualified crossing.

Tuned for bass guitar — A1 (55 Hz) up to ~311 Hz (periods ~3.2–18.2 ms).

### Key parameters

| name | value | meaning |
|------|-------|---------|
| `min_amplitude` | 0.01 | gate level — above the noise floor, below the softest expected note |
| `min_spacing` | 2.5 ms | minimum gap between crossings; below the shortest fundamental period, so it passes fundamentals up to ~400 Hz while blocking most harmonic crossings |
| `amp_attack` / `amp_release` | 1 / 10 ms | short-term amplitude envelope follower |

The probe outputs expose the amplitude envelope (`amp_env`), the raw
pre-gating crossing (`raw_zc`), and the derivative magnitude at each qualified
crossing (`zc_deriv`).
