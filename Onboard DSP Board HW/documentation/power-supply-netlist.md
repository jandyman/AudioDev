# Power Section — Netlist + BOM

**Status:** Draft for schematic entry. Implements `power-supply.md` (topology §3, MCU SMPS §4). Connections are given **by pin name** — take pin *numbers* from each KiCad symbol/datasheet, don't trust memory (mine or yours). Items marked ⚠ go on the netlist-review-gate checklist. **No reference designators in this doc — parts are named by function; KiCad owns annotation.**
**Scope:** charge input (1/4″ jack ring) → charger → cell node → power switch → `VBAT`, from which **two sibling regulators** run: the buck-boost to `3V3_D` and the low-noise LDO to `3V3_A`. Plus battery sense, on/off, VDDA feed, and the H725 core-SMPS externals. No USB on the board; no power path — the regulators always draw from the cell.

**Revised 2026-09-24.** The LDO used to be fed from the buck-boost output and the digital rail used to be 3.45 V. Both changed together; `power-supply.md` §2a carries the reasoning.

---

## 1. Nets

| Net | Description |
|---|---|
| `CHG_IN` | ~5 V charge input — the **ring** of the offboard 1/4″ TRS output jack |
| `AUDIO_OUT` | Jack **tip** — DAC output stage via volume pot (owned by `dac-selection.md`, listed here for the connector only) |
| `bat+` | Battery + (onboard cell connector) — charger output node, 3.0–4.2 V (TP4054 has no power path). *As-built name; was `BATT` in this doc's earlier revisions* |
| `VBAT` | **Post-switch** system node: `bat+` → volume-pot integrated switch → `VBAT` → regulator inputs + battery-sense divider. Note: shares its *name* with the MCU's backup-domain VBAT pin but not copper — the MCU's backup-domain pin ties to VDD/`3V3_D` (§7 of `pin-allocation.md`) |
| `3V3_D` | Digital rail, buck-boost output, **set to 3.25 V** (§2 divider; window and reasoning in `power-supply.md` §6a). **Renamed from `3V45_D`** with the voltage change. The name denotes the 3.3 V logic class; the setpoint is carried in the tables, not the net name |
| `3V3_A` | Analog rail, 3.30 V (LDO output, fed from `VBAT`). Carries the capture converters' analog supplies, **all three** of the playback converter's supplies (analog, charge-pump and digital), the MCU's analog supply via ferrite, and the preamp boards via the pickup connectors |
| `MCU_VDDA` | 3V3_A after ferrite, MCU VDDA only (no VREF+ pin on the VFQFPN68 — internally tied to VDDA, so this net *is* the ADC reference) |
| `BATT_SENSE` | Divider midpoint → MCU ADC pin |
| *(no EN net)* | The on/off switch is in the battery line (see `VBAT`), so the buck-boost EN ties directly to `VBAT` (always enabled when powered); a 1 MΩ bleed to GND defines the off state |
| `FB_3V3` | Buck-boost feedback divider midpoint. **Renamed from `FB_3V45`** with the retarget to 3.25 V |
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

### Buck-boost → 3V3_D (TPS63020DSJR, VSON-14 DSJ)

**Adjustable part retained; rail retargeted to 3.25 V, 2026-09-24.** The fixed 3.3 V sibling was evaluated and rejected on cost and sourcing (`power-supply.md` §6a).

| Pin | Net / connection |
|---|---|
| VIN (both) | `VBAT` + 10 µF to GND (at pin) |
| VINA | `VBAT` + 0.1 µF to GND (datasheet caps this at 0.22 µF) |
| EN | `VBAT` — regulator runs whenever the power switch closes |
| PS/SYNC | `GND` — power-save enabled. **Polarity confirmed** against SLVS916I (pin table: "1 disabled, 0 enabled"; §8: power save is entered with PS/SYNC low) |
| L1 | `SW_L1` → 1.5 µH inductor → `SW_L2` |
| L2 | `SW_L2` |
| VOUT (all) | `3V3_D` + 2× 22 µF to GND |
| FB | `FB_3V3` — divider midpoint (below) |
| PG | `GND` (unused; open-drain). ⚠ Open decision — routing it to a spare GPIO with a pull-up is the natural interlock for the playback soft-mute, and it is free now |
| GND / PGND / PAD | `GND` |

