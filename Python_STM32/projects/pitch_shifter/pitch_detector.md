# Pitch Detector

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

### Note-onset reset

A second input, `reset`, is wired to the attack detector's `trigger`. On each
onset impulse the per-filter period stats (`mu`, `sigma`, `intervals_seen`,
`last_peak_sample`) are cleared so a new note starts from a **clean slate**
instead of the EMA gliding off the previous note's period (which otherwise left
`P` stale — up to ~2.5× wrong — for the first cycles of a note). The biquads and
envelope followers keep running across the reset, so no filter transient is
injected. Because the stats are cleared, `qualified` honestly drops to 0 until
`MIN_INTERVALS_FOR_QUALIFIED` fresh intervals rebuild it (~3 cycles), during
which the loop controller falls back to ungated "newest delay-valid" selection —
preferable to gating on a wrong period.

### Key parameters

`fc_0` / `fc_1` / `fc_2` (per-filter cutoffs), `peak_frac`, `ema_tau_intervals`,
`cleanness_thresh`, `amp_thresh`, `env_fc_hz`, `min_peak_distance_ms`.
