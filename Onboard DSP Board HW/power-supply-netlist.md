# Power Section — Netlist + BOM

**Status:** Draft for schematic entry. Implements `power-supply.md` (topology §3, MCU SMPS §4). Connections are given **by pin name** — take pin *numbers* from each KiCad symbol/datasheet, don't trust memory (mine or yours). Items marked ⚠ go on the netlist-review-gate checklist. **No reference designators in this doc — parts are named by function; KiCad owns annotation.**
**Scope:** charge input (1/4″ jack ring) → TP4054 → BATT → TPS63020 → 3V45_D → TPS7A20 → 3V3_A, plus battery sense, on/off, VDDA feed, and the H725 core-SMPS externals. No USB on the board; no power path — the regulators always draw from the cell.

---

## 1. Nets

| Net | Description |
|---|---|
| `CHG_IN` | ~5 V charge input — the **ring** of the offboard 1/4″ TRS output jack |
| `AUDIO_OUT` | Jack **tip** — DAC output stage via volume pot (owned by `dac-selection.md`, listed here for the connector only) |
| `bat+` | Battery + (onboard cell connector) — charger output node, 3.0–4.2 V (TP4054 has no power path). *As-built name; was `BATT` in this doc's earlier revisions* |
| `VBAT` | **Post-switch** system node: `bat+` → volume-pot integrated switch → `VBAT` → regulator inputs + battery-sense divider. Note: shares its *name* with the MCU's backup-domain VBAT pin but not copper — MCU pin 8 ties to VDD/`3V45_D` (§7 of `pin-allocation.md`) |
| `3V45_D` | Digital rail, 3.45 V (buck-boost output) |
| `3V3_A` | Analog rail, 3.30 V (LDO output) |
| `MCU_VDDA` | 3V3_A after ferrite, MCU VDDA only (no VREF+ pin on the VFQFPN68 — internally tied to VDDA, so this net *is* the ADC reference) |
| `BATT_SENSE` | Divider midpoint → MCU ADC pin |
| *(no EN net)* | The on/off switch is in the battery line (see `VBAT`), so the buck-boost EN ties directly to `VBAT` (always enabled when powered); a 1 MΩ bleed to GND defines the off state |
| `FB_3V45` | TPS63020 feedback divider midpoint |
| `SW_L1`, `SW_L2` | Buck-boost inductor nodes (keep tight, no other loads) |
| `nCHG` | Charger CHRḠ open-drain → charge-indicator LED |
| `VLX_CORE`, `VFB_CORE` | H725 SMPS inductor nodes ⚠ |
| `GND` | Single ground plane (partition by placement, no splits — per board plan) |

## 2. Connections

### Output-jack interface (offboard 1/4″ TRS, chassis-mounted; 3-pin header/JST on the PCB)

| Jack contact | Net / connection |
|---|---|
| Tip | `AUDIO_OUT` (from volume pot / DAC output stage — see `dac-selection.md`) |
| Ring | `CHG_IN` → TVS to GND → charger IN |
| Sleeve | `GND` |

Dual-role ring: a normal TS/TRS audio cable grounds (or passively loads) the ring — the charger input just sits unpowered, which is benign; the special charge cable feeds ~5 V on the ring. **The TVS is the primary protection** — the TP4054's ports withstand ~11 V abs max (⚠ verify on the exact vendor's datasheet; several fabs second-source this part), operating VCC 4.25–6.5 V, so clamp well below that. Keep the `CHG_IN` trace away from `AUDIO_OUT` from the header to the power corner.

### TP4054 — linear CC/CV charger (SOT-23-5)

| Pin | Net / connection |
|---|---|
| VCC | `CHG_IN` + 1 µF to GND (close to pin) |
| BAT | `BATT` + 1 µF to GND (the 10 µF cell bulk also lives on this net) |
| PROG | 2.0 kΩ → GND ⚠ (≈500 mA; ICHG ≈ 1000 V / RPROG — **recompute when cell is chosen**, keep ≤1C) |
| CHRḠ | `nCHG` → 1 kΩ → indicator LED → `CHG_IN` (lights while charging; dark when done or unplugged) |
| GND | `GND` |

