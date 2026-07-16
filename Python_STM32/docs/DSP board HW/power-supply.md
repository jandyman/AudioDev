# Power Supply — 3V3_A / 3V3_D from 1S Li-ion

**Status:** In discussion — topology recommended, parts proposed but not finalized. Resolves the regulator portion of Phase 0 item 4 of `multichannel-audio-board-plan.md`, and **§4 amends Phase 0 item 1** (MCU variant: H723 → H725 for the internal core SMPS). Charger/power-path and on/off strategy are touched on but decided separately.
**Scope:** everything between the battery/charger system node and the two 3.3 V-class rails: the digital rail (MCU, codec IOVDD/DVDD, future BT module) and the analog rail (ADC5140 AVDD ×2, PCM5102A CPVDD/AVDD, MCU VDDA/VREF+) — plus the MCU core-domain supply choice, which turns out to be the biggest battery-life lever on the board.

---

## 1. Requirements

- Single 3.7 V Li-ion cell (onboard) → regulator input **3.0–4.2 V**. Charger is a **TP4054** linear CC/CV part (no power path — regulators always draw from the cell; proven on the prior active-electronics board).
- **Charge input = the ring of the 1/4″ TRS output jack** — no USB connector on the board. A normal audio cable grounds the ring (benign: charger input sits at 0 V); a special charge cable feeds ~5 V on the ring. Proven approach from a prior active-electronics board. Consequence: audio out and charging are mutually exclusive by construction (same jack), so run-while-charging matters only for non-audio activity.
- **Simple and small** — minimum regulator count, minimum externals.
- **Power efficient** — this is the battery-life budget, and battery life gates the **cell size**; savings here enable a physically smaller cell.
- **3V3_A must be quiet across the whole discharge curve** — 8-channel capture of instrument-level (~0.1 V) signals; analog performance must not degrade as the cell empties.
- JLCPCB/LCSC availability (turnkey assembly).

## 2. The core constraint

A 1S Li-ion cell **straddles 3.3 V**: it spends most of its discharge at 3.6–4.0 V but is only empty at ~3.0 V. That kills the two simple topologies:

- **Buck only:** drops out around BATT ≈ 3.4–3.5 V and the rail sags from there — the last ~15 % of capacity is spent browning out.
- **LDO for 3V3_A fed from the battery:** same dropout problem, and worse — an LDO in dropout has essentially **no PSRR**, so analog gets noisy exactly when the cell is low.

So the main rail must come from a **buck-boost**, and the analog LDO must be fed from a regulated node with real headroom, not from the battery.

## 3. Recommended topology (board rails)

