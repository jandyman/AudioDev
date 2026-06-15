A bank of low-pass filters with per-filter cleanness scoring and a selector that
emits a trusted period estimate `P` (and its spread `sigma_sel`) for the loop
controller. Its job is to avoid the octave/harmonic errors a raw zero-crossing
period count makes on a harmonically-rich bass note.

Per filter *k* (`NUM_FILTERS` = 3, ascending cutoff):

- 2nd-order Butterworth LPF (causal biquad) + a one-pole envelope follower on `|x_filt|`.
- Tall-peak detection: local maxima of `x_filt` above `peak_frac × env_filt`, with a minimum spacing.
- An EMA over inter-tall-peak intervals → `mu` (period, samples) and `sigma` (std).
- `cleanness = 1 / (1 + sigma/mu)` and `amplitude = env_filt / env_raw`.

### Selection

The selector picks the **lowest-cutoff** filter that clears all of:
`cleanness ≥ cleanness_thresh`, `amplitude ≥ amp_thresh`, and at least
`MIN_INTERVALS_FOR_QUALIFIED` (3) observed intervals (so the EMA has settled).
The selected `mu` becomes `P`, and `qualified` goes to 1. The loop controller
uses `P` for its integer-multiple loop-length gate, falling back to
"newest delay-valid" when `qualified` is 0.

### Outputs

Beyond the selector outputs (`selected_filter`, `P`, `sigma_sel`, `qualified`),
every per-filter intermediate is exposed as a probe — `x_filt_k`, `env_filt_k`,
`tall_peak_k`, `mu_k`, `sigma_k`, `cleanness_k`, `amplitude_k` — for diagnosis.

### Key parameters

`fc_0` / `fc_1` / `fc_2` (per-filter cutoffs), `peak_frac`, `ema_tau_intervals`,
`cleanness_thresh`, `amp_thresh`, `env_fc_hz`, `min_peak_distance_ms`.