No power path, no TS input, no safety timer — that's the simplification being bought (see `power-supply.md` §8 for the run-while-charging caveat this creates). Internal reverse-blocking means no isolation diode and µA-class battery drain when `CHG_IN` is dead. Thermal check ⚠: worst-case dissipation ≈ (5 V − 3.0 V) × 0.5 A = 1 W into a SOT-23-5 — it will thermally fold back on a deeply discharged cell (by design, but slows charging; drop RPROG current if enclosure is hot).

### TPS63020DSJR — buck-boost → 3V45_D

| Pin | Net / connection |
|---|---|
| VIN (both) | `BATT` + 10 µF to GND (at pin) |
| VINA | `BATT` + 0.1 µF to GND |
| EN | `VBAT` (tied to VIN — regulator runs whenever the power switch closes; as-built 2026-07-15) |
| PS/SYNC | `GND` ⚠ (power-save/PFM enabled — verify polarity: GND = PFM on this part) |
| L1 | `SW_L1` → 1.5 µH inductor → `SW_L2` |
| L2 | `SW_L2` |
| VOUT (all) | `3V45_D` + 2× 22 µF to GND |
| FB | `FB_3V45` |
| GND / PGND / PAD | `GND` |

FB divider: `3V45_D` → 590 kΩ → `FB_3V45` → 100 kΩ → GND. Vout = 0.5 V × (1 + 590/100) = **3.45 V**. Both 1 %. ⚠ Confirm 0.5 V FB reference and max-R guidance in the datasheet.

Power switch **(superseded as-built 2026-07-15)**: the switch is the integrated switch on the **volume pot** (the earlier volume-pot candidate won after all; the MCU control pots dropped from three to two — `pin-allocation.md` §6 item 6), and it is a **hard switch in the battery line**: `bat+` → pot switch → `VBAT`. The buck-boost EN ties to `VBAT`, and a 1 MΩ `VBAT` → GND bleed gives a defined off state. The switch now carries the full regulator input current (hundreds of mA peaks at low battery), not µA — **⚠ check the pot-switch current rating**, which the old EN-only scheme made irrelevant.

### TPS7A2033PDBVR — 3V3_A LDO (SOT-23-5)

| Pin | Net / connection |
|---|---|
| IN (1) | `3V45_D` + local 1 µF to GND (at the pin) |
| GND (2) | `GND` |
| EN (3) | `3V45_D` (always on with its input) |
| NC (4) | — |
| OUT (5) | `3V3_A` + local 1 µF to GND |

**Fed directly from `3V45_D` — no boundary filter.** `3V45_D` is already routed into the analog zone to power the codec digital supplies (ADC IOVDD, DAC DVDD), so the LDO simply taps it there. Its PSRR plus the local 1 µF input cap reject the rail's switcher/island noise. A series ferrite + shunt cap was considered and **dropped** — with `3V45_D` present in the zone regardless, it added parts and routing difficulty for negligible gain.