**Divider:** `3V3_D` → **1.10 MΩ** → `FB_3V3` → **200 kΩ** → GND. 0.5 V × (1 + 1100/200) = **3.250 V**. Both ordinary E24 1 % values, low side at the datasheet's specified *"range of 200 kΩ"*.

⚠ **The high-side resistor is the large one, and it runs from the output to the feedback pin.** The board is currently entered with the two transposed, which sets the rail to 0.585 V and stops every device on the board from starting. No automated check catches it, because both arrangements are electrically legal — **put the arithmetic in the schematic as a text note beside the divider.**

**Worst case is setpoint × 1.089** (±1 % reference, ±2 % divider, ±1 % line and load, +5 % power-save lift) = **3.54 V**, against the 3.6 V ceiling on the MCU and capture-converter I/O supplies. Minimum is setpoint × 0.96 = **3.12 V**, against a 3.0 V floor on those same I/O supplies. `power-supply.md` §6a carries why the setpoint sits at the top of its window.

Power switch: the integrated switch on the **volume pot**, a **hard switch in the battery line**: cell node → pot switch → `VBAT`. Both regulators and the sense divider hang off `VBAT`, so off-state draw through the board is zero. The switch carries the full system input current (hundreds of mA peaks at low battery) — **⚠ check the pot-switch current rating.**

### Low-noise LDO → 3V3_A (SOT-23-5)

| Pin | Net / connection |
|---|---|
| IN (1) | **`VBAT`** + local 1 µF to GND (at the pin) |
| GND (2) | `GND` |
| EN (3) | `VBAT` (always on with its input) |
| NC (4) | — genuinely a no-connect on this part; it has no noise-bypass or soft-start pin |
| OUT (5) | `3V3_A` + local 1 µF to GND |

**Fed from the switched battery node, not from the digital rail.** This is the 2026-09-24 change. It must be `VBAT` and never the cell node — the cell node is ahead of the power switch, so an LDO there would drain the battery with the instrument off.

**Why the battery rather than a regulated rail.** No switching converter then appears anywhere upstream of the analog supply. This part's rejection is specified only to 1 MHz (45 dB light load, 40 dB full load) and the buck-boost switches at 2.4 MHz, so feeding the LDO from the switcher asked it to reject a frequency it has no published figure for. `power-supply.md` §2a carries the full trade, including what it costs.

**Headroom.** Worst-case output is 3.350 V (±1.5 % over line, load and temperature) and dropout is 145 mV max at 300 mA, scaling to roughly 50 mV at this board's ~85 mA. Regulation therefore holds down to a cell voltage near **3.39 V**, below which the rail follows the cell at about 40 mV under it. Every device on the rail stays inside its recommended window to a cell voltage of about **3.24 V** — the binding minimum is the playback converter's analog supply at 3.2 V in ground-centred mode; the capture converters are in spec to 3.0 V.

**Thermal.** (4.2 − 3.3) V × 85 mA = 77 mW at full charge, falling to nothing as the cell drains. SOT-23-5 at ~200–250 °C/W gives a 15–19 °C rise. Acceptable, but it makes this the warmest small part in the analog section — **place it away from the bias reference divider and its buffer.**

**Place the LDO near its analog loads**, but route its *input* from `VBAT` along the same path that feeds the buck-boost rather than across the analog island. The partition that protects analog performance is at the signal level — pickup inputs and the bias reference kept clear of digital rails and their returns. 3V3_A distribution caps at each load are in the converter sections, not here.

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
| VDDSMPS / VSSSMPS | `3V3_D` / `GND` with local decoupling per AN5419 |

This block is deliberately under-specified — it is the one part I could not fully verify from memory, and mode-strapping (LDO vs SMPS-direct vs cascade) changes the VCAP wiring. Take it verbatim from the Nucleo-H725 schematic during Phase 2. Belongs physically in the MCU island, not the power corner.

### Test points

See `test-points.md` (single source of truth; categorized by access type). Power-section signals — `CHG_IN`, `bat+`/`VBAT`, `3V3_D`, `3V3_A`, `MCU_VDDA`, `BATT_SENSE`, VCORE (at any VCAP) — are all Cat 3 (touch at a decoupling cap / divider / connector), except GND loops (Cat 1).

## 3. BOM