One buck-boost, one LDO — two regulators total (the MCU's core SMPS in §4 is on-die; only its inductor appears on the board):

```
BATT (3.0–4.2 V; TP4054 charges this node from the jack-ring input)
   │
   ├─ TPS63020 buck-boost ──► 3V45_D  (3.45 V, digital: H7 VDD, codec IOVDD/DVDD, BT, pull-ups)
   │                             │        └─ (on-die SMPS ──► VCORE, §4)
   │                             └─ TPS7A20 3.3 V LDO ──► 3V3_A  (ADC5140 AVDD ×2, PCM5102A CPVDD/AVDD,
   │                                                              H7 VDDA/VREF+ via ferrite)
   └─ battery sense divider ──► ADC pin
```

**Why the digital rail is 3.45 V, not 3.30 V:** the LDO needs headroom to have PSRR. 150 mV of headroom clears the TPS7A20's dropout (~110 mV max at 300 mA; far less at our ~100 mA analog load) while staying comfortably inside the H7's 3.6 V VDD operating max even at the top of the regulator tolerance band. Digital doesn't care — the H7, codec IOVDD, and any BT module all spec to 3.6 V, and logic levels stay consistent because everything digital shares the rail. With the core behind the on-die SMPS (§4), the VDD-level penalty on the core shrinks further (the buck converts the excess instead of burning it).

**Why this wins on the stated goals:**

- **Simple/small:** two ICs, one inductor (plus the small SMPS inductor at the MCU, §4). No intermediate rail, no second board-level switcher.
- **Efficient:** the switcher (~90 % over the load range) carries *all* the current; the only linear loss is 3.3/3.45 = **96 %** on the small analog share. Buck-boost quiescent is ~25–50 µA in power-save mode; the LDO adds ~8 µA.
- **Quiet where it matters:** 3V3_A sits behind a dedicated low-noise LDO (10 µVrms, high PSRR) whose input is already a regulated rail — it never sees the battery sag or charger switchover. Constant 3.3 V AVDD from full charge to empty, so codec full-scale and the PCM5102A output level never drift.
- **Bonus:** feeding H7 **VDDA/VREF+ from 3V3_A** (through a ferrite) gives the battery-sense ADC a clean, known 3.300 V reference for free.
- **Discharge-curve behavior:** with Vout = 3.45 V the converter is in clean buck mode for nearly the whole discharge (cell above ~3.5 V ≈ 85 % of capacity); the noisier buck-boost transition region only occurs near empty — and 3V3_A is behind the LDO anyway.

## 4. MCU core supply — H725 (internal SMPS) instead of H723 (LDO-only)

**Amends Phase 0 item 1 of the board plan.** The H72x line splits by part number: **H723/H733 are LDO-only; H725/H735 add an on-die buck (SMPS) for the core domain** — same die, same LQFP-144, similar price. With the LDO, core power drawn from the rail is VDD × I_core regardless of core voltage; the SMPS converts instead of burning. Constraint (per DS13311/AN5419 — reverify on the datasheet pass): **SMPS-direct mode maxes out at VOS1 / 400 MHz**; VOS0 / 550 MHz requires the LDO in the loop (SMPS→LDO cascade, buck pre-drops to 1.8 V, LDO finishes).

Rough numbers, ~200 mA core-domain current at 550 MHz as baseline:

| Config | MCU rail power | vs. baseline |
|---|---|---|
| H723, 550 MHz, LDO (former plan) | ~690 mW | — |
| H723, 400 MHz, LDO | ~450 mW | −35 % |
| H725, 550 MHz, SMPS→LDO cascade | ~400 mW | −42 % |
| **H725, 400 MHz, SMPS direct** | **~175 mW** | **−75 %** |

**Decision: STM32H725ZGT6, wired for SMPS, plan of record 400 MHz SMPS-direct.** The MCU was ~⅔ of the board power budget; this roughly **halves total draw → double the runtime, or a half-size cell** — the point of the exercise. An SMPS-wired H725 board can still fall back to LDO mode (and cascade recovers 550 MHz if ever needed); an H723-wired board can never gain the SMPS, so this must be decided before schematic — hence now.

**DSP headroom at 400 MHz** (why this is safe): YIN measured ~1–2 % of a 500 MHz M7 per voice. Pickup summing happens **before** any serious DSP, so the serious path is 4 channels, not 8; voice allocation can reduce further. Known work item: **YIN is bursty** — its compute lands in spikes, and the 27 % clock cut shrinks the burst budget, so it needs reworking (spread the difference-function accumulation across chunks, or similar — several ways to go). Tracked as an open item.

**Board cost:** one 2.2 µH inductor + caps at the MCU (per AN5419), SMPS pins wired at schematic time. VCAP configuration differs by supply mode — take it from AN5419/the H725 Nucleo reference, not the H723ZG Nucleo.

**Availability (checked 2026-07-13):** LCSC lists STM32H725ZGT6 as [C730156](https://lcsc.com/product-detail/Pre-ordered-MCUs_STMicroelectronics-STM32H725ZGT6_C730156.html) (~$11–13.5) — but in the **pre-order** category. Same gate as before: confirm lead time early; JLCPCB consignment or global sourcing as fallback. H735ZGT6 is the +crypto sibling.

## 5. Rejected alternatives (rail topology)

| Topology | Why not |
|---|---|
| Buck-boost @ 3.3 V, ferrite-only split to 3V3_A | Smallest (one IC), but AVDD rides on switcher ripple/PFM bursts. Too risky for 8-ch instrument-level capture; the LDO is one SOT-23 and <$0.15. Keep as a documented fallback only if 3V3_A proves overkill on spin-1 measurements. |
| Buck-boost @ 3.3 V + low-noise LDO from BATT | Rail count identical to the recommendation but the LDO drops out below ~3.45 V cell — analog PSRR collapses over the last stretch of discharge, and the LDO input carries charger transients. Strictly worse. |
| Buck only @ 3.3 V, early cutoff | Simplest converter but forfeits ~15 % of capacity. Contradicts the battery-life goal. |
| Buck-boost @ ~3.8 V intermediate + 2 LDOs | Clean, but three regulators and burns ~9 % extra on the (dominant) digital load. Over-engineered here. |

## 6. Part candidates (LCSC checked 2026-07-13)

| Part | Role | Key specs | ~Price | Notes |
|---|---|---|---|---|
| **TPS63020DSJR** ([C15483](https://www.lcsc.com/product-detail/C15483.html)) | Buck-boost → 3V45_D | Vin 1.8–5.5 V, adjustable out, ~2 A buck / >1 A boost @ 3 V in, 2.4 MHz, power-save mode, IQ ~25–50 µA, EN pin | ~$0.49 | **Leaning choice.** Adjustable version (fixed parts don't offer 3.45 V). Huge current headroom for BT growth. 3×4 mm VSON + one 1.5 µH inductor. |
| TPS63802DLAR | Buck-boost alt | 2 A, smaller, lower IQ (~11 µA) | ~$1+ | Newer, tighter land pattern; fallback if TPS63020 stock dries up. |
| **TPS7A2033PDBVR** ([C2862740](https://www.lcsc.com/product-detail/voltage-regulators-linear-low-drop-out-ldo-regulators_texas-instruments-tps7a2033pdbvr_C2862740.html)) | LDO → 3V3_A | 300 mA, 10 µVrms noise, PSRR ~65 dB @ 100 kHz, dropout 110 mV typ @ 300 mA, IQ 8.5 µA, SOT-23-5 | ~$0.10–0.15 | **Leaning choice.** 20 k+ in stock. No noise-bypass cap needed. |
| LP5907MFX-3.3 | LDO alt | 250 mA, similar noise class | ~$0.30 | Fine substitute. |
| **TP4054** ([C382138](https://www.lcsc.com/product-detail/C382138.html)) | Charger (upstream) | Linear CC/CV, ≤500 mA (RPROG-set), CHRḠ status, reverse-blocking, SOT-23-5 | ~$0.05 | **Chosen 2026-07-13** — proven on the prior active-electronics board; replaces the BQ2407x-class pick. No power path/TS/timer — acceptable because audio and charging are mutually exclusive (shared jack) and the convention is power-off while charging (§8). BQ24075 remains the upgrade path if spin-2 BT wants charge-while-on. |
| **STM32H725ZGT6** ([C730156](https://lcsc.com/product-detail/Pre-ordered-MCUs_STMicroelectronics-STM32H725ZGT6_C730156.html)) | MCU (core SMPS, §4) | LQFP-144, 550 MHz-capable, on-die core buck | ~$11–13.5 | **Pre-order at LCSC — check lead time early.** |

## 7. Power budget (draft — verify against datasheets)

| Rail | Load | Est. current |
|---|---|---|
| 3V45_D | H725 @ 400 MHz, SMPS direct (§4) | ~50–70 mA (was ~150–250 mA for H723/LDO/550) |
| | 2× ADC5140 IOVDD + DVDD | ~10–20 mA |
| | I2C pull-ups, misc | ~2 mA |
| | BT module (spin 2, budgeted) | ~50–150 mA peak |
| | **Design capacity** | **500 mA** (TPS63020 has ≥3× margin) |
| 3V3_A | 2× ADC5140 AVDD | ~30–40 mA |
| | PCM5102A CPVDD/AVDD/DVDD (incl. charge pump) | ~10–15 mA (⚠ verify) |
| | H725 VDDA/VREF+ | ~2–4 mA |
| | **Design capacity** | **150 mA** (TPS7A20 = 300 mA) |

Rough runtime: total draw drops from ~1 W (H723/LDO/550 baseline) to **~0.5 W** → ~140 mA at 3.7 V → a 1000 mAh cell gives ~6–7 h, a 2000 mAh cell ~13 h. **This is what enables the cell downsize.** Real number still depends on the final cell pick (open in the plan) and BT duty cycle on spin 2.

## 8. Integration notes

- **Charge input (jack ring):** the ring node sees the world — ground shorts from TS plugs (fine), driven/cold pins from balanced TRS gear (fine, low voltage), ESD from cable handling. The TVS is the **primary** protection — the TP4054's abs-max headroom is modest (~11 V claimed on ports; verify on the exact vendor's datasheet — the part is multi-sourced). Route the ring trace away from the tip (audio) net.
- **Run-while-charging caveat (TP4054, no power path):** if the system is left ON while charging, load current flows through the charger's current/termination sensing — charge may terminate late or never, floating the cell at 4.2 V (longevity cost, not a safety event). Convention: **power off while charging** — natural anyway since the jack can't carry audio and charge power at once. Revisit if spin-2 BT wants charge-while-on; that's when a power-path part (BQ24075) earns its cost and board space.
- **On/off:** switch on TPS63020 **EN** — the volume pot's integrated switch (`dac-selection.md`) is the natural SW1, since EN carries only µA. Off-state draw ≈ converter shutdown (<1 µA) + LDO (dies with its input) + charger reverse leakage (µA-class) + sense divider. Charging works with the system off — which per the caveat above is also the *correct* way to charge.
- **Battery sense:** high-value divider (e.g. 1 MΩ/1 MΩ + 100 nF) from BAT to an ADC pin — ~2 µA standing drain; accept it, or high-side-switch the divider from a GPIO if off-state drain matters. Accuracy is good because VREF+ is the LDO's 3.300 V.
- **Sequencing:** 3V3_A rises after 3V45_D by construction (LDO fed from the switcher). Verify the ADC5140 has no AVDD-before-IOVDD requirement (believed relaxed — confirm in datasheet). PCM5102A **XSMT** soft-mute (GPIO PD15) is held low until rails + BCLK are stable, then released to un-mute; its auto power-down also restarts on SAI clock resume (see `dac-selection.md`).
- **Mixed levels:** the PCM5102A digital inputs (BCK/LRCK/DIN/XSMT) are driven by 3.45 V SAI logic — confirm VIH and input abs-max (≈ DVDD + 0.5 V) on the final datasheet pass.
- **Ripple modes:** enable TPS63020 power-save (PFM) for light-load efficiency; PFM ripple lands only on the digital rail. If it ever bothers something, the mode pin can force PWM at a battery-life cost.
- **Layout:** per the plan's partitioning — buck-boost inductor loop minimized, in the charger/buck zone, far from codec inputs. The MCU SMPS inductor is a second small switching loop: keep it tight to its pins and away from the codec island too. TPS7A20 local to the codec/DAC analog island; ferrite + local caps at H7 VDDA.
- **H725 core:** SMPS externals (2.2 µH + caps) and VCAP configuration per AN5419 and the **H725/735 Nucleo reference** (not the H723ZG Nucleo — supply mode differs). Supply-mode selection is latched at boot via PWR config — get it into the platform init early.

## 9. Open items

1. **Cell capacity + connector** (plan Phase 0 item 4) — re-run with the ~0.5 W budget; a smaller cell is now on the table.
2. **H725ZGT6 sourcing** — LCSC shows pre-order; confirm lead time / JLCPCB consignment early (long-lead risk, same as the old H723 gate).
3. **Verify SMPS/VOS rules in DS13311** — confirm 400 MHz VOS1 SMPS-direct and the cascade path to 550 MHz; confirm SMPS external component values.
4. **YIN burst rework** — spread the bursty difference-function work so worst-case chunk load fits the 400 MHz budget (several viable approaches; tracked in the DSP roadmap, not here).
5. Verify ADC5140 AVDD current and supply-sequencing requirements from the datasheet (budget above is an estimate).
6. Confirm PCM5102A supply mins (CPVDD/AVDD/DVDD) and 3.45 V-logic input tolerance on the datasheet (VIH / input abs-max check).
7. Tolerance stack check: TPS63020 FB accuracy + 1 % divider vs. TPS7A20 worst-case dropout at actual analog load — confirm ≥50 mV headroom at worst case, else nudge 3V45_D up (ceiling: H7 VDD 3.6 V max).
8. Decide on/off scheme (EN switch vs. SYSOFF) and whether the sense divider needs a disconnect.
9. Re-confirm LCSC stock of all ICs at order time.

---

*Updated 2026-07-13: DAC references corrected ES9023 → **PCM5102A** (finalized in `dac-selection.md` rev 2) throughout §2/§3/§7/§8 and the budget/open-items — analog supplies are CPVDD/AVDD on 3V3_A, mute via XSMT (PD15). Cell/system net renamed `VBAT`→`BATT` to match the schematic and avoid the MCU pin-6 VBAT collision (see `pin-allocation.md` §7).*
