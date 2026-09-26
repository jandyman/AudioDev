# Power Supply — Charger, Buck-Boost, and Rails (1S Li-ion → 3V3_D / 3V3_A)

**Status:** **Re-decided 2026-09-24 — the analog LDO now feeds from the battery and the digital rail drops to 3.3 V.** See §2a for why the earlier arrangement was reversed. Topology and all three ICs are otherwise settled. Resolves the regulator portion of Phase 0 item 4 of `multichannel-audio-board-plan.md`, and **§4 amends Phase 0 item 1** (MCU variant: H723 → H725 for the internal core SMPS). What remains is **verification against datasheets before fab** (§9) — checks, not choices.
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
- **LDO for 3V3_A fed from the battery:** loses regulation below a cell voltage of about 3.4 V, and an LDO in dropout has essentially **no PSRR** — so analog degrades over the last stretch of discharge.

So the main digital rail must come from a **buck-boost**. The analog LDO's supply is a separate question, and §2a answers it differently from the way this document originally did.

## 2a. Where the analog LDO feeds from — reversed 2026-09-24

**The analog LDO feeds from the battery, not from the switched digital rail.** This reverses the original choice, which is recorded in §5 as a rejected alternative. The reversal is worth stating in full, because the original reasoning was not wrong so much as one-sided.

**What the original reasoning got right.** An LDO fed from the cell does lose regulation near the end of discharge, and its rejection does collapse when it does. Both true.

**What it left out.** Feeding the LDO from the switcher puts a 2.4 MHz converter permanently upstream of the analog supply. The chosen LDO's rejection is specified only to 1 MHz — 45 dB at light load, 40 dB at full load — with nothing published at or above the switching frequency. In power-save mode it is worse still, because the burst rate varies with load and spreads energy across exactly the range where rejection is already falling. So the original arrangement trades *a degraded tail* for *a switching artifact present the whole time*, and the document never weighed the second half of that trade.

**What forced the question.** Holding the digital rail high enough for the LDO's dropout, while keeping it under the lowest device ceiling on that rail, turns out to be impossible. The converter's Dynamic Voltage Positioning lifts the output 3 % typical and 5 % maximum above the setpoint at light load — a deliberate feature, not a tolerance — and once that sits on top of the reference and divider tolerances there is no setpoint that satisfies both ends. The playback converter's digital supply ceiling of 3.46 V is the binding one, and nothing about the rail voltage can rescue it.

**Why moving the LDO dissolves it rather than patching it.** The digital rail was only ever held at 3.45 V to give the LDO headroom; every other device on it would prefer 3.3 V. Take that one consumer off the rail and the reason for the elevation disappears, the rail drops into the 3.3 V logic class (set to 3.25 V, §6a), every ceiling gains margin, and power-save mode can stay enabled.

**What it costs, measured rather than asserted.**

- **Dissipation.** The LDO now drops from the cell instead of from a 3.45 V rail. Against the switcher's efficiency this is a penalty at high charge and a *saving* at low charge, breaking even at a cell voltage of 3.71 V — close to the cell's own nominal. Capacity-weighted, it is **+4.5 mW on roughly 556 mW, about 0.8 %**, or four minutes off an eight-hour run.
- **Truncated discharge tail.** Regulation is lost at a cell voltage near 3.39 V. Below that the analog rail follows the cell down at roughly 40 mV below it, and every device stays inside its recommended window until the cell reaches about 3.24 V. Against a 3.0 V cutoff that costs a few percent of capacity — and it degrades rather than cutting off.
- **The residual worth watching.** In that same tail, the LDO's rejection falls away, so digital current steps on the battery node begin to reach the analog rail, and the bias reference — a divider from the analog rail — drifts down with it. Both effects appear in the same last few percent of discharge. This is a bench observation for bring-up, not a design decision.

**Rejected while making this change:** lowering the analog rail below 3.3 V to buy back tail capacity. It gains barely 1 % of runtime and costs converter headroom on a signal chain that is already short of level.

## 3. Recommended topology (board rails)

