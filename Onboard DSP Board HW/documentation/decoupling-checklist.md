# Decoupling Checklist — tick against the schematic

**Purpose:** one place to audit every supply/reference cap against the schematic, because bypass caps are the classic schematic-review blind spot — they're pin→GND stubs with no role in the logical connectivity, so a net/logic review slides right past *absent* ones. Consolidates the per-device decoupling from `adc-netlist.md` §7, `dac-selection.md` §6, `pin-allocation.md` §7, and `power-supply-netlist.md` §2.

**No reference designators** — parts are named by pin/function; KiCad owns annotation. Status column checked against the saved board 2026-11-11; distances are pad centre to pad centre.

**Two kinds of cap, don't confuse them:**

- **Supply bypass** (AVDD, IOVDD, VDD, CPVDD, DVDD…) — decouples an *input* rail. Droppable in value but should be present at every supply pin.
- **Mandatory reg/reference output** (AREG, DREG, VREF, MICBIAS, VCAP, LDOO, charge-pump caps) — the *output* cap of an on-chip regulator or reference. **Not optional** — the part is unstable or out of spec without it.

Legend: ☑ on the board · ☐ not on the board · ⚠ open question (risk-list item named)

---

## ADC codecs — TLV320ADC5140 (×2, per device)

| Pin | Rail / role | Cap | Kind | Status |
|---|---|---|---|---|
| AVDD (1) | analog supply (`3V3_A`) | 0.1 µF at pin | supply bypass | ☑ 0.1 µF at 1.6–1.8 mm, both devices |
| — | analog bulk (shared across the pair, on `3V3_A`) | 10 µF | supply bulk | ☑ two 10 µF on the rail, 6–7 mm from the converters |
| IOVDD (19) | digital-I/O supply (`3V3_D`) | 0.1 µF at pin | supply bypass | ☑ as-built 1 µF at each pin (1.2 and 2.6 mm) in place of 0.1 µF |
| AREG (2) | on-chip 1.8 V analog reg output | 10 µF to AVSS | **mandatory output** | ☑ 10 µF at 1.8–2.0 mm (raised from 1 µF 2026-11-13) |
| VREF (3) | reference | ≥1 µF to AVSS | **mandatory output** | ☑ 1 µF at 1.8 mm |
| DREG (24) | on-chip 1.5 V core reg output | 10 µF to GND | **mandatory output** | ☑ 10 µF at 1.3–1.4 mm (raised from 1 µF 2026-11-13) |
| MICBIAS (5) | preamp supply reg output | none | — | not used: the preamps run from `3V3_A`; pin left open, output never enabled |

Notes: AREG abs-max 2.0 V — never tie to `3V3_A`.

## DAC — PCM5102A

| Pin | Rail / role | Cap | Kind | Status |
|---|---|---|---|---|
| CPVDD (1) | charge-pump / analog supply (`3V3_A`) | 0.1 µF at pin | supply bypass | ☑ 1.1 mm |
| — | analog bulk (shared on `3V3_A`, CPVDD side) | 10 µF | supply bulk | ☑ 2.6 mm |
| AVDD (8) | analog supply (`3V3_A`) | 0.1 µF at pin | supply bypass | ☑ 1.7 mm |
| DVDD (20) | digital-core supply (**`3V3_A`, 3.30 V** — moved off the digital rail 2026-09-24; maximum 3.46 V, `dac-selection.md` §8) | 0.1 µF at pin; bulk folds into the analog rail's bulk | supply bypass | ☑ 1.9 mm |
| LDOO (18) | internal 1.8 V LDO output | 0.1 µF to GND | **mandatory output** | ⚠ as-built 2.2 µF at 1.6 mm — risk list AUD-11 |
| CAPP/CAPM (2/4) | charge-pump flying cap | 2.2 µF across the pair | **mandatory** | ☑ 2.2 mm |
| VNEG (5) | −3.3 V charge-pump rail | 2.2 µF to GND | **mandatory output** | ☑ 1.7 mm |

