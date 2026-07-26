# Test Points — Multichannel ADC/DAC Board

**Status:** Consolidated from the scattered TP lists in `pin-allocation.md` §9, `adc-netlist.md` §9, and `power-supply-netlist.md`. Categorized to minimize dedicated-TP real estate. ⚠ items need a bench/package call before layout.

**Supersedes** the per-doc test-point lists — treat this file as the single source of truth for what gets a physical pad.

## Categorization scheme

Three categories, by *what kind of access the signal needs* — not just importance:

- **Category 1 — wire-loop pad.** Super important, looked at often. Wants a pad big enough to solder a wire or a bent wire loop to (semi-permanent scope/monitor lead, or scope-clip ground).
- **Category 2 — probe pad / via.** Hard-to-reach signal — unrealistic to land a scope probe otherwise (runs chip-to-chip between leadless packages). Occasional access; a small landing pad or exposed via is enough.
- **Category 3 — no dedicated TP.** Reachable by touching one side of an SMT passive, a connector pin, or a probeable IC lead. Listed here for reference with the touch point, but **not** given board real estate.

## Package reachability (the deciding factor)

| Part | Package | Leads probeable? |
|---|---|---|
| STM32H725RGV6 (MCU) | VFQFPN68, 8×8 mm, 0.4 mm pitch, exposed pad | **No** — leadless |
| TLV320ADC5140 ×2 (ADC) | 24-WQFN 4×4 (RTW) | **No** — leadless |
| PCM5102A (DAC) | TSSOP-20 | **Yes** — gull-wing leads, ~0.65 mm pitch ⚠ confirm you're comfortable probing |

Consequence: an MCU-only net with no series/pull passive is unreachable and needs a pad. An MCU↔ADC net is unreachable at **both** ends. An MCU↔DAC net is reachable **at the DAC lead**.

---

## Category 1 — wire-loop pads

| # | Signal / net | Pin · Pad | Why Cat 1 |
|---|---|---|---|
| 1 | **GND** ×2–3 | — | Scope ground reference for every measurement; bent wire loops for clip-on grounds. Distribute one near the MCU, one near the codec/analog corner, one near the DAC output. |
| 2 | **MCO1** | PA8 · 43 | Clock-tree / PLL health (HSE→PLL3 lock). Checked at every bring-up and after any clock change. MCU pin is leadless, so it has no other access — a dedicated pad is mandatory, and it earns a wire loop for repeat use. |

*Optional promotions:* if you want permanent rail monitors rather than hunting for a decoupling cap, promote `3V45_D` and `3V3_A` (Cat 3 below) to Cat 1 loops. Low cost, your call.

---

## Category 2 — probe pad / via (otherwise unreachable)

The ADC TDM bus runs from the leadless MCU to the leadless ADC pair — **no probeable endpoint anywhere on the net.** These need pads. ⚠ **Not yet in the schematic** (netlist check 2026-07-24): entered so far are TP1 (MCO1), TP11 (MICBIAS_A), TP12–14 (GND) — add TP symbols for the three bus nets below before layout completion.

| # | Signal / net | Pin · Pad | Runs | Also called |
|---|---|---|---|---|
| 3 | **SAI4_SCK_B** | PA2 · 19 | MCU → ADC5140 ×2 BCLK | `BCLK_ADC` |
| 4 | **SAI4_FS_B** | PC0 · 13 | MCU → ADC5140 ×2 FSYNC | `FSYNC_ADC` |
| 5 | **SAI4_SD_B** | PA0 · 17 | ADC5140 ×2 → MCU (shared SDOUT bus) | `SDOUT_ADC` |

### ⚠ Pending your package assessment — DAC bus + XSMT

These run MCU → PCM5102A. The **DAC end is TSSOP (probeable)**, so if you're OK landing a fine tip / micro-clip on 0.65 mm leads, they drop to **Category 3** (no pad). If not, they're **Category 2** and need pads:

| Signal / net | Pin · Pad | DAC pin | Verdict |
|---|---|---|---|
| `I2S1_CK` (BCK) | PA5 · 24 | PCM5102A BCK | Cat 3 if you probe the TSSOP lead; else Cat 2 |
| `I2S1_WS` (LRCK) | PA4 · 23 | PCM5102A LRCK | " |
| `I2S1_SDO` (DIN) | PA7 · 26 | PCM5102A DIN | " |
| `DAC_XSMT` | PC9 · 42 | PCM5102A XSMT (pin 17) | Static line — verify low→high at startup once; Cat 3 at the DAC lead, else Cat 2 |

---

## Category 3 — no dedicated TP (touch a passive / lead / connector)

Reachable without dedicated board area. Recorded here so nothing is lost from the old lists.

| Signal / net | Where to touch it |
|---|---|
| `3V45_D` (digital rail) | C101 / C104 4.7 µF output caps (⚠ 2×22 µF per power doc still pending) |
| `3V3_A` (analog rail) | LDO **U1** output side — C12/C13 as-built (1 µF output cap still to add) |
| `MCU_VDDA` | C37 / C38 / FB1 |
| VCORE | VCAP caps C90–C92 (near MCU) |
| `bat+` / `VBAT` | bulk cap C23 / connector J3; post-switch `VBAT` at U2 VIN (⚠ VIN caps still to add) |
| `CHG_IN` | charger input cap C30 / jack ring J4.2 (no TVS as-built; D1 is the *status* LED, not a TVS) |
| `BATT_SENSE` | R12/R13 divider midpoint |
| `I2C1_SCL` | R2 pull-up (to 3V45_D) |
| `I2C1_SDA` | R1 pull-up |
| `CODEC_SHDNZ` | R18 10 kΩ pull-down (MCU sheet) |
| `MICBIAS_A` / `MICBIAS_B` | C_micbias 1 µF caps (to AVSS); also on J1/J2 buffer headers |
| ADC input line (one per device) | INxP blocking cap (4.7 µF tantalum) / DNP C_emi shunt pad |
| DAC OUTL (post-pad) | L-pad resistors / volume pot RV3 / output jack |
| `SAI4_MCLK_B` reserve | PA1 · 18 — DNP; already a reserve pad, populate only if MCLK ever needed |

---

## Summary count

- **Category 1 (wire loops):** GND ×2–3 + MCO1 → ~3–4 pads.
- **Category 2 (probe pads):** 3 (ADC TDM bus) + up to 4 more (DAC bus + XSMT) pending the TSSOP-probe call → **3–7 pads.**
- **Category 3:** 0 dedicated pads.

Worst case ~11 pads; best case ~6 if the DAC lines are probed at the TSSOP leads.

## Open items

1. ⚠ **DAC-bus probeability** — confirm whether probing PCM5102A TSSOP leads is acceptable; decides Cat 2 vs Cat 3 for `I2S1_CK/WS/SDO` and `DAC_XSMT` (4 potential pads).
2. GND loop placement — one per region (MCU / analog / DAC output).
3. Decide whether to promote `3V45_D` / `3V3_A` to Cat 1 monitor loops.
