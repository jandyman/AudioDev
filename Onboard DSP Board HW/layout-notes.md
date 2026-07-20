# Layout Notes — Multichannel ADC/DAC Board

**Status:** Pre-layout decisions and rationale, captured from the placement/stackup discussion. Feeds the Phase 2 board layout. ⚠ items still need a bench/datasheet/layout call. Companion to `pin-allocation.md`, `adc-netlist.md`, `power-supply.md`/`-netlist.md`, `dac-selection.md`, and `test-points.md`.

**Read first for a fresh session:** this file assumes the schematic is entered (netlist-gate items tracked in the per-section docs) and captures how the board should be *placed and stacked up*, plus the analog-interface decisions that drive it.

## 0. Package reality (drives everything)

| Part | Package | Leads probeable? | Consequence |
|---|---|---|---|
| STM32H725RGV6 (MCU) | VFQFPN68, 8×8 mm, 0.4 mm pitch, exposed pad = VSS | No — leadless | Exposed pad drops to L2 ground via a thermal via array; single-row peripheral pins escape on L1 |
| TLV320ADC5140 ×2 (ADC) | 24-WQFN 4×4 (RTW), leadless | No | MCU↔ADC nets unreachable at both ends → dedicated TP pads |
| PCM5102A (DAC) | TSSOP-20, gull-wing | Yes (~0.65 mm) | MCU↔DAC nets probeable at the DAC lead |

All three are single-row/peripheral parts — no BGA-style escape — which is a big part of why 4 layers works (§3).

## 1. Floor plan — long, thin board

End-to-end placement along the long axis:

```
[ ANALOG FRONT END ]───[ MCU ]───[ POWER ]
  ADC5140 ×2, DAC       H725       TPS63020 buck-boost,
  MICBIAS, input caps   (middle)   TP4054 charger, LDO*
```

- **Analog front end at one end, switcher/charger at the other.** The whole point is distance between the TPS63020's (and charger's) high-di/dt loops and the instrument-level front end.
- **MCU in the middle.** Minimizes the runs to both the SAI4 codec bus (to the analog end) and the I2S1 DAC bus. At 12.288 MHz (SAI) / 3.072 MHz (I2S) these lengths are electrically short — placement is about noise, not signal integrity.
- **\*`3V3_A` LDO placed mid-board (near its load), not at the power end.** Put the LDO close to the analog load so its PSRR isn't undone by a long *post*-LDO trace re-acquiring noise; let the noisier pre-LDO `3V45_D` do the long haul (the LDO rejects it). Local analog bulk stays at the ADC pair (`C_bulk` + `FB1` for `MCU_VDDA`).
- **MICBIAS never goes toward the power end.** It's generated *inside* each ADC and only leaves the board via `J1`/`J2` to the offboard pickup preamps.

## 2. Grounding — one unified plane

**Single ground plane for analog + digital (TI-recommended, and current mixed-signal best practice).** Do **not** split analog/digital grounds — the old split-plane guidance has been walked back for ~15 years because a return current forced to detour around a gap radiates/couples worse than the split ever prevented. Partition by **placement** (§1), not by cutting copper.

This board is the poster child for it: the audio buses run from the mid-board MCU out to the analog/DAC end, so they *need* a continuous return the whole way, and analog living off at one end means the digital return currents (concentrated at the MCU) never have a reason to flow under the analog corner.

## 3. Stackup — 4 layers, Sig / GND / GND\* / Sig

4 layers, not 6. The case for 6 (BGA escape, high-speed sandwiched between two planes) doesn't apply: no BGA, 12 MHz top digital speed, routing-light design. Cheaper and thinner at JLCPCB, too.

| Layer | Role |
|---|---|
| **L1 (top)** | Components + primary/critical signal routing (audio analog + both clock buses live here, over solid L2) |
| **L2** | **Solid, unbroken GND plane** — the unified ground of §2. Never gapped. MCU exposed-pad thermal vias land here. |
| **L3** | **GND-dominant plane** — ground pour stitched hard to L2, *with a `3V45_D` island under the MCU* (§5) for power routing (+ fat feeds for the other low-current rails). Effectively a second ground plane. |
| **L4 (bottom)** | Tolerant routing (control, LED, spare GPIO) over L3 ground fill, plus stitching |

\*Not a dedicated power plane. The board doesn't need one (few rails, low currents); a GND-dominant L3 with a local power island buys more ground reference for the mid-board→analog signal returns and gives L4 a ground under it. The one spot where power routing is dense — the MCU's clustered supply pins — gets the island.

Notes:
- **Keep the sensitive fanout on L1 over L2.** Analog crossovers that must dip to L4 stay ground-referenced, because L3 under them is ground fill.
- **Stitch L2↔L3 liberally** (every ~5–10 mm, and beside any signal-layer transition) so the two ground planes are truly one node, not a floating pour. Keep a clean keep-out around the `3V45_D` island, and don't let an L4 trace cross the island gap without a nearby stitch via.

## 4. Test points

See `test-points.md` (single source of truth, categorized by access type). Summary: Cat 1 wire loops = GND ×2–3 + MCO1; Cat 2 probe pads = the ADC SAI4 bus; DAC I2S bus + XSMT pending the ⚠ TSSOP-probe call; everything else Cat 3 (touch a passive). GND loops one per region (MCU / analog / DAC out).