Charge-pump caps (flying + VNEG) closest to the device. Single ground plane — each cap takes its own via(s).

## MCU — STM32H725RGV6

| Pin(s) | Rail / role | Cap | Kind | Status |
|---|---|---|---|---|
| VDD (pads 9, 22, 35, 51, 68) | digital core/IO supply (`3V3_D`) | 100 nF one per pin + 4.7 µF bulk | supply bypass | ☑ 100 nF at 1.2–2.6 mm of every pin |
| Backup-domain supply (pad 1) | tied to `3V3_D` | shares the VDD capacitors | supply bypass | ☑ 100 nF at 1.4 mm |
| VDDSMPS (pad 6) | core-SMPS input (`3V3_D`) | ≥1× 100 nF ≤~2 mm from the pin via + 4.7 µF ≤~5 mm (coverage rule, `layout-notes.md` §5.1) | supply bypass | ⚠ 100 nF at 3.0 mm, 4.7 µF at 6.0 mm — slightly outside the rule; risk list AUD-31 |
| VFBSMPS (pad 7) | core-SMPS output | 2 × 10 µF at the inductor output; 2.2 µH inductor VLXSMPS→VFBSMPS | **mandatory (SMPS)** | ☑ 2 × 10 µF at 5.5 and 7.0 mm (at the inductor) |
| VCAP (pads 33, 49, 66) | core supply input in direct-SMPS mode | 100 nF each, all three on the SMPS output net | **mandatory** | ☑ 100 nF at 1.6–2.1 mm of each pin; joined to the SMPS output 2026-11-11 |
| VDDA (pad 16) | analog supply / ADC ref (`MCU_VDDA` via VDDA ferrite from `3V3_A`) | 100 nF + 1 µF at pin | supply bypass | ☑ 3.8 and 4.8 mm |
| NRST (pad 12) | reset | 100 nF to GND | filter | ☑ |
| BOOT0 (pad 63) | boot strap | 10 kΩ pull-down | strap | ☑ |

## Power section and the rest (supply-rail bypass)

| Node | Cap | Status |
|---|---|---|
| charger supply input | 1 µF | ☑ as-built 4.7 µF at 1.5 mm (voltage rating to confirm — risk list AUD-30) |
| charger battery pin / cell node | 1 µF + 10 µF cell bulk | ☑ as-built 4.7 µF at 1.7 mm; no separate 10 µF on the cell side of the switch |
| buck-boost power input (`VBAT`) | 10 µF + 0.1 µF at the pins | ⚠ both fitted, neither at the power-input pins (10 µF through ≈12 mm of trace) — risk list AUD-26. The control-supply pin has the 0.1 µF at 1.9 mm |
| buck-boost output (`3V3_D`) | 2 × 22 µF | ☑ at 2.3 and 4.4 mm, plus 4.7 µF |
| analog LDO input (`VBAT`) | 1 µF at pin | ☑ 1 µF + 100 nF at 2.1–2.8 mm |
| analog LDO output (`3V3_A`) | 1 µF at pin | ☑ 1 µF at 1.9 mm, 10 µF at 2.5 mm |
| VDDA feed | VDDA ferrite + 100 nF + 1 µF at the MCU VDDA pin | ☑ |
| reference buffer amplifier supply (`3V3_A`) | 0.1 µF at pin | ☐ none; nearest capacitor on the rail ≈8 mm — risk list AUD-29 |
| radio module supply (`3V3_D`) | none | by decision — no room, module carries its own (`bluetooth-constraints.md`) |

---

## Open (all tracked in `dsp-board-audit-risk-list.md`)

2. **Buck-boost input capacitor placement** (AUD-26).
3. **Core-SMPS input coverage** (AUD-31).
4. **Playback-converter internal-regulator capacitor** — 2.2 µF against 0.1 µF (AUD-11).
5. **Reference buffer bypass** (AUD-29).

Mandatory reg/reference output caps (ADC AREG/VREF/DREG, MCU VCAP, DAC charge-pump/LDOO/VNEG) are the ones that must never be dropped for part-count.
