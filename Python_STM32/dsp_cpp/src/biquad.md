# Biquad

Direct Form I biquad filter, a 2-section cascade, and Audio EQ Cookbook
coefficient generators. Shared C++ helper (not a graph block) — the processing
core of the EQ stack, paired with [eq_design](eq_design.md) (computes
coefficients) and [param_update](../include/param_update.md) (applies them
IRQ-safely).

## Types

- **`BiquadCoeffs`** — the five coefficients (`b0,b1,b2,a1,a2`), no state.
- **`Biquad`** — Direct Form I section owning a 4-sample delay line. `process(x)`
  is header-inlined (`always_inline`) so the audio ISR pays no call overhead.
- **`BiquadCascade`** — up to `kMaxBiquadSections` (= 2) sections in series, i.e.
  up to 4th order. `process()` is likewise ISR-inlined.
- **`EqChannel`** — a ready-made hi-shelf → low-pass chain with the
  foreground/ISR staging handshake built in.

## Coefficient convention

`a1`/`a2` are stored **negated** relative to the cookbook (they appear with a
minus sign in the difference equation), so `process()` is all additions. This
matches ARM CMSIS-DSP biquad storage.

## Threading model

- `process()` — audio ISR; must inline.
- `recompute()` (`EqChannel`) — foreground main loop; trig is fine here.
- `set_coeffs()` — swaps coefficients **without touching the delay line**, so live
  `fc`/gain changes don't click. `set_coeffs_and_reset()` also zeros the delay
  (use on order changes).
- `apply_new_coefficients()` (`EqChannel`) — ISR-side commit of staged
  coefficients (plain struct assignment).

`sample_rate` is passed explicitly to the generators so the code compiles
identically for STM32 and Mac-native (pybind) targets.