## 5. MCU power routing — `3V45_D` island on L3 (not L2)

**Goal:** ease the *power routing* around the MCU — get `3V45_D` to all the MCU supply pins without a rat's nest of traces.

**Do:** place a `3V45_D` copper island on **L3, directly under the MCU footprint**, and feed it from the power end with a few vias + a fat trace. Supply pins tap the island locally. **Pour ground on all of L3 the island and rail feeds don't use, stitched to L2** (§3) — so the island costs no ground reference; L3 stays a de-facto second ground plane everywhere else.

**Do NOT** carve this island into L2. L2 is the unified ground plane, and the MCU is the single worst place to gap it (SAI/I2S/USB/SWD/I2C all fan out there → every return current would detour around the hole). There's also a hard conflict: the MCU exposed pad's thermal/ground via array must land in L2 ground right where the island would go. Island on L3, exposed pad → L2 ground, and the two never fight.

## 6. Analog interface decisions (settled this pass)

### 6.1 MICBIAS drive — OK for 4 buffers/device

Per the TLV320ADC5140 datasheet (SBAS892): **MICBIAS current drive = 20 mA** for bias ≥ 2.5 V (your VREF×1.096 = 3.014 V setting qualifies); **over-current trip = 30 mA**; load regulation 0.6 % typ. Each ADC has its *own* MICBIAS feeding *its* 4 buffers → **5 mA/buffer budget**; JFET followers idle ~0.5–2 mA, so ~8 mA/device — comfortable, nowhere near OCP. Two devices, two independent 20 mA supplies, 8 buffers total.

**Layout:** datasheet says avoid common trace impedance to multiple loads — **star-route MICBIAS from the pin**, don't daisy-chain the 4 buffer feeds.

### 6.2 `3V45_D` as digital supply — all three chips OK

- **STM32H725** (VDD = `3V45_D`): op 1.62–3.6 V, abs-max ~4.0 V → fine.
- **ADC5140** (IOVDD = `3V45_D`): IOVDD abs-max **3.9 V** (0.45 V headroom); inputs referenced to its own IOVDD → no mismatch. ⚠ 3.45 is ~4.5 % over the 3.3 V nominal — glance at recommended-operating IOVDD max (likely 3.6) at the datasheet gate.
- **PCM5102A** (runs off `3V3_A`, **not** 3.45): only its digital inputs are *driven* at 3.45 V. Input abs-max ≈ DVDD + 0.5 = **3.8 V** → 3.45 within it (~0.35 V margin), well above VIH. **Watch power-up:** don't let the MCU drive I2S into the DAC before `3V3_A` is up. Safe in practice — STM32 GPIOs are Hi-Z at reset, `3V3_A` trails `3V45_D` only by the LDO turn-on delay, and XSMT is held low.

### 6.3 Pickup ribbons — 6-conductor is fine

Two pickups, 4 channels each. Per pickup: 6-conductor ribbon = GND, PWR (MICBIAS), 4 buffered signals. Short runs; ~1 K source into 20 K ADC input.

No fundamental issue — the buffering (low-Z source) is what makes single-ended unshielded ribbon viable:

- **Crosstalk** ~ –65 dB at 20 kHz (few-pF coupling into a ~950 Ω node), better toward DC. Negligible.
- **Shared single ground** carries µA-level signal returns + near-constant buffer supply current → sub-µV signal-dependent drop. Negligible.
- **EMI ingress** is the only real risk (unshielded near magnetic pickups); low source-Z mitigates, and the DNP `C_emi` (100–330 pF) RF shunt at each channel's board entry is available (pole ~500 kHz at 1 K drive → safe to populate, well above audio band).
- Insertion loss of the 1 K/20 K divider ≈ –0.4 dB — already in `adc-netlist.md`, not new.

**Recommendations:** order conductors so the quiet lines separate signals (`GND · S1 · S2 · PWR · S3 · S4` — MICBIAS is a low-Z AC ground); keep the ribbon away from the SMPS/charger end. Optional margin: widen to a ground-interleaved ribbon (`G S G S …`) to kill shared-return coupling — not needed here.

## 7. Open items carried into layout

1. ⚠ **DAC-bus probeability** — probing PCM5102A TSSOP leads acceptable? Decides Cat 2 vs Cat 3 (4 pads) in `test-points.md`.
2. ⚠ **L3 plane discipline** — confirm `3V45_D` island extent under the MCU + ground-flood/stitch elsewhere (esp. analog end) so no L4 crossover references chopped power.
3. ⚠ **ADC5140 recommended-operating IOVDD max** at 3.45 V (abs-max already cleared).
4. **GND wire-loop placement** — one per region (MCU / analog / DAC output).
5. **DAC power-up ordering** — verify firmware keeps I2S Hi-Z until `3V3_A` is up (XSMT-low reinforces).
6. **Pickup ribbon width** — stay at 6-conductor vs widen to ground-interleaved (cost call).
7. **MICBIAS star-route** to the 4 buffer feeds (no common impedance).
8. Existing netlist-gate ⚠ items in the per-section docs still stand (crystal load caps, I2C pull-up/ADDR values, VCAP/AN5419 SMPS-direct wiring, tantalum polarity, etc.).
