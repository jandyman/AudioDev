# EQ Design

Generalized biquad filter design. Shared C++ helper (not a graph block) — turns a
human-facing `FilterParams` into the `CascadeCoeffs` consumed by
[biquad](biquad.md)'s `BiquadCascade`, applied via
[param_update](../include/param_update.md)'s `FilterChannel`.

## API

`void filter_design(const FilterParams& p, CascadeCoeffs& out);` — a **pure
function** (no I/O, no globals). Call it from the foreground (interrupts enabled);
trig is fine there. Hand the resulting `CascadeCoeffs` to
`FilterChannel::update()` (or `update_with_reset()` on an order change).

`FilterParams`: `type`, `fc_hz`, `fs_hz`, `order` (1–4), `gain_db`, `q`.

## Filter types

- **LP / HP** — Butterworth cascade, order 1–4. Odd orders make the first section
  first-order (`b2=a2=0`).
- **LS / HS** — shelving, order 1–4. 2nd-order sections use Butterworth-derived
  `Q`; gain is distributed proportionally to pole count across sections.
- **BP** — peaking EQ (Audio EQ Cookbook), fixed order 2. `gain_db` = peak
  boost/cut, `q` = Q factor.

Coefficient convention (`a1`/`a2` stored negated) matches [biquad](biquad.md). On
an order change the caller must use `FilterChannel::update_with_reset()` so unused
sections don't keep stale delay state.
