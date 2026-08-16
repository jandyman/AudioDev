# Power Supply — Charger, Buck-Boost, and Rails (1S Li-ion → 3V45_D / 3V3_A)

**Status:** **Decided and entered.** Topology, all three ICs, and the rail voltages are settled; the circuit is in the schematic. Resolves the regulator portion of Phase 0 item 4 of `multichannel-audio-board-plan.md`, and **§4 amends Phase 0 item 1** (MCU variant: H723 → H725 for the internal core SMPS). What remains is **verification against datasheets before fab** (§9) — checks, not choices.
**Scope:** everything between the charge input and the two 3.3 V-class rails — the TP4054 charger, the **TPS63020 buck-boost** that makes the digital rail, and the TPS7A20 LDO that makes the analog rail — plus the MCU core-domain supply choice, which is the biggest battery-life lever on the board. Pin-by-pin connections and BOM are in `power-supply-netlist.md`; device documentation links are in §10 here.

**Battery:** single-cell Li-ion, **~1200 mAh planned** (cell and connector picked at build time — it sizes runtime, not the circuit; the regulator input range covers any 1S cell).

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
   ├─ TPS63020 buck-boost ──► 3V45_D  (3.45 V, digital: H7 VDD, codec IOVDD/DVDD, pull-ups)
   │                             │        └─ (on-die SMPS ──► VCORE, §4)
   │                             └─ TPS7A20 3.3 V LDO ──► 3V3_A  (ADC5140 AVDD ×2, PCM5102A CPVDD/AVDD,
   │                                                              H7 VDDA via ferrite — VREF+ is internal
   │                                                              to VDDA on the VFQFPN68)
   └─ battery sense divider ──► ADC pin
