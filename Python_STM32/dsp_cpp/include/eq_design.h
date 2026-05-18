// eq_design.h — Generalized biquad filter design: LP, HP, LS, HS, BP, orders 1–4.
//
// filter_design() is a pure function: no I/O, no globals. Call it from the
// foreground (interrupts enabled) — trig is fine here. Pass the resulting
// CascadeCoeffs to FilterChannel::update() or update_with_reset() to apply.
//
// Coefficient convention: a1/a2 stored negated (matches biquad.h / CMSIS convention).
//
// Filter types:
//   LP / HP  — Butterworth cascade, order 1–4.
//              Odd orders: first section is first-order (b2=a2=0).
//   LS / HS  — Shelving filters, order 1–4.
//              2nd-order sections use Butterworth-derived Q values; gain is
//              distributed proportionally to pole count across sections.
//   BP       — Peaking EQ (Audio EQ Cookbook), fixed order 2.
//              gain_db: peak boost/cut; q: Q factor.

#pragma once
#include <stdint.h>
#include "biquad.h"

enum class FilterType : uint8_t { LP, HP, LS, HS, BP };

struct FilterParams {
  FilterType type    = FilterType::LP;
  float fc_hz        = 1000.f;
  float fs_hz        = 48000.f;
  int   order        = 2;       // 1–4 for LP/HP/LS/HS; ignored for BP (always 2)
  float gain_db      = 0.f;     // LS/HS: shelf boost/cut; BP: peak gain; unused for LP/HP
  float q            = 0.7071f; // BP only: Q factor
};

// Fill `out` with biquad coefficients derived from `p`.
// For order changes, caller must use FilterChannel::update_with_reset() to avoid
// stale delay state in unused sections.
void filter_design(const FilterParams& p, CascadeCoeffs& out);