**Place the LDO near its analog loads** (board plan §1: keep the *post*-LDO `3V3_A` run short so the regulated output doesn't re-acquire noise). Feed it from the same `3V45_D` entry that serves the codec IOVDD/DVDD pins; decouple those digital pins locally (per the codec sections) so their switching current loops at the pin. The partition that protects analog performance is at the *signal* level — pickup inputs, MICBIAS, and the AVDD reference kept clear of the digital rails and their returns — not the physical presence of `3V45_D`. 3V3_A distribution caps at each load are in the codec/DAC sections, not here.

### VDDA feed (MCU analog supply + ADC reference)

`3V3_A` → VDDA ferrite (600 Ω @ 100 MHz, 0603) → `MCU_VDDA` → H725 VDDA (pin 16); 1 µF + 0.1 µF to GND at the pin (entered on the MCU sheet's decoupling section).

### Battery sense

`VBAT` → 1 MΩ → `BATT_SENSE` → 1 MΩ → GND; 0.1 µF `BATT_SENSE` → GND. `BATT_SENSE` → MCU PC4 = ADC1_INP4 (pin 47, per `pin-allocation.md` §2). Divide-by-2, full-scale 4.4 V → 2.2 V at ADC, ~2 µA standing drain. **As-built notes (2026-07-15):** the divider hangs on the **post-switch `VBAT`** node, so it reads only while the unit is switched on — no off-state drain, and no high-side disconnect FET needed (closes open item 8 of `power-supply.md`); divider resistors = **1 MΩ as-built** (entry typo fixed 2026-07-23). *(Sense filter cap value still unset — 0.1 µF per this doc.)*

### H725 core-SMPS externals ⚠ (verify wiring against AN5419 / Nucleo-H725 before entry)

| Connection | Net / part |
|---|---|
| VLXSMPS → 2.2 µH inductor → VFBSMPS | `VLX_CORE` / `VFB_CORE` |
| VFBSMPS | 4.7 µF to GND (at pin) |
| VCAP pins | per AN5419 for **SMPS-direct** mode (in this mode VCAP ties to the SMPS output path — confirm exact strap + cap values) ⚠ |
| VDDSMPS / VSSSMPS | `3V45_D` / `GND` with local decoupling per AN5419 |

This block is deliberately under-specified — it is the one part I could not fully verify from memory, and mode-strapping (LDO vs SMPS-direct vs cascade) changes the VCAP wiring. Take it verbatim from the Nucleo-H725 schematic during Phase 2. Belongs physically in the MCU island, not the power corner.

### Test points

See `test-points.md` (single source of truth; categorized by access type). Power-section signals — `CHG_IN`, `bat+`/`VBAT`, `3V45_D`, `3V3_A`, `MCU_VDDA`, `BATT_SENSE`, VCORE (at any VCAP) — are all Cat 3 (touch at a decoupling cap / divider / connector), except GND loops (Cat 1).

## 3. BOM

| Item | Value / Part | Package | LCSC | Notes |
|---|---|---|---|---|
| jack interface header | 3-pin header/JST to offboard TRS jack | THT/SMD | pick | tip/ring/sleeve; jack + volume pot are chassis parts, not on BOM |
| ring TVS | TVS, ~5 V working (SMAJ5.0A class) | SMA/0603 | pick | on `CHG_IN` (jack ring) |
| charger | TP4054 (TPower) | SOT-23-5 | [C382138](https://www.lcsc.com/product-detail/C382138.html) | linear CC/CV charger, proven on prior board |
| charge LED | charge indicator | 0603 | basic | driven by CHRḠ |
| buck-boost | TPS63020DSJR | VSON-14 3×4 | [C15483](https://www.lcsc.com/product-detail/C15483.html) | buck-boost |
| 3V3_A LDO | TPS7A2033PDBVR | SOT-23-5 | [C2862740](https://www.lcsc.com/product-detail/voltage-regulators-linear-low-drop-out-ldo-regulators_texas-instruments-tps7a2033pdbvr_C2862740.html) | 3.3 V low-noise LDO |
| buck-boost inductor | 1.5 µH, ≥3 A sat, shielded | 4×4 mm (XFL4020/SWPA4030 class) | pick at order | buck-boost inductor |
| MCU SMPS inductor | 2.2 µH, ≥0.5 A sat, low DCR | 2520/3030 | pick per AN5419 | H725 core SMPS |
| VDDA ferrite | Ferrite 600 Ω @ 100 MHz (Sunlord GZ1608D601TF) | 0603 | [C1002](https://jlcpcb.com/partdetail/Sunlord-GZ1608D601TF/C1002) | VDDA feed; basic-class, ~200 mA / 450 mΩ DCR (VDDA draws ~2–4 mA) |
| power switch | integrated switch on volume pot | chassis | — | hard on/off in the battery line (`bat+` → `VBAT`); pot itself is a chassis part, see `pin-allocation.md` §6 |
| charger IN/BAT caps | 1 µF X7R 25 V | 0603 | basic | charger VCC + BAT |
| cell bulk / buck-boost VIN | 10 µF X7R ≥10 V | 0805 | basic | BATT bulk / buck-boost VIN |
| misc 0.1 µF | 0.1 µF X7R | 0402 | basic | VINA, battery-sense filter, spare |
| 3V45_D output bulk | 22 µF X5R/X7R ≥10 V (2×) | 0805 | basic | 3V45_D output |
| LDO in/out + VDDA caps | 1 µF X7R ≥10 V | 0402/0603 | basic | LDO in/out, VDDA |
| MCU SMPS VFB cap | 4.7 µF X7R | 0603 | basic | SMPS VFB ⚠ verify value |
| charger PROG | 2.0 kΩ 1 % | 0402 | basic | PROG (≈500 mA) ⚠ recompute w/ cell |
| LED series | 1 kΩ | 0402 | basic | charge-LED series |
| FB divider top | 590 kΩ 1 % | 0402 | basic | buck-boost FB top |
| FB divider bottom | 100 kΩ 1 % | 0402 | basic | buck-boost FB bottom |
| EN/VBAT bleed | 1 MΩ | 0402 | basic | VBAT → GND bleed / off state |
| battery-sense divider | 1 MΩ 1 % (2×) | 0402 | basic | battery sense |
| GND test loops | test point | — | — | Cat 1 only; see `test-points.md` |

Passives are JLCPCB basic-class; exact LCSC codes at order time. The three ICs were stock-checked 2026-07-13 (`power-supply.md` §6).

## 3a. Charger section as built (2026-07-15)

Entered in the schematic with these deltas from §2 above (validated topology — same circuit proven on the prior active-electronics board):

- **As-built symbols/parts:** the charger is drawn with an MCP73811 symbol — pin functions align with the TP4054 SOT-23-5 (1 = CHRḠ/CE open, 2 = GND, 3 = BAT → `bat+`, 4 = VCC → `CHG_IN`, 5 = PROG; ⚠ confirm footprint/pin mapping against the real TP4054 at BOM time). Battery connector = 2-pin; TRS interface = 3-pin (tip → volume-pot wiper `out`, ring → charger VCC, sleeve → GND). The volume pot carries the power switch.
- **PROG:** 30 kΩ → ICHG ≈ 1000 V / 30 k ≈ **33 mA** (⚠ confirm intended — doc's earlier 2.0 kΩ ≈ 500 mA; recompute for the chosen cell, ≤1C).
- **No TVS on the ring** (dropped — field-proven without it) and **no charge LED** (CHRḠ left open).
- **Caps:** 4.7 µF on `CHG_IN`, 4.7 µF on `bat+` (doc had 1 µF + 10 µF bulk; revisit at layout if desired).

## 4. Netlist-gate checklist additions (the ⚠ items)

1. TP4054 RPROG once the cell is chosen (ICHG ≈ 1000 V / RPROG, keep ≤1C); confirm the constant on the exact vendor's datasheet — the part is multi-sourced. **As built: 30 kΩ ≈ 33 mA — confirm.**
2. ~~TP4054 abs-max input vs. TVS clamp voltage~~ **Resolved 2026-07-15: no TVS — circuit field-proven on prior board.**
3. Charger thermal: worst-case ~1 W in SOT-23-5 at 500 mA into a flat cell; confirm foldback behavior is acceptable or reduce ICHG.
4. No TS/thermistor and no safety timer on TP4054 — confirm the chosen cell is acceptable without pack-level protection assumptions (most protected cells are).
5. TPS63020 PS/SYNC polarity for power-save mode; FB reference voltage (0.5 V assumed) and divider max-R guidance.
6. **H725 SMPS block wired verbatim from AN5419/Nucleo-H725** — mode strap, VCAP treatment, L/C values.
7. PCM5102A VIH / input abs-max vs 3.45 V logic; ADC5140 sequencing (carried over from `power-supply.md` open items).
8. **Pot-switch current rating** — the volume pot's integrated switch now hard-switches the battery line (§2 as-built note), carrying full regulator input current.

---

*Schematic-entry status: rails, switch-in-battery-line (volume pot), charger (§3a as-built deltas: 30 kΩ PROG ⚠, no TVS, no charge LED, charger drawn with an MCP73811 symbol standing in for the TP4054), battery-sense divider, VDDA ferrite + caps, and the MCU core-SMPS externals (2.2 µH + 4.7 µF, MCU sheet) are entered. Still missing vs. this doc (re-verified against the netlist 2026-07-24): **buck-boost VIN caps** (10 µF + 0.1 µF at the pins — `VBAT` net currently has zero capacitance, and it sits *after* the switch, so the switcher's input loop has no local reservoir), **3V45_D output capacitance** (as-built 2×4.7 µF vs the 2×22 µF the TPS63020 datasheet assumes — upgrade or justify), the **LDO input cap** (1 µF at the IN pin, fed directly from `3V45_D` — no boundary filter), sense-filter cap value, per-pin AVDD/IOVDD 0.1 µF + analog 10 µF bulk, remaining test points. Battery-sense divider values fixed.*