```

**Why the digital rail is 3.45 V, not 3.30 V:** the LDO needs headroom to have PSRR. 150 mV of headroom clears the TPS7A20's dropout (~110 mV max at 300 mA; far less at our ~100 mA analog load) while staying comfortably inside the H7's 3.6 V VDD operating max even at the top of the regulator tolerance band. Digital doesn't care — the H7 and codec IOVDD both spec to 3.6 V, and logic levels stay consistent because everything digital shares the rail. With the core behind the on-die SMPS (§4), the VDD-level penalty on the core shrinks further (the buck converts the excess instead of burning it).

**Why this wins on the stated goals:**

- **Simple/small:** two ICs, one inductor (plus the small SMPS inductor at the MCU, §4). No intermediate rail, no second board-level switcher.
- **Efficient:** the switcher (~90 % over the load range) carries *all* the current; the only linear loss is 3.3/3.45 = **96 %** on the small analog share. Buck-boost quiescent is ~25–50 µA in power-save mode; the LDO adds ~8 µA.
- **Quiet where it matters:** 3V3_A sits behind a dedicated low-noise LDO (10 µVrms, high PSRR) whose input is already a regulated rail — it never sees the battery sag or charger switchover. Constant 3.3 V AVDD from full charge to empty, so codec full-scale and the PCM5102A output level never drift.
- **Bonus:** feeding H7 **VDDA from 3V3_A** (through a ferrite) gives the battery-sense ADC a clean, known 3.300 V reference for free (VREF+ has no pin on the VFQFPN68 — it is internally tied to VDDA, so VDDA *is* the ADC reference).
- **Discharge-curve behavior:** with Vout = 3.45 V the converter is in clean buck mode for nearly the whole discharge (cell above ~3.5 V ≈ 85 % of capacity); the noisier buck-boost transition region only occurs near empty — and 3V3_A is behind the LDO anyway.

## 4. MCU core supply — H725 (internal SMPS) instead of H723 (LDO-only)

**Amends Phase 0 item 1 of the board plan.** The H72x line splits by part number: **H723/H733 are LDO-only; H725/H735 add an on-die buck (SMPS) for the core domain** — same die, similar price. With the LDO, core power drawn from the rail is VDD × I_core regardless of core voltage; the SMPS converts instead of burning. Constraint (AN5419, confirmed by ST): **SMPS-direct mode maxes out at VOS1 / 400 MHz**; VOS0 / 550 MHz requires the LDO in the loop (SMPS→LDO cascade, buck pre-drops to 1.8 V, LDO finishes).

Rough numbers, ~200 mA core-domain current at 550 MHz as baseline:

| Config | MCU rail power | vs. baseline |
|---|---|---|
| H723, 550 MHz, LDO (former plan) | ~690 mW | — |
| H723, 400 MHz, LDO | ~450 mW | −35 % |
| H725, 550 MHz, SMPS→LDO cascade | ~400 mW | −42 % |
| **H725, 400 MHz, SMPS direct** | **~175 mW** | **−75 %** |

**Decision: STM32H725RGV6 (VFQFPN68, 8×8 mm), SMPS-direct, plan of record 400 MHz.** The MCU was ~⅔ of the board power budget; this roughly **halves total draw → double the runtime, or a half-size cell** — the point of the exercise. The VFQFPN68 package does not bond out VDDLDO (the connections are made internally; ST-confirmed) — **SMPS-direct is the only supply configuration it supports, making 400 MHz a hard ceiling on this package**. There is no board-level recovery to 550 MHz; the exit, if DSP headroom ever proves insufficient, is a respin to the LQFP-144 sibling (H725ZGT6) wired for SMPS→LDO cascade. The §5 headroom analysis below and the YIN burst rework are therefore load-bearing. The package buys ~6× less board area, an exposed ground pad under the die, and a tight SMPS hot loop (VSSSMPS two pads from the inductor pins).

**DSP headroom at 400 MHz** (why this is safe): YIN measured ~1–2 % of a 500 MHz M7 per voice. Pickup summing happens **before** any serious DSP, so the serious path is 4 channels, not 8; voice allocation can reduce further. Known work item: **YIN is bursty** — its compute lands in spikes, and the 27 % clock cut shrinks the burst budget, so it needs reworking (spread the difference-function accumulation across chunks, or similar — several ways to go). Tracked as an open item.

**Board cost:** one 2.2 µH inductor VLXSMPS→VFBSMPS + 4.7 µF at VFBSMPS (entered on the MCU sheet, per AN5419). With the LDO permanently disabled on this package, **VCAP treatment is 100 nF per pin ×3** (ST-confirmed) — also entered.

**Availability:** JLCPCB stocks STM32H725RGV6 as [C5271073](https://jlcpcb.com/partdetail/STMicroelectronics-STM32H725RGV6/C5271073) (~$10–12, low stock — 10 pcs secured 2026-07-15); DigiKey/ST eStore carry it as fallback. H735RGV6 is the +crypto sibling.

## 5. Rejected alternatives (rail topology)

| Topology | Why not |
|---|---|
| Buck-boost @ 3.3 V, ferrite-only split to 3V3_A | Smallest (one IC), but AVDD rides on switcher ripple/PFM bursts. Too risky for 8-ch instrument-level capture; the LDO is one SOT-23 and <$0.15. Keep as a documented fallback only if 3V3_A proves overkill on spin-1 measurements. |
| Buck-boost @ 3.3 V + low-noise LDO from BATT | Rail count identical to the recommendation but the LDO drops out below ~3.45 V cell — analog PSRR collapses over the last stretch of discharge, and the LDO input carries charger transients. Strictly worse. |
| Buck only @ 3.3 V, early cutoff | Simplest converter but forfeits ~15 % of capacity. Contradicts the battery-life goal. |
| Buck-boost @ ~3.8 V intermediate + 2 LDOs | Clean, but three regulators and burns ~9 % extra on the (dominant) digital load. Over-engineered here. |

## 6. Parts (chosen; LCSC checked 2026-07-13, TI lifecycle re-checked 2026-07-28)

| Part | Role | Key specs | ~Price | Notes |
|---|---|---|---|---|
| **TPS63020DSJR** ([C15483](https://www.lcsc.com/product-detail/C15483.html)) | Buck-boost → 3V45_D | Vin 1.8–5.5 V, adjustable out, ~2 A buck / >1 A boost @ 3 V in, 2.4 MHz, power-save mode, IQ ~25–50 µA, EN pin | ~$0.49 | **Chosen.** Adjustable version (fixed parts don't offer 3.45 V). Large current headroom for load growth. 3×4 mm VSON-14 + one 1.5 µH inductor. TI lifecycle **ACTIVE** (re-checked 2026-07-28). |
| TPS63802DLAR | Buck-boost alt | 2 A, smaller, lower IQ (~11 µA) | ~$1+ | Newer, tighter land pattern; fallback if TPS63020 stock dries up. TI also lists TPS631010 / TPS631000 as its own upgrade path (8 µA IQ, smaller package) — relevant only if a future spin re-opens the part. |
| **TPS7A2033PDBVR** ([C2862740](https://www.lcsc.com/product-detail/voltage-regulators-linear-low-drop-out-ldo-regulators_texas-instruments-tps7a2033pdbvr_C2862740.html)) | LDO → 3V3_A | 300 mA, ultra-low noise (7–10 µVrms class), PSRR 95 dB @ 1 kHz, dropout 110 mV typ @ 300 mA, IQ 8.5 µA, SOT-23-5 | ~$0.10–0.15 | **Chosen.** 20 k+ in stock. **No noise-bypass cap required** — that is the specific reason this part beats the usual low-noise LDOs here: same noise floor, one fewer part. |
| LP5907MFX-3.3 | LDO alt | 250 mA, similar noise class | ~$0.30 | Fine substitute. |
| **TP4054** ([C382138](https://www.lcsc.com/product-detail/C382138.html)) | Charger (upstream) | Linear CC/CV, ≤500 mA (RPROG-set), CHRḠ status, reverse-blocking, SOT-23-5 | ~$0.05 | **Chosen 2026-07-13** — proven on the prior active-electronics board; replaces the BQ2407x-class pick. No power path/TS/timer — acceptable because audio and charging are mutually exclusive (shared jack) and the convention is power-off while charging (§8). BQ24075 remains the upgrade path if a later spin wants charge-while-on. |
| **STM32H725RGV6** ([C5271073](https://jlcpcb.com/partdetail/STMicroelectronics-STM32H725RGV6/C5271073)) | MCU (core SMPS, §4) | VFQFPN68 8×8 mm, on-die core buck (SMPS-only package → 400 MHz), 1 MB flash / 564 KB RAM | ~$10–12 | **Chosen.** Low JLCPCB stock — 10 pcs secured; DigiKey fallback. |

## 6a. Buck-boost design detail (TPS63020, checked against SLVS916I rev I)

The netlist (`power-supply-netlist.md` §2) carries the connections; this is the reasoning behind the values, and the three places the datasheet pass changed or confirmed something.

**Confirmed — PS/SYNC tied to GND is correct for power-save.** The pin is documented as *"Enable / disable power save mode (1 disabled, 0 enabled …)"*, and §8 states plainly that power save is entered with PS/SYNC low. Tying it to GND gives PFM at light load, which is where this board spends most of its life. Driving it high (or clocking it) forces fixed-frequency PWM — available later as a bench experiment if PFM ripple ever bothers the digital rail, at a quiescent-current cost.

**Confirmed — 500 mV feedback reference**, so the target ratio is Vout/VFB − 1 = 5.9.

**Changed — divider impedance was too low by half.** The datasheet is explicit that the low-side resistor *"must be kept in the range of 200 kΩ"*, and every entry in its own resistor-selection table uses 180 kΩ. The originally entered 590 kΩ / 100 kΩ pair hits the 5.9 ratio correctly but sits at half the intended impedance level — off-book for a converter whose feedback node is deliberately specified at a fixed impedance (loop compensation and the FB pin's bias/leakage behaviour are characterised around it). **Use 1.18 MΩ / 200 kΩ:** 0.5 V × (1 + 1180/200) = **3.450 V exactly**, both standard E96 1 % values, and it halves the divider's standing drain from ~5.0 µA to ~2.5 µA on a node that is live the whole time the unit is switched on. See §9.

**Capacitance — the reference design is the benchmark.** TI's characterisation circuit for a 3.3 V output runs **2 × 10 µF input** and **3 × 22 µF output** with the same 1.5 µH inductor this board uses. Against that:

- **Input: currently zero.** The `VBAT` net has no local capacitance at all, and it sits *after* the mechanical power switch — so the switcher's input loop closes through switch contacts and chassis wiring. This is the one item on the board that is not a documentation gap but a circuit gap. Fit the 10 µF + 0.1 µF at the pins as this doc has always specified.
- **Output: 2 × 4.7 µF entered vs. 2 × 22 µF specified.** Under the reference design's 3 × 22 µF, and the load here includes an MCU whose current steps hard. Bring it to the specified 2 × 22 µF.
- **VINA bypass 0.1 µF is correct** — and note the datasheet caps this one: *must not exceed 0.22 µF*.

**Inductor — 1.5 µH is TI's own value.** The BOM's "1.5 µH, ≥3 A sat, shielded, 4×4 mm class" matches the characterisation part (Coilcraft XFL4020-152ML) exactly. No derivation needed; this is the reference value for this converter at this output.

**Free features worth using.** Load is disconnected from the battery during shutdown (no reverse leakage path when switched off), and there is a **power-good output** — currently unused, but it is the natural interlock if firmware ever wants to know the digital rail is up before releasing the DAC soft-mute.

---

## 7. Power budget (draft — verify against datasheets)

| Rail | Load | Est. current |
|---|---|---|
| 3V45_D | H725 @ 400 MHz, SMPS direct (§4) | ~50–70 mA (was ~150–250 mA for H723/LDO/550) |
| | 2× ADC5140 IOVDD + DVDD | ~10–20 mA |
| | I2C pull-ups, misc | ~2 mA |
| | **Design capacity** | **500 mA** (TPS63020 has ≥3× margin) |
| 3V3_A | 2× ADC5140 AVDD | ~30–40 mA |
| | PCM5102A CPVDD/AVDD/DVDD (incl. charge pump) | ~10–15 mA (⚠ verify) |
| | H725 VDDA | ~2–4 mA |
| | **Design capacity** | **150 mA** (TPS7A20 = 300 mA) |

Rough runtime: total draw drops from ~1 W (H723/LDO/550 baseline) to **~0.5 W** → ~140 mA at 3.7 V → a 1000 mAh cell gives ~6–7 h, a 2000 mAh cell ~13 h. **This is what enables the cell downsize.** Real number still depends on the final cell pick (open in the plan).

## 8. Integration notes

- **Charge input (jack ring):** the ring node sees the world — ground shorts from TS plugs (fine), driven/cold pins from balanced TRS gear (fine, low voltage), ESD from cable handling. The TVS is the **primary** protection — the TP4054's abs-max headroom is modest (~11 V claimed on ports; verify on the exact vendor's datasheet — the part is multi-sourced). Route the ring trace away from the tip (audio) net.
- **Run-while-charging caveat (TP4054, no power path):** if the system is left ON while charging, load current flows through the charger's current/termination sensing — charge may terminate late or never, floating the cell at 4.2 V (longevity cost, not a safety event). Convention: **power off while charging** — natural anyway since the jack can't carry audio and charge power at once. Revisit if a later spin ever wants charge-while-on; that's when a power-path part (BQ24075) earns its cost and board space.
- **On/off:** switch on TPS63020 **EN** — the volume pot's integrated switch (`dac-selection.md`) is the natural power switch, since EN carries only µA. Off-state draw ≈ converter shutdown (<1 µA) + LDO (dies with its input) + charger reverse leakage (µA-class) + sense divider. Charging works with the system off — which per the caveat above is also the *correct* way to charge.
- **Battery sense:** high-value divider (e.g. 1 MΩ/1 MΩ + 100 nF) from BAT to an ADC pin — ~2 µA standing drain; accept it, or high-side-switch the divider from a GPIO if off-state drain matters. Accuracy is good because VDDA — the ADC reference on this package — is the LDO's 3.300 V.
- **Sequencing:** 3V3_A rises after 3V45_D by construction (LDO fed from the switcher). Verify the ADC5140 has no AVDD-before-IOVDD requirement (believed relaxed — confirm in datasheet). PCM5102A **XSMT** soft-mute (GPIO PC9, net `DAC_XSMT`) is held low until rails + BCLK are stable, then released to un-mute; its auto power-down also restarts on SAI clock resume (see `dac-selection.md`).
- **Mixed levels:** the PCM5102A digital inputs (BCK/LRCK/DIN/XSMT) are driven by 3.45 V SAI logic — confirm VIH and input abs-max (≈ DVDD + 0.5 V) on the final datasheet pass.
- **Ripple modes:** enable TPS63020 power-save (PFM) for light-load efficiency; PFM ripple lands only on the digital rail. If it ever bothers something, the mode pin can force PWM at a battery-life cost.
- **Layout:** per the plan's partitioning — buck-boost inductor loop minimized, in the charger/buck zone, far from codec inputs. The MCU SMPS inductor is a second small switching loop: keep it tight to its pins and away from the codec island too. TPS7A20 local to the codec/DAC analog island; ferrite + local caps at H7 VDDA.
- **H725 core:** SMPS externals (2.2 µH + caps) and VCAP configuration per AN5419; on the VFQFPN68 only SMPS-direct exists (VDDLDO internal), VCAP = 100 nF ×3. Supply-mode selection is latched at boot via PWR config — get it into the platform init early.

## 9. Verification before fab

No open decisions — the topology, the three ICs, the rail voltages, and the on/off scheme are settled. These are checks and value corrections to clear at the netlist/layout gates.

**Circuit corrections (from the §6a datasheet pass — do these):**

1. **FB divider → 1.18 MΩ / 200 kΩ.** The entered 590 k / 100 k has the right ratio at half the datasheet's specified impedance. New pair gives 3.450 V exactly and halves divider drain.
2. **Fit the buck-boost input capacitance.** 10 µF + 0.1 µF at the pins — `VBAT` currently has none, and it sits after the power switch, so the input loop has no local reservoir.
3. **Raise 3V45_D output capacitance to the specified 2 × 22 µF** (entered as 2 × 4.7 µF; TI's reference for this converter uses 3 × 22 µF).

**Datasheet confirmations:**

4. Tolerance stack: TPS63020 FB accuracy + 1 % divider vs. TPS7A20 worst-case dropout at the actual analog load — confirm ≥50 mV headroom worst case, else nudge 3V45_D up (ceiling: H7 VDD 3.6 V max).
5. ADC5140 AVDD current draw and supply-sequencing requirement (the §7 budget is an estimate; sequencing believed relaxed).
6. PCM5102A supply mins (CPVDD/AVDD/DVDD) and 3.45 V-logic input tolerance (VIH / input abs-max).
7. Re-confirm LCSC stock of all three ICs at order time. (TI lifecycle for the TPS63020 re-checked ACTIVE 2026-07-28.)

**Carried elsewhere:**

8. **YIN burst rework** — spread the bursty difference-function work so worst-case chunk load fits the 400 MHz budget. A firmware task, tracked in the DSP roadmap, not a board item.

*Closed:* cell capacity (1S Li-ion ~1200 mAh, picked at build — see header); on/off scheme (hard switch in the battery line via the volume pot's integrated switch, `power-supply-netlist.md` §2); battery-sense disconnect (unnecessary — the divider hangs on the post-switch node, so it draws nothing when off).

---

## 10. Device documentation

**TPS63020 buck-boost — primary**

| Document | ID / Rev | Link |
|---|---|---|
| TPS6302x high-efficiency single-inductor buck-boost converter with 4-A switches | **SLVS916I**, Jul 2010 (rev I, Aug 2019) | https://www.ti.com/lit/ds/symlink/tps63020.pdf |
| Product folder — lifecycle (**ACTIVE**), package, ordering | — | https://www.ti.com/product/TPS63020 |

Datasheet sections the design leans on: **§8.2.2** external component selection (inductor, input/output capacitance — the reference values in §6a come from here); **§8.2.3** setting the output voltage (500 mV reference, the 200 kΩ low-side guidance); **§8.4** power-save mode and PS/SYNC behaviour.

**TPS63020 — supporting**

| Document | ID | Link | Why it matters here |
|---|---|---|---|
| Design considerations for a resistive feedback divider in a DC/DC converter | SLYT469 | https://www.ti.com/lit/pdf/slyt469 | The background for the §9 divider correction — why the impedance level, not just the ratio, is specified. |
| Layer design for reducing radiated EMI of DC/DC buck-boost converters | SLVAEP5 | https://www.ti.com/lit/pdf/slvaep5 | Direct input to the layout rule "minimize the inductor loop, keep it in the charger/buck zone" — worth reading before placing this corner on a board carrying instrument-level analog. |
| Minimizing ringing at the switch node of a boost converter | SLVA255 | https://www.ti.com/lit/pdf/slva255 | Switch-node ringing is the emission source the analog section cares about. |
| Basic calculations of a 4-switch buck-boost power stage | SLVA535 | https://www.ti.com/lit/pdf/slva535 | If the inductor or capacitance ever needs re-deriving rather than copying TI's reference values. |
| Performing accurate PFM-mode efficiency measurements | SLVA236 | https://www.ti.com/lit/pdf/slva236 | Power-save mode is enabled here; naive bench measurement of PFM efficiency misleads. |
| QFN and SON PCB attachment | SLUA271 | https://www.ti.com/lit/pdf/slua271 | VSON-14 land pattern and thermal-pad attachment. |
| Topical index of TI low-power buck-boost application notes | SLVAEH8 | https://www.ti.com/lit/pdf/slvaeh8 | Entry point if a new question comes up. |

**TPS63020 — evaluation, models, layout reference**

| Item | Link | Note |
|---|---|---|
| TPS63020EVM-487 evaluation module | https://www.ti.com/tool/TPS63020EVM-487 | 1.8–5.5 V in, 3.3 V out — close to this board's operating point. |
| EVM user's guide (schematic + layout) | https://www.ti.com/lit/pdf/slvu365 | TI's own layout of this converter; the most useful single reference for the hot-loop placement. |
| EVM Gerbers | https://www.ti.com/lit/zip/slvc313 | Copy-reference for the inductor/cap placement if the corner proves fussy. |
| TINA-TI transient model / PSpice model | https://www.ti.com/lit/tsc/slim154 · https://www.ti.com/lit/zip/slim135 | For simulating the load step from the MCU if the output-capacitance call needs backing. |

**Other rail parts**

| Part | Role | Datasheet | Sourcing |
|---|---|---|---|
| TPS7A20 (TPS7A2033PDBVR) | 3V3_A LDO | https://www.ti.com/lit/ds/symlink/tps7a20.pdf · folder: https://www.ti.com/product/TPS7A20 | [LCSC C2862740](https://www.lcsc.com/product-detail/voltage-regulators-linear-low-drop-out-ldo-regulators_texas-instruments-tps7a2033pdbvr_C2862740.html) |
| TP4054 | Li-ion linear charger | Multi-sourced clone of the LTC4054 — **take the datasheet from the vendor actually shipped**; the charge-current constant and port abs-max differ between fabs (§9, and `power-supply-netlist.md` §4 item 1) | [LCSC C382138](https://www.lcsc.com/product-detail/C382138.html) |
| STM32H725RGV6 core SMPS | MCU core supply (§4) | ST **AN5419** — SMPS supply modes and VCAP treatment; wire verbatim from the Nucleo-H725 schematic | [JLCPCB C5271073](https://jlcpcb.com/partdetail/STMicroelectronics-STM32H725RGV6/C5271073) |