One buck-boost, one LDO — two regulators total (the MCU's core SMPS in §4 is on-die; only its inductor appears on the board):

```
BATT (3.0–4.2 V; TP4054 charges the cell node from the jack-ring input)
   │   ── hard on/off switch (volume pot's integrated switch) ──
   │
   ├─ buck-boost ──► 3V3_D  (3.25 V digital: MCU VDD, capture-converter IOVDD ×2, radio, pull-ups)
   │                    └─ (on-die SMPS ──► VCORE, §4)
   │
   ├─ low-noise LDO ──► 3V3_A  (3.3 V analog: capture-converter AVDD ×2,
   │                            playback converter's analog, charge-pump AND
   │                            digital supplies, MCU VDDA via ferrite, and the
   │                            preamp boards via the pickup connectors)
   │
   └─ battery sense divider ──► ADC pin
```

Both rails are in the 3.3 V logic class — analog regulated at 3.30 V, digital set to 3.25 V (§6a) — and they are **siblings, not a cascade**: each takes the switched battery node directly.

**Why the digital rail is 3.25 V.** It no longer has an LDO to feed, so nothing asks it to be higher. The ceilings it must respect are 3.6 V for both the MCU supply and the capture converters' I/O supply, and 3.25 V leaves 60 mV of worst-case margin once the converter's power-save lift is included — where 3.30 V would leave 13 mV. §6a carries the window and why the setpoint sits near its top.

**Why the playback converter's digital supply sits on the *analog* rail.** Its ceiling is 3.46 V — the lowest on the board and too low to live under a switched rail with a power-save lift on it. Moving it costs nothing and gains margin: its analog and charge-pump supplies are already on the analog rail, every one of its digital pins is an *input* so it drives no external line and puts no switching current on that rail, and it draws 8 mA typical. This is the one device whose digital supply does not belong with the other digital supplies, and the reason is a number in its datasheet rather than a preference.

**Why this wins on the stated goals:**

- **Simple/small:** two ICs, one inductor (plus the small SMPS inductor at the MCU, §4). No intermediate rail, no second board-level switcher.
- **Efficient:** the switcher carries the digital load at ~93 %. The analog share drops linearly from the cell — a penalty above a 3.71 V cell and a saving below it, worth about 0.8 % of runtime overall (§2a). Buck-boost quiescent is ~25–50 µA in power-save mode; the LDO adds ~8 µA.
- **Quiet where it matters:** the analog rail sits behind a dedicated low-noise LDO (7 µVrms, 10 Hz–100 kHz) fed from the cell, so **no switching converter appears anywhere upstream of it**. The battery is the quietest source on the board, and the rejection that used to be spent fighting a 2.4 MHz switcher is now spent on nothing. The rail is a constant 3.3 V from full charge down to a cell voltage of about 3.39 V, and follows the cell gently below that.
- **Bonus:** feeding H7 **VDDA from 3V3_A** (through a ferrite) gives the battery-sense ADC a clean, known 3.300 V reference for free (VREF+ has no pin on the VFQFPN68 — it is internally tied to VDDA, so VDDA *is* the ADC reference).
- **Discharge-curve behaviour:** at 3.3 V out the converter is in clean buck mode for most of the discharge and enters the buck-boost transition region near empty — and the analog rail is no longer downstream of it, so that transition reaches nothing that cares.

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
| ~~Buck-boost @ 3.3 V + low-noise LDO from BATT~~ | **This is now the adopted topology — see §2a.** Originally rejected as "strictly worse" on the grounds that the LDO drops out near the bottom of the discharge. That drawback is real and still stands, but the rejection never weighed what the alternative costs: a 2.4 MHz switcher permanently upstream of the analog rail, at a frequency where the LDO's rejection is unspecified. |
| Buck-boost @ 3.45 V feeding the analog LDO | The original recommendation. Dropped because no setpoint satisfies both the LDO's dropout floor and the playback converter's 3.46 V digital-supply ceiling once the converter's power-save lift is counted. Recoverable only by disabling power save *and* using 0.1 % divider parts *and* moving that one supply anyway — three constraints to keep one arrangement that was itself only there to serve the LDO. |
| Buck only @ 3.3 V, early cutoff | Simplest converter but forfeits ~15 % of capacity. Contradicts the battery-life goal. |
| Buck-boost @ ~3.8 V intermediate + 2 LDOs | Clean, but three regulators and burns ~9 % extra on the (dominant) digital load. Over-engineered here. |

## 6. Parts (chosen; LCSC checked 2026-07-13, TI lifecycle re-checked 2026-07-28)

| Part | Role | Key specs | ~Price | Notes |
|---|---|---|---|---|
| **TPS63020DSJR** ([C15483](https://www.lcsc.com/product-detail/C15483.html)) | Buck-boost → 3V3_D | Vin 1.8–5.5 V, adjustable out, ~2 A buck / >1 A boost @ 3 V in, 2.4 MHz, power-save mode, IQ ~25–50 µA, EN pin | ~$0.49 | **Retained.** Set to **3.25 V** by an external divider (§6a). The fixed 3.3 V sibling (TPS63021DSJR) was evaluated — same package and pinout, no divider, trimmed ±1 % — and **rejected on cost and sourcing**: ~$3.50 assembled against ~$0.49, lower stock, and it is the niche SKU, so the adjustable part is the one to standardise on at any real quantity. Retargeting to 3.25 V (§6a) recovers the tolerance margin the fixed part would have bought, for the price of choosing two resistor values carefully. |
| TPS63802DLAR | Buck-boost alt | 2 A, smaller, lower IQ (~11 µA) | ~$1+ | Newer, tighter land pattern; fallback if TPS63020 stock dries up. TI also lists TPS631010 / TPS631000 as its own upgrade path (8 µA IQ, smaller package) — relevant only if a future spin re-opens the part. |
| **TPS7A2033PDBVR** ([C2862740](https://www.lcsc.com/product-detail/voltage-regulators-linear-low-drop-out-ldo-regulators_texas-instruments-tps7a2033pdbvr_C2862740.html)) | LDO → 3V3_A, **fed from the switched battery node** | 300 mA; output noise 7 µVrms (10 Hz–100 kHz); output accuracy **±1.5 %** over line, load and temperature; **dropout 145 mV max at 300 mA** in this package, scaling down with load (~50 mV at the ~85 mA here); PSRR 45 dB at 1 MHz and **unspecified above**; IQ 8.5 µA; SOT-23-5 | ~$0.10–0.15 | **Chosen.** 20 k+ in stock. **No noise-bypass cap required** — the specific reason this part beats the usual low-noise LDOs here: same noise floor, one fewer part, and pin 4 is a genuine no-connect. Note the two corrected figures: dropout is 145 mV max rather than the 110 mV this table previously carried, and the PSRR figure that matters is the one at high frequency, not the 1 kHz headline. |
| LP5907MFX-3.3 | LDO alt | 250 mA, similar noise class | ~$0.30 | Fine substitute. |
| **TP4054** ([C382138](https://www.lcsc.com/product-detail/C382138.html)) | Charger (upstream) | Linear CC/CV, ≤500 mA (RPROG-set), CHRḠ status, reverse-blocking, SOT-23-5 | ~$0.05 | **Chosen 2026-07-13** — proven on the prior active-electronics board; replaces the BQ2407x-class pick. No power path/TS/timer — acceptable because audio and charging are mutually exclusive (shared jack) and the convention is power-off while charging (§8). BQ24075 remains the upgrade path if a later spin wants charge-while-on. |
| **STM32H725RGV6** ([C5271073](https://jlcpcb.com/partdetail/STMicroelectronics-STM32H725RGV6/C5271073)) | MCU (core SMPS, §4) | VFQFPN68 8×8 mm, on-die core buck (SMPS-only package → 400 MHz), 1 MB flash / 564 KB RAM | ~$10–12 | **Chosen.** Low JLCPCB stock — 10 pcs secured; DigiKey fallback. |

## 6a. Buck-boost design detail (checked against SLVS916I rev I)

The netlist (`power-supply-netlist.md` §2) carries the connections; this is the reasoning behind the values, and the three places the datasheet pass changed or confirmed something.

**Confirmed — PS/SYNC tied to GND is correct for power-save,** and with the rail at 3.3 V it can stay there. The pin is documented as *"Enable / disable power save mode (1 disabled, 0 enabled …)"*. Power save is entered below about 100 mA of average inductor current, so this board is in fixed-frequency PWM whenever it is playing and drops into power save only when idle. Driving the pin high forces PWM always — no longer needed for headroom, and available as a bench experiment if power-save ripple ever bothers the digital rail.

**Dynamic Voltage Positioning is a feature, not a tolerance, and it must be budgeted.** SLVS916I §7.3.1: *"the output voltage is typically 3 % above the nominal output voltage at light load currents, as the device is in power save mode."* The specification table bounds it at **+0.6 % to +5 %** referenced to the PWM setpoint, and it only ever pushes upward. Every ceiling on the digital rail has to be checked against setpoint × 1.05, not against the setpoint.

**Setpoint: 3.25 V, from a 1.10 MΩ high-side / 200 kΩ low-side divider.**
0.5 V × (1 + 1100/200) = **3.250 V**; both ordinary E24 1 % values, low side at the
datasheet's specified *"range of 200 kΩ"*. **High side runs from the output to the feedback
pin, low side from the feedback pin to ground** — see the transposition note below.

*Why 3.25 V and not something else.* The usable window is **3.13 – 3.30 V**:

- **Top of the window is 3.30 V.** Worst case is setpoint × 1.089 — ±1 % reference, ±2 %
  from two 1 % resistors, ±1 % line and load, and the +5 % power-save lift above. At
  3.30 V that reaches 3.59 V against the 3.6 V ceiling on the MCU supply and the capture
  converters' I/O supply: 13 mV, too thin. At 3.25 V it reaches 3.54 V — 60 mV.
- **Bottom of the window is 3.13 V,** set by the capture converters' I/O supply, whose
  recommended minimum is 3.0 V. The rail's minimum is setpoint × 0.96, so 3.0 / 0.96.
- **We sit near the top because two margins shrink going down.** The radio wants ≥3.3 V
  for full output power, and the playback converter's input threshold is 0.7 × its own
  supply = **2.35 V**, fixed by the analog rail while the MCU's drive strength falls with
  the digital rail.
- **Going lower saves almost nothing.** The MCU and the radio each contain a switching
  regulator, so they draw constant *power* and do not care what the rail is. Only the
  MCU's I/O switching scales with V², worth roughly 4 mW of the board's ~560 mW.
- **1.8 V is not reachable at all** — the playback converter's 2.35 V input threshold,
  which its own supply sets and the digital rail cannot lower.

**The divider is the one place on this board where a legal wiring gives a wrong answer.**
Its value depends on *which* of two resistors sits on *which* side of a node, and both
arrangements are electrically legal, so neither ERC nor DRC nor a pin-by-pin datasheet
check distinguishes them. The board was entered with the two transposed, which regulates
the rail to 0.585 V and leaves nothing able to start. **Put the arithmetic in the schematic
as a text note beside the divider, and recompute it whenever either value changes.**

*The fixed 3.3 V sibling was considered and rejected.* It deletes the divider entirely —
its feedback pin ties straight to the output — and specifies a trimmed ±1 %. But it costs
~$3.50 assembled against ~$0.49, carries lower stock, and is the niche SKU: at any real
quantity the adjustable part is the one to standardise on. Retargeting to 3.25 V recovers
the same margin for the price of choosing two values carefully.

**Capacitance — the reference design is the benchmark.** TI's characterisation circuit for a 3.3 V output runs **2 × 10 µF input** and **3 × 22 µF output** with the same 1.5 µH inductor this board uses. Against that:

- **Input: 10 µF + 0.1 µF at the pins**, on the switched battery node — which sits *after* the mechanical power switch, so without local capacitance the switcher's input loop would close through switch contacts and chassis wiring.
- **Output: 2 × 22 µF** on the digital rail, against the reference design's 3 × 22 µF, with an MCU load whose current steps hard.
- **VINA bypass 0.1 µF** — the datasheet caps this one: *must not exceed 0.22 µF*.
- **New with §2a:** the analog LDO's input now sits on the same switched battery node. Its own input capacitance is separate from the switcher's and belongs at its pin, not shared across the node.

**Inductor — 1.5 µH is TI's own value.** The BOM's "1.5 µH, ≥3 A sat, shielded, 4×4 mm class" matches the characterisation part (Coilcraft XFL4020-152ML) exactly. No derivation needed; this is the reference value for this converter at this output.

**Free features worth using.** Load is disconnected from the battery during shutdown (no reverse leakage path when switched off), and there is a **power-good output** — currently unused, but it is the natural interlock if firmware ever wants to know the digital rail is up before releasing the playback soft-mute. Note that with §2a the analog rail no longer depends on the switcher at all, so power-good now indicates only the digital rail's state.

---

## 7. Power budget (datasheet figures, 2026-09-24)

| Rail | Load | Current |
|---|---|---|
| 3V3_D | H725 @ 400 MHz, SMPS direct (§4) | ~50–70 mA |
| | 2× ADC5140 IOVDD (static + TDM bus switching) | <1 mA — the I/O supply draw is 0.05–0.1 mA each, far below this table's earlier estimate |
| | BLE module, averaged | <1 mA |
| | I²C pull-ups, misc | ~1 mA |
| | **Design capacity** | **500 mA** |
| 3V3_A | 2× ADC5140 AVDD, four channels operating | **42.6 mA** (21.3 mA each) |
| | PCM5102A AVDD + CPVDD, with signal | **22 mA typ / 32 mA max** — the earlier ~10–15 mA estimate carried a ⚠ and was low |
| | PCM5102A DVDD, moved to this rail per §3 | **8 mA typ / 13 mA max** |
| | H725 VDDA | ~3 mA |
| | Preamp boards, two, via the pickup connectors | 7.6 mA |
| | Bias reference divider and buffer | ~0.1 mA |
| | **Total** | **~85 mA typ, ~107 mA max** |
| | **Design capacity** | **150 mA** (the LDO is a 300 mA part) |

**Runtime.** Digital branch ~224 mW delivered, taken as constant power because the MCU's on-die SMPS draws roughly constant power as its input moves. Analog branch 85 mA drawn straight from the cell. Total battery draw is about **560 mW**, so a 1200 mAh cell gives roughly **eight hours**. Moving the analog LDO to the battery costs about **four minutes** of that (§2a).

**LDO dissipation.** (4.2 − 3.3) V × 85 mA = **77 mW** at full charge, falling to nothing as the cell discharges. In SOT-23-5 at roughly 200–250 °C/W that is a 15–19 °C rise — acceptable, but it makes the LDO the warmest small part on the board, and it sits in the analog section. Keep it away from the bias reference.

## 8. Integration notes

- **Charge input (jack ring):** the ring node sees the world — ground shorts from TS plugs (fine), driven/cold pins from balanced TRS gear (fine, low voltage), ESD from cable handling. The TVS is the **primary** protection — the TP4054's abs-max headroom is modest (~11 V claimed on ports; verify on the exact vendor's datasheet — the part is multi-sourced). Route the ring trace away from the tip (audio) net.
- **Run-while-charging caveat (TP4054, no power path):** if the system is left ON while charging, load current flows through the charger's current/termination sensing — charge may terminate late or never, floating the cell at 4.2 V (longevity cost, not a safety event). Convention: **power off while charging** — natural anyway since the jack can't carry audio and charge power at once. Revisit if a later spin ever wants charge-while-on; that's when a power-path part (BQ24075) earns its cost and board space.
- **On/off:** a **hard switch in the battery line**, via the volume pot's integrated switch, between the cell node and the switched battery node. Everything downstream — buck-boost, analog LDO, sense divider — hangs off the switched node, so off-state draw through the board is zero and only the charger's own reverse leakage remains. **This is what makes §2a safe:** the analog LDO must sit on the switched node, never on the cell node, or it would drain the battery with the instrument off. Charging works with the system off, which per the caveat above is also the correct way to charge.
- **Battery sense:** high-value divider (e.g. 1 MΩ/1 MΩ + 100 nF) from BAT to an ADC pin — ~2 µA standing drain; accept it, or high-side-switch the divider from a GPIO if off-state drain matters. Accuracy is good because VDDA — the ADC reference on this package — is the LDO's 3.300 V.
- **Sequencing — changed by §2a, and confirmed harmless.** The two rails are now siblings rather than a cascade, and the analog rail will generally rise *first*, since the LDO starts as soon as the switch closes while the switcher soft-starts. SBAS892A settles it: *"The power-supply sequence between the IOVDD and AVDD rails can be applied in any order."* The same section requires the shutdown pin be held low until the I/O supply is stable, which the pull-down does by construction, and specifies a supply ramp slower than 1 V/µs and at least 100 ms between a power-down and the next power-up. The playback converter's soft-mute is held low until the rails and bit clock are stable, then released — and it needs a pull-down to guarantee that state through reset (see the risk register).
- **Mixed levels — resolved by §3.** Every digital signal is now in the 3.3 V logic class on both ends: the SAI drives from the 3.25 V digital rail, and the playback converter's digital supply is the 3.3 V analog rail. The two rails are nominally equal and independently regulated, so the small difference between them is well inside the ±0.3 V input allowance. The input-level question this line used to carry no longer arises.
- **Ripple modes:** power save stays enabled. Its ripple and its 3–5 % voltage lift now land only on the digital rail, where the nearest ceiling is 3.6 V and there is room for both. Nothing analog is downstream of the switcher any more.
- **Layout:** per the plan's partitioning — buck-boost inductor loop minimized, in the charger/buck zone, far from codec inputs. The MCU SMPS inductor is a second small switching loop: keep it tight to its pins and away from the codec island too. The analog LDO stays local to the codec/DAC analog island, but **its input trace now runs from the switched battery node**, so route that trace along the same path the digital rail's feed takes rather than across the analog island; ferrite + local caps at H7 VDDA.
- **H725 core:** SMPS externals (2.2 µH + caps) and VCAP configuration per AN5419; on the VFQFPN68 only SMPS-direct exists (VDDLDO internal), VCAP = 100 nF ×3. Supply-mode selection is latched at boot via PWR config — get it into the platform init early.

## 9. Verification before fab

No open decisions. These are changes to enter and checks to clear.

**Decided 2026-09-24**

1. **Keep the adjustable buck-boost and retarget the rail to 3.25 V** (divider 1.10 MΩ high-side / 200 kΩ low-side, §6a). The fixed 3.3 V sibling was evaluated and rejected on cost and sourcing — ~$3.50 assembled against ~$0.49, lower stock, and the niche SKU of the two. Retargeting recovers the same tolerance margin; the divider stays, with its arithmetic as a schematic note.

**Changes to enter**

2. **Analog LDO input and enable move to the switched battery node** — not the cell node, which is ahead of the power switch (§8).
3. **Digital rail retargets to 3.25 V** — enter 1.10 MΩ from the output to the feedback pin and 200 kΩ from the feedback pin to ground. **The two currently entered resistors are transposed**; this is the edit that fixes them.
4. **Playback converter's digital supply moves to the analog rail** (§3). Required either way; its 3.46 V ceiling cannot live under a power-save lift.
5. **Rename `3V45_D` → `3V3_D` and `FB_3V45` → `FB_3V3`.** A net named for a voltage it no longer carries is exactly the kind of stale label that causes the next error. The new name denotes the 3.3 V logic class; the 3.25 V setpoint lives in the tables.
6. **Add a pull-down on the playback soft-mute line** so the part is muted by default through power-up and MCU reset (risk register, BU-DA3).

**Datasheet confirmations — items 7 and 8 were on this list before and had not been done; doing them is what found the rail problem. Do not defer them again.**

7. ~~Tolerance stack against LDO dropout.~~ **Done, and it failed.** No setpoint satisfied both the dropout floor and the playback converter's ceiling; §2a is the resolution. The check as written also named the wrong ceiling — it said the MCU's 3.6 V, missing that a device on the same rail sits at 3.46 V.
8. ~~Playback converter supply minimums and logic input tolerance.~~ **Done.** Analog and charge-pump supplies 3.0/3.1 V minimum, 3.46 V maximum; digital supply 3.1–3.46 V. The maximum is the number that forced §3.
9. ~~Capture converter AVDD draw and sequencing.~~ **Done.** 21.3 mA each at four channels; sequencing between the I/O and analog supplies may be in any order (§8).
10. **BLE module supply range at 3.3 V** — the one device whose limits have not been read.
11. Re-confirm LCSC stock of all ICs at order time, including the converter chosen in item 1.

**Carried elsewhere**

12. **YIN burst rework** — spread the bursty difference-function work so worst-case chunk load fits the 400 MHz budget. A firmware task, tracked in the DSP roadmap, not a board item.
13. **End-of-charge behaviour** — below a cell voltage of about 3.39 V the analog LDO enters dropout, its rejection falls away, and the bias reference drifts down with the rail. Bench observation during bring-up, not a design decision (§2a).

*Closed:* cell capacity (1S Li-ion ~1200 mAh, picked at build); on/off scheme (hard switch in the battery line via the volume pot's integrated switch); battery-sense disconnect (the divider hangs on the switched node, so it draws nothing when off); buck-boost input capacitance and digital-rail output capacitance, both now entered.

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