| Item | Value / Part | Package | LCSC | Notes |
|---|---|---|---|---|
| jack interface header | 3-pin header/JST to offboard TRS jack | THT/SMD | pick | tip/ring/sleeve; jack + volume pot are chassis parts, not on BOM |
| ring TVS | TVS, ~5 V working (SMAJ5.0A class) | SMA/0603 | pick | on `CHG_IN` (jack ring) |
| charger | TP4054 (TPower) | SOT-23-5 | [C382138](https://www.lcsc.com/product-detail/C382138.html) | linear CC/CV charger, proven on prior board |
| charge LED | charge indicator | 0603 | basic | driven by CHRḠ |
| buck-boost | TPS63020DSJR | VSON-14 3×4 (DSJ) | [C15483](https://www.lcsc.com/product-detail/C15483.html) | Adjustable, set to 3.25 V by the divider above |
| 3V3_A LDO | TPS7A2033PDBVR | SOT-23-5 | [C2862740](https://www.lcsc.com/product-detail/voltage-regulators-linear-low-drop-out-ldo-regulators_texas-instruments-tps7a2033pdbvr_C2862740.html) | 3.3 V low-noise LDO |
| buck-boost inductor | 1.5 µH, ≥3 A sat, shielded | 4×4 mm (XFL4020/SWPA4030 class) | pick at order | buck-boost inductor |
| MCU SMPS inductor | 2.2 µH, ≥0.5 A sat, low DCR | 2520/3030 | pick per AN5419 | H725 core SMPS |
| VDDA ferrite | Ferrite 600 Ω @ 100 MHz (Sunlord GZ1608D601TF) | 0603 | [C1002](https://jlcpcb.com/partdetail/Sunlord-GZ1608D601TF/C1002) | VDDA feed; basic-class, ~200 mA / 450 mΩ DCR (VDDA draws ~2–4 mA) |
| power switch | integrated switch on volume pot | chassis | — | hard on/off in the battery line (`bat+` → `VBAT`); pot itself is a chassis part, see `pin-allocation.md` §6 |
| charger IN/BAT caps | 1 µF X7R 25 V | 0603 | basic | charger VCC + BAT |
| cell bulk / buck-boost VIN | 10 µF X7R ≥10 V | 0805 | basic | BATT bulk / buck-boost VIN |
| misc 0.1 µF | 0.1 µF X7R | 0402 | basic | VINA, battery-sense filter, spare |
| 3V3_D output bulk | 22 µF X5R/X7R ≥10 V (2×) | 0805 | basic | Digital-rail output, entered |
| LDO in/out + VDDA caps | 1 µF X7R ≥10 V | 0402/0603 | basic | LDO in/out, VDDA |
| MCU SMPS VFB cap | 4.7 µF X7R | 0603 | basic | SMPS VFB ⚠ verify value |
| charger PROG | 2.0 kΩ 1 % | 0402 | basic | PROG (≈500 mA) ⚠ recompute w/ cell |
| status / charge LED | red, KT-0603R | 0603 | [C2286](https://jlcpcb.com/partdetail/C2286) | Vf 1.8–2.4 V, 300 mcd @ 20 mA, basic-class, 7.6 M stock, $0.007 |
| LED series | 1 kΩ | 0402 | basic | charge-LED series — ≈1.5 mA (≈22 mcd, plainly visible); 2.2 kΩ ≈ 0.7 mA if battery life is preferred |
| FB divider high side | **1.10 MΩ 1 %** | 0402 | basic | Output → feedback pin. Sets 3.25 V with the 200 kΩ low side. ⚠ currently entered transposed with it |
| FB divider low side | **200 kΩ 1 %** | 0402 | basic | Feedback pin → ground. Datasheet specifies the low side in the "range of 200 kΩ" |
| EN/VBAT bleed | 1 MΩ | 0402 | basic | VBAT → GND bleed / off state |
| battery-sense divider | 1 MΩ 1 % (2×) | 0402 | basic | battery sense |
| GND test loops | test point | — | — | Cat 1 only; see `test-points.md` |

Passives are JLCPCB basic-class; exact LCSC codes at order time. The three ICs were stock-checked 2026-07-13 (`power-supply.md` §6).

**Red, not green, and the reason is the rail voltage** — a reason that strengthens now the rail is 3.3 V. A green LED's ~3.0 V Vf leaves only ~0.3 V across the series resistor, so part-to-part Vf spread swings the current several-fold and the brightness with it. Red's ~1.9 V leaves ~1.4 V and a well-defined current. Any future indicator on this rail should follow the same reasoning rather than the colour preference.

## 3a. Charger section as built (2026-07-15)

Entered in the schematic with these deltas from §2 above (validated topology — same circuit proven on the prior active-electronics board):

- **As-built symbols/parts:** the charger is drawn with an MCP73811 symbol — pin functions align with the TP4054 SOT-23-5 (1 = CHRḠ/CE open, 2 = GND, 3 = BAT → `bat+`, 4 = VCC → `CHG_IN`, 5 = PROG; ⚠ confirm footprint/pin mapping against the real TP4054 at BOM time). Battery connector = 2-pin; TRS interface = 3-pin (tip → volume-pot wiper `out`, ring → charger VCC, sleeve → GND). The volume pot carries the power switch.
- **PROG:** 30 kΩ → ICHG ≈ 1000 V / 30 k ≈ **33 mA** (⚠ confirm intended — doc's earlier 2.0 kΩ ≈ 500 mA; recompute for the chosen cell, ≤1C).
- **No TVS on the ring** (dropped — field-proven without it) and **no charge LED** (CHRḠ left open).
- **Caps:** 4.7 µF on `CHG_IN`, 4.7 µF on `bat+` (doc had 1 µF + 10 µF bulk; revisit at layout if desired).

## 4. Netlist-gate verification checklist (the ⚠ items)

These are facts to confirm and values to correct before fab — not open decisions. Topology and parts are settled (`power-supply.md`).

1. TP4054 RPROG once the cell is chosen (ICHG ≈ 1000 V / RPROG, keep ≤1C); confirm the constant on the exact vendor's datasheet — the part is multi-sourced. **As built: 30 kΩ ≈ 33 mA — confirm.**
2. ~~TP4054 abs-max input vs. TVS clamp voltage~~ **Resolved 2026-07-15: no TVS — circuit field-proven on prior board.**
3. Charger thermal: worst-case ~1 W in SOT-23-5 at 500 mA into a flat cell; confirm foldback behavior is acceptable or reduce ICHG.
4. No TS/thermistor and no safety timer on TP4054 — confirm the chosen cell is acceptable without pack-level protection assumptions (most protected cells are).
5. ~~PS/SYNC polarity; feedback reference voltage and divider guidance~~ **Resolved 2026-07-28 against SLVS916I:** PS/SYNC low = power-save enabled (as drawn, correct); FB reference = 500 mV (as assumed, correct); low-side divider resistor specified at ~200 kΩ → **divider revised to 1.18 MΩ / 200 kΩ, update the entered values.**
5a. **Buck-boost input capacitance is missing** — fit 10 µF + 0.1 µF at the VIN/VINA pins. `VBAT` has no local capacitance and sits after the mechanical power switch, so the switcher's input loop currently closes through switch contacts and wiring. TI's reference circuit uses 2× 10 µF input.
5b. ~~Digital-rail output capacitance.~~ Entered at 2× 22 µF.
6. **H725 SMPS block wired verbatim from AN5419/Nucleo-H725** — mode strap, VCAP treatment, L/C values.
7. ~~Playback-converter input levels; capture-converter sequencing.~~ Both closed — all digital signalling is now 3.3 V on both ends, and SBAS892A allows the I/O and analog supplies to come up in any order.
8. **Pot-switch current rating** — the volume pot's integrated switch now hard-switches the battery line (§2 as-built note), carrying full regulator input current.

---

*Schematic-entry status (2026-09-24): rails, switch-in-battery-line (volume pot), charger (§3a as-built deltas: 30 kΩ PROG ⚠, no TVS, no charge LED, charger drawn with an MCP73811 symbol standing in for the TP4054), battery-sense divider, VDDA ferrite + caps, buck-boost input and output capacitance, and the MCU core-SMPS externals are entered.*

*Still to enter, all from the 2026-09-24 rail change:* **LDO input and enable moved to `VBAT`**; **digital rail retargeted to 3.25 V** with the divider corrected to 1.10 MΩ high-side / 200 kΩ low-side (currently transposed); **playback converter's digital supply moved to `3V3_A`**; **net renamed `3V45_D` → `3V3_D`**; **pull-down on the playback soft-mute line**. Carried from before: the LDO input cap (1 µF at its IN pin, now on `VBAT`), sense-filter cap value, per-pin analog/IO 0.1 µF plus analog bulk, remaining test points.
