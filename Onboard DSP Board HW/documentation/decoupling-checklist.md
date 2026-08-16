# Decoupling Checklist — tick against the schematic

**Purpose:** one place to audit every supply/reference cap against the schematic, because bypass caps are the classic schematic-review blind spot — they're pin→GND stubs with no role in the logical connectivity, so a net/logic review slides right past *absent* ones. Consolidates the per-device decoupling from `adc-netlist.md` §7, `dac-selection.md` §6, `pin-allocation.md` §7, and `power-supply-netlist.md` §2.

**No reference designators** — parts are named by pin/function; KiCad owns annotation. Status column reflects the as-built notes in the source docs as of 2026-07-24.

**Two kinds of cap, don't confuse them:**

- **Supply bypass** (AVDD, IOVDD, VDD, CPVDD, DVDD…) — decouples an *input* rail. Droppable in value but should be present at every supply pin.
- **Mandatory reg/reference output** (AREG, DREG, VREF, MICBIAS, VCAP, LDOO, charge-pump caps) — the *output* cap of an on-chip regulator or reference. **Not optional** — the part is unstable or out of spec without it.

Legend: ☑ entered · ☐ not yet entered · ⚠ value/spec to confirm

---

## ADC codecs — TLV320ADC5140 (×2, per device)

| Pin | Rail / role | Cap | Kind | Status |
|---|---|---|---|---|
| AVDD (1) | analog supply (`3V3_A`) | 0.1 µF at pin | supply bypass | ☐ per-pin 0.1 µF not yet entered |
| — | analog bulk (shared across the pair, on `3V3_A`) | 10 µF | supply bulk | ☐ not yet entered |
| IOVDD (19) | digital-I/O supply (`3V45_D`) | 0.1 µF at pin | supply bypass | ☐ per-pin 0.1 µF not yet entered |
| AREG (2) | on-chip 1.8 V analog reg output | 1 µF to AVSS | **mandatory output** | ☑ entered |
| VREF (3) | reference | ≥1 µF to AVSS | **mandatory output** | ☑ entered |
| DREG (24) | on-chip 1.5 V core reg output | 1 µF to GND | **mandatory output** | ☑ entered |
| MICBIAS (5) | preamp supply reg output | 1 µF to AVSS | **mandatory output** | ☑ entered |

Notes: AREG abs-max 2.0 V — never tie to `3V3_A`. AVDD/IOVDD per-pin 0.1 µF + the shared 10 µF are the **main open gap** (both devices).

## DAC — PCM5102A

| Pin | Rail / role | Cap | Kind | Status |
|---|---|---|---|---|
| CPVDD (1) | charge-pump / analog supply (`3V3_A`) | 0.1 µF at pin | supply bypass | ⚠ confirm entered |
| — | analog bulk (shared on `3V3_A`, CPVDD side) | 10 µF | supply bulk | ⚠ confirm entered |
| AVDD (8) | analog supply (`3V3_A`) | 0.1 µF at pin | supply bypass | ⚠ confirm entered |
| DVDD (20) | digital-core supply (`3V45_D`, 3.45 V ⚠) | 0.1 µF at pin; bulk folds into the digital rail's 10 µF | supply bypass | ⚠ confirm entered; DVDD-on-3.45 V spec check (`dac-selection.md` §8) |
| LDOO (18) | internal 1.8 V LDO output | 0.1 µF to GND | **mandatory output** | ⚠ confirm entered |
| CAPP/CAPM (2/4) | charge-pump flying cap | 2.2 µF across the pair | **mandatory** | ⚠ confirm entered |
| VNEG (5) | −3.3 V charge-pump rail | 2.2 µF to GND | **mandatory output** | ⚠ confirm entered |

Charge-pump caps (flying + VNEG) closest to the device. Single ground plane — each cap takes its own via(s).

## MCU — STM32H725RGV6

| Pin(s) | Rail / role | Cap | Kind | Status |
|---|---|---|---|---|
| VDD (pads 9, 22, 35, 51, 68) | digital core/IO supply (`3V45_D`) | 100 nF one per pin + 4.7 µF bulk | supply bypass | ☑ entered (per-pin placement at layout) |
| VDDSMPS (pad 6) | core-SMPS input (`3V45_D`) | ≥1× 100 nF ≤~2 mm from the pin via + 4.7 µF ≤~5 mm (coverage rule, `layout-notes.md` §5.1) | supply bypass | ☑ entered |
| VFBSMPS (pad 7) | core-SMPS feedback | 4.7 µF at pin; 2.2 µH inductor VLXSMPS→VFBSMPS | **mandatory (SMPS)** | ☑ entered |
| VCAP (pads 33, 49, 66) | core-domain cap (LDO disabled) | 100 nF each | **mandatory output** | ☑ entered |
| VDDA (pad 16) | analog supply / ADC ref (`MCU_VDDA` via VDDA ferrite from `3V3_A`) | 100 nF + 1 µF at pin | supply bypass | ☑ entered |
| NRST (pad 12) | reset | 100 nF to GND | filter | ☑ entered |
| BOOT0 (pad 63) | boot strap | 10 kΩ pull-down | strap | ☑ entered |

## Power section (supply-rail bypass)

| Node | Cap | Status |
|---|---|---|
| charger VCC | 1 µF | ☑ entered (as-built 4.7 µF) |
| charger BAT / cell bulk | 1 µF + 10 µF cell bulk | ☑ entered (as-built 4.7 µF) |
| buck-boost VIN | 10 µF + 0.1 µF at the pins | ☐ **not yet entered** — `VBAT` (post-switch) currently has zero capacitance; switcher input loop has no local reservoir |
| buck-boost VOUT (`3V45_D`) | 2× 22 µF | ⚠ as-built 2× 4.7 µF vs datasheet 2× 22 µF — upgrade or justify |
| LDO IN (`3V45_D`) | 1 µF at pin | ☐ **not yet entered** |
| LDO OUT (`3V3_A`) | 1 µF at pin | ☐ **not yet entered** |
| VDDA feed | VDDA ferrite + 100 nF + 1 µF at the MCU VDDA pin | ☑ entered |

---

## Priority gaps (as of 2026-07-24)

1. **ADC per-pin AVDD/IOVDD 0.1 µF + shared 10 µF** (both devices) — the decoupling that surfaced this checklist. ☐
2. **Buck-boost VIN caps** (10 µF + 0.1 µF) — the switcher input loop has no local reservoir. ☐
3. **LDO in/out 1 µF caps.** ☐
4. **`3V45_D` output bulk** — 2× 4.7 µF → 2× 22 µF upgrade (or justify). ⚠
5. **DAC supply/charge-pump caps** — confirm the full set entered; resolve DVDD-on-3.45 V spec check. ⚠

Mandatory reg/reference output caps (ADC AREG/VREF/DREG/MICBIAS, MCU VCAP, DAC charge-pump/LDOO/VNEG) are the ones that must never be dropped for part-count — verify each is present before layout.
