# Layout Notes — Multichannel ADC/DAC Board

**Status:** Layout decisions and rationale. Feeds the Phase 2 board layout. ⚠ items still need a bench/datasheet/layout call. Companion to `pin-allocation.md`, `adc-netlist.md`, `power-supply.md`/`-netlist.md`, `dac-selection.md`, `bluetooth-constraints.md`, and `test-points.md`. This is the **canonical layout doc**; part-level footprint/BOM choices (packages, dielectrics, JLC part numbers) live in the separate **assignments doc** — cross-referenced here, not duplicated.

**Read first for a fresh session:** this file assumes the schematic is entered (netlist-gate items tracked in the per-section docs) and captures how the board should be *placed and stacked up*, plus the analog-interface decisions that drive it.

**Scope note:** "the board" here means the **main control-cavity board only**. The two offboard pickup preamp PCBs have their own layout rules — input-node copper discipline, Repeat Layout from a hierarchical sheet, custom magnet-wire footprints, bottom-side connector placement — and those live in **`preamp-board.md`** §11, not here.

## 0. Package reality (drives everything)

| Part | Package | Leads probeable? | Consequence |
|---|---|---|---|
| STM32H725RGV6 (MCU) | VFQFPN68, 8×8 mm, 0.4 mm pitch, exposed pad = VSS | No — leadless | Exposed pad drops to L2 ground via a thermal via array; single-row peripheral pins escape on L1 |
| TLV320ADC5140 ×2 (ADC) | 24-WQFN 4×4 (RTW), leadless | No | MCU↔ADC nets unreachable at both ends → dedicated TP pads |
| PCM5102A (DAC) | TSSOP-20, gull-wing | Yes (~0.65 mm) | MCU↔DAC nets probeable at the DAC lead |

All three are single-row/peripheral parts — no BGA-style escape — which is a big part of why 4 layers works (§3).

## 1. Floor plan — long, thin board

> **Actual placements live in [`placement-register.md`](placement-register.md)** — generated from the KiCad PCB by `tools/placement_register.py`, keyed by part value rather than reference designator. Consult it before reasoning about distances or adjacency; this section carries the *intent*, the register carries the *fact*. Re-run the script after any placement change.

End-to-end placement along the long axis:

```
[ ANALOG FRONT END ]───[ MCU ]───[ POWER ]───[ RADIO / CONTROLS ]
  ADC5140 ×2, DAC       H725       TPS63020    BLE module (corner,
  MICBIAS, input caps   (middle)   buck-boost, antenna on the edge),
                                   TP4054      volume pot
                                   charger,
                                   LDO*
```

- **Analog front end at one end, switcher/charger at the other.** The whole point is distance between the TPS63020's (and charger's) high-di/dt loops and the instrument-level front end.
- **MCU in the middle.** Minimizes the runs to both the SAI4 codec bus (to the analog end) and the I2S1 DAC bus. At 8.192 MHz (SAI) / 2.048 MHz (I2S) these lengths are electrically short — placement is about noise, not signal integrity.
- **\*`3V3_A` LDO placed mid-board (near its load), not at the power end.** Put the LDO close to the analog load so its PSRR isn't undone by a long *post*-LDO trace re-acquiring noise; let the noisier pre-LDO `3V45_D` do the long haul (the LDO rejects it). Local analog bulk stays at the ADC pair (the analog bulk cap + the VDDA ferrite for `MCU_VDDA`).
- **MICBIAS never goes toward the power end.** It's generated *inside* each ADC and only leaves the board via the pickup connectors to the offboard pickup preamps.
- **The radio and the user controls share the far corner, past the power end.** The BLE module wants an extreme corner with its antenna on a board edge, and the analog end is spoken for — so it goes at the opposite extreme, which puts it next to the switcher. That adjacency is managed rather than avoided; see §1.2.

### 1.1 Fits on one side (validated against the KiCad layout, 2026-07)

With the ADC section placed for real, the whole board is tracking to a **single-sided, single-board** layout on the ~90×30 mm target — no back-side components required. Two moves make it fit; back-side placement and board-splitting are held in reserve only (§8):

- **Output jack off-board.** The ¼″ TRS lives off the PCB (charge-ring wiring runs out to it), freeing the edge it would otherwise own.
- **Tag-Connect debug, not a header** (§4) — reclaims the 2×5 header footprint and its probe keep-out.

### 1.2 Radio corner — a packed corner, deliberately

`bluetooth-constraints.md` is the canonical doc for the BLE module; this section
carries only what the *layout* has to know. `placement-register.md` carries the
measured clearances — read it rather than trusting any number written by hand.

The corner holds the module, the volume pot, the battery connector, and the
buck-boost inductor within a few millimetres of each other. There is no arrangement
that separates them, so the design picks what to protect:

- **The antenna end is protected absolutely.** It faces the board edge, copper is
  cleared beneath it on every layer out to both edges it faces, and nothing is placed
  off the end of it. Everything else in the corner is beside the module *body*, which
  wants solid ground under it anyway.
- **Orientation does the work that spacing can't.** The module's supply and UART pads
  face the board edge, away from the converter; the column facing the inductor carries
  only ground and unused pins. A re-lay must preserve this.
- **The switcher adjacency is not a 2.4 GHz problem.** At ~2.4 MHz switching there is
  no in-band mechanism; the exposure is near-field coupling into module pins, which
  the pad ordering above already answers. Keep the switch node's copper short.
- **The pots have plastic cases** — a dielectric load, not a conductive one — and sit
  at the far end of the module from the antenna.
- **Clearances are tight enough to be an assembly constraint, not just an RF one.**
  Sub-millimetre courtyard gaps in this corner want a DRC pass with the real
  clearance rules before fabrication, and the through-hole pot placed with care.

## 2. Grounding — one unified plane

**Single ground plane for analog + digital (TI-recommended, and current mixed-signal best practice).** Do **not** split analog/digital grounds — the old split-plane guidance has been walked back for ~15 years because a return current forced to detour around a gap radiates/couples worse than the split ever prevented. Partition by **placement** (§1), not by cutting copper.

This board is the poster child for it: the audio buses run from the mid-board MCU out to the analog/DAC end, so they *need* a continuous return the whole way, and analog living off at one end means the digital return currents (concentrated at the MCU) never have a reason to flow under the analog corner.

**The one sanctioned void: the BLE antenna keep-out.** Copper is cleared on every layer across the module's antenna end (§1.2). This is not an exception to the rule above so much as a case where the rule's *reason* doesn't apply: the void sits at an extreme corner, past the last routing on the board, with the module's own body between it and everything else. No signal crosses it and no return current has any reason to reach it, so nothing is forced to detour. The test for whether a plane cut is acceptable was never "is the plane whole" but "does any return current have to go around it" — and here nothing does. Carry the void out to the board edges rather than leaving an isolated copper island in the middle of it, and keep it out of the module *body's* footprint, which needs solid ground.

## 3. Stackup — 4 layers, Sig / GND / GND\* / Sig

4 layers, not 6. The case for 6 (BGA escape, high-speed sandwiched between two planes) doesn't apply: no BGA, 12 MHz top digital speed, routing-light design. Cheaper and thinner at JLCPCB, too.

| Layer | Role |
|---|---|
| **L1 (top)** | Components + primary/critical signal routing (audio analog + both clock buses live here, over solid L2) |
| **L2** | **Solid, unbroken GND plane** — the unified ground of §2. Never gapped, with one sanctioned exception: the BLE antenna keep-out at the far corner (§2). MCU exposed-pad thermal vias land here. |
| **L3** | **GND-dominant plane** — ground pour stitched hard to L2, *with a `3V45_D` island under the MCU* (§5) for power routing (+ fat feeds for the other low-current rails). Effectively a second ground plane. |
| **L4 (bottom)** | Tolerant routing (control, LED, spare GPIO) over L3 ground fill, plus stitching |

\*Not a dedicated power plane. The board doesn't need one (few rails, low currents); a GND-dominant L3 with a local power island buys more ground reference for the mid-board→analog signal returns and gives L4 a ground under it. The one spot where power routing is dense — the MCU's clustered supply pins — gets the island.

Notes:
- **Keep the sensitive fanout on L1 over L2.** Analog crossovers that must dip to L4 stay ground-referenced, because L3 under them is ground fill.
- **Stitch L2↔L3 liberally** (every ~5–10 mm, and beside any signal-layer transition) so the two ground planes are truly one node, not a floating pour. Keep a clean keep-out around the `3V45_D` island, and don't let an L4 trace cross the island gap without a nearby stitch via.

## 4. Test points

See `test-points.md` (single source of truth, categorized by access type). Summary: Cat 1 wire loops = GND ×2–3 + MCO1; Cat 2 probe pads = the ADC SAI4 bus; DAC I2S bus + XSMT pending the ⚠ TSSOP-probe call; everything else Cat 3 (touch a passive). GND loops one per region (MCU / analog / DAC out).

**Debug connector — Tag-Connect TC2030, no header.** SWD/RTT via a Tag-Connect **TC2030** footprint (six pads + three locating holes, no connector body) rather than a 2×5 1.27 mm Cortex header — this reclaims the header footprint and its probe-clearance keep-out, part of what buys single-sided fit (§1.1). Signals: SWDIO, SWCLK, NRST, VCC (sense), GND (+ one spare); RTT rides over SWD, so no UART pin is needed. Program/debug with the J-Link via Segger's Tag-Connect adapter. Legged (TC2030-IDC) vs. no-leg (TC2030-IDC-NL + retaining clip) is a mechanical/assembly call — NL drops the through-holes but needs the clip held during bring-up.

## 5. MCU power routing — `3V45_D` island on L3 (not L2)

**Goal:** ease the *power routing* around the MCU — get `3V45_D` to all the MCU supply pins without a rat's nest of traces.

**Do:** place a `3V45_D` copper island on **L3, directly under the MCU footprint**, and feed it from the power end with a few vias + a fat trace. Supply pins tap the island locally. **Pour ground on all of L3 the island and rail feeds don't use, stitched to L2** (§3) — so the island costs no ground reference; L3 stays a de-facto second ground plane everywhere else.

**Do NOT** carve this island into L2. L2 is the unified ground plane, and the MCU is the single worst place to gap it (SAI/I2S/USB/SWD/I2C all fan out there → every return current would detour around the hole). There's also a hard conflict: the MCU exposed pad's thermal/ground via array must land in L2 ground right where the island would go. Island on L3, exposed pad → L2 ground, and the two never fight.

**No matching 3V3_A plane/island under the ADC/DAC — deliberate.** The island trick is justified *only* at the MCU, and for a routing reason, not a performance one: the H725's clustered VDD pins would be a rat's nest otherwise. Neither condition holds at the analog end — `3V3_A` is low-current (~150 mA for the whole analog rail, §7 of `power-supply-netlist.md`) and the codecs have only a few supply pins each, so it needs a clean *reference*, not a low-impedance delivery plane. Carving a `3V3_A` island into L3 under the front end would gap the ground pour directly beneath the most sensitive signals — the opposite of the §2/§3 intent that L3 stay solid ground fill under the analog end (so the mid-board→analog L1 returns, and any L4 crossover, always reference ground). Deliver `3V3_A` to the codec/DAC AVDD pins as a fat trace or a **small local top-side pour** (e.g. tying the two ADC5140 AVDD pins together) plus per-pin decoupling — never a plane that chops L3 ground.

## 5.1 MCU SMPS corner (VFQFPN68) — routing recipe

No ST reference design exists for the QFN68 package; this section stands in for it (worked out 2026-07-24). Pads **4 = VSSSMPS, 5 = VLXSMPS, 6 = VDDSMPS, 7 = VFBSMPS** are consecutive on one edge — ST put the whole SMPS hot loop on one corner, but pin 5 (the switch node) sits *between* the input pair, so a literal pad-4↔pad-6 input cap would wall off its escape. Resolution — on this stackup the L2 ground plane is ~0.1 mm below L1, so a plane-returned loop encloses *less* area than any top-side detour:

- **VLX (pad 5) escapes straight out on L1 to the inductor.** Highest priority; shortest trace, minimal copper area (the switch node is the dV/dt antenna), no vias.
- **100 nF input cap beside that corridor:** pad 6 → short trace → cap → **via(s) to L2 at the cap's ground end**; pad 4 gets its **own via(s) into L2 right at the pad**. The chopped input current closes: cap → 6 → switch → 4 → 0.1 mm down → plane → back up. Double vias at each ground landing where space allows.
- **VFB 4.7 µF at the inductor's far terminal**, ground end via'd immediately to L2.
- **VDDSMPS 4.7 µF bulk = island↔GND cap in the general corner area, *not* at the pin.** It's a switching-frequency reservoir refilling the 100 nF — several mm of island-over-plane path is negligible at low MHz, and keeping it off the pin row is what lets the inductor sit close. Placed between the island's feed and the SMPS corner it doubles as island bulk for the five VDD pins (whose cluster 4.7 µF follows the same island↔GND pattern).
- **In2 under pads 4–7 stays ground pour** — the 3V45 island's extent must stop short of this corner so the L2/L3 return under the SMPS pins is solid ground.

**Plane-fed decoupling model (settled 2026-07-24, supersedes "cap at pin X" phrasing everywhere).** At 0.4 mm pitch over a ~0.1 mm-distant plane pair, caps don't belong to pins: supply pins via directly into the island (no top-side cap hop required), and every island↔GND cap serves every pin through the planes, weighted by lateral distance (~50–100 pH/mm spreading at this spacing — "local" ≈ within a few mm). Requirements become **coverage**, not assignment: a 100 nF-class cap within ~2 mm of every supply via, bulk (4.7 µF) within ~5 mm, and one 100 nF sited between the VDDSMPS via and the quiet VDD taps (the SMPS is the noisy consumer that bounces the island). Non-negotiable discipline: **vias immediately at every cap pad** and at pads 4/6 themselves — a trace-then-distant-via reinserts the inductance this scheme exists to remove. The island's plane capacitance (tens of pF) does not replace the caps; it only replaces the wiring. Freeing quiet VDD pins of dedicated caps is encouraged where it buys space near pin 6 / the VLX corridor.

## 5.1.1 HSE and the core SMPS share one package edge — an over-constrained corner

**The single most useful fact about this corner, and it is a pinout constraint, not a layout choice.** ST placed the core-SMPS hot loop and the HSE crystal pair on the *same* package edge, 0.4 mm pitch, separated only by a VSS/VDD pair:

```
pin 4  VSSSMPS
pin 5  VLXSMPS   ← switch node
pin 6  VDDSMPS
pin 7  VFBSMPS
pin 8  VSS       ← ST's interposed
pin 9  VDD       ←   ground/supply buffer
pin 10 PH0 / HSE_IN
pin 11 PH1 / HSE_OUT
pin 12 NRST
```

Whatever drives HSE therefore sits ~2–4 mm from the buck switch node however it is placed. Three consequences:

- **Proximity is not the hazard — loop area is, on both sides.** ST's "inductor as close as possible" and the conventional "crystal as close as possible" are the same rule applied to two adjacent loops: shorten VLX because it is the aggressor's antenna, shorten the crystal loop because it is the victim's. Mutual inductance between two small coplanar loops falls as ~1/d³ *and* scales with the product of the two areas, so shrinking both beats separating them by a wide margin. Two tight loops 2 mm apart couple weakly.
- **ST interposed VSS/VDD deliberately** — a grounded pin and a supply pin between the switcher's return and the oscillator input. Combined with the converter being core-supply-only (sub-watt) and the switching FETs being on-die (the only exposed dV/dt copper is the short VLX run), the adjacency is routinely managed rather than marginal. The crystal's high-Q tank is its own defence: disturbance at the switching fundamental sits far outside the tank's passband, and any resulting spur is further attenuated by PLL3's loop filter before reaching SAI4. **The one thing worth actually checking** is where the internal SMPS switching frequency and its low harmonics fall relative to the crystal frequency — a harmonic landing near it is the only mechanism that turns proximity into injection pulling (AN5419).
- **But the corner is genuinely over-constrained.** The inductor must be tight to pads 5/7. The crystal wants to be both tight to pads 10/11 *and* far from that inductor, and on the only axis available those pull in opposite directions — moving the crystal toward its pins moves it toward the switcher. There is no placement that satisfies everything; the design picks which constraint to relax.

**Plan of record:** keep the crystal on the far side of the HSE pins from the SMPS group, favouring switcher separation over absolute run length, with both load caps flanking the crystal terminals and vias immediately at their ground ends (the resonant loop is crystal ↔ caps ↔ ground, and that triangle is what must stay small). The **SMD1612 package (1.92 mm², against 3.2 mm² for a 2016 and 8.0 mm² for a 3225)** is what makes this tractable at all, and is the reason the crystal frequency was moved to a stock 24 MHz — see `pin-allocation.md` §1.

Package size is the single most effective lever in this corner, and it has paid off at every step down. Each reduction relaxes the over-constraint directly: a smaller can shortens the crystal↔cap↔ground triangle *and* buys separation from the inductor on the same axis, so the two opposing pulls of the previous paragraph both ease at once. 3225 → 2016 closed the HSE-pin distance from 5.33 mm to 4.28 mm; 2016 → 1612 should close it further. The 1612's own load caps are smaller in value too (6.8 pF against 15 pF), which keeps the flanking passives from becoming the new area floor. **If this corner is ever re-opened, look at package size before looking at placement.**

**Related decision — the pin-6 decoupler is deliberately omitted** so the inductor can sit close, with the nearest `3V45_D` cap covering it through the plane per §5.1's coverage model. Note this is the weakest case for the distributed argument: the SMPS input current is chopped with fast edges, which is exactly what wants a local low-inductance cap, and ~3 mm of plane at 50–100 pH/mm is 150–300 pH in the path. Acceptable given the corridor conflict, but **put the island on the spin-1 bring-up list with a scope** rather than assuming it.

## 5.2 `3V3_A` LDO — fed directly from `3V45_D`, no boundary filter (settled 2026-07-25)

`3V45_D` is already routed into the analog zone: the mixed-signal codecs put their **digital** supplies there — both ADCs' IOVDD and the DAC's DVDD sit on `3V45_D` (deliberately, to keep codec digital current off the analog LDO). So there is no "keep `3V45_D` out of analog" to win — the rail is in the zone regardless.

Given that, the `3V3_A` LDO is fed **directly from `3V45_D`**, tapping the same entry that serves the codec digital pins. Its PSRR plus a local 1 µF input cap reject the rail's switcher/island noise. An earlier plan added a series ferrite + shunt cap at the boundary to pre-clean the feed; it was **dropped** — with `3V45_D` present in the zone anyway, it cost parts and routing for negligible gain.

- **Place the LDO near its analog loads** (§1: short *post*-LDO `3V3_A` run so the regulated output doesn't re-acquire noise).
- **Decouple the codec IOVDD/DVDD pins locally** (per the codec sections) so their digital switching current loops at the pin rather than wandering the zone.
- **The real partition is at the signal level, not the rail's presence:** keep the instrument-level pickup inputs, MICBIAS, and the AVDD reference clear of the digital rails and their return currents. One unified ground plane throughout (§2); nothing here splits it.

## 6. Analog interface decisions (settled this pass)

### 6.1 MICBIAS drive — OK for 4 buffers/device

⚠ **MICBIAS is no longer used as the preamp supply.** The preamp boards take the **3.3 V analog rail** — the amplifier's own supply rejection (>80 dB across the audio band) makes MICBIAS's noise isolation unnecessary (`analog-front-end.md` §4). This section is retained because the numbers matter if it is ever brought back.

Per the TLV320ADC5140 datasheet (SBAS892): **MICBIAS current drive = 20 mA** for bias ≥ 2.5 V; **over-current trip = 30 mA**; load regulation 0.6 % typ. Against that ceiling the present front end would draw ~3.8 mA per board — comfortable, but a very different figure from the sub-milliamp follower loads this section was written for.

The 20 mA ceiling was previously recorded as foreclosing higher-current devices or any gain stage on the preamp boards. **That constraint no longer applies** — moving the preamps to the analog rail removes the ceiling entirely, and a gain stage is exactly what the boards now carry (`analog-front-end.md`).

**Layout:** if MICBIAS is ever used to feed multiple loads, the datasheet calls for avoiding common trace impedance — star-route from the pin rather than daisy-chaining. **Not applicable as drawn.** The equivalent live concern is the preamp boards' own shared bias node, handled on those boards (`preamp-board.md` §8).

### 6.2 `3V45_D` as digital supply — all three chips OK

- **STM32H725** (VDD = `3V45_D`): op 1.62–3.6 V, abs-max ~4.0 V → fine.
- **ADC5140** (IOVDD = `3V45_D`): IOVDD abs-max **3.9 V** (0.45 V headroom); inputs referenced to its own IOVDD → no mismatch. ⚠ 3.45 is ~4.5 % over the 3.3 V nominal — glance at recommended-operating IOVDD max (likely 3.6) at the datasheet gate.
- **PCM5102A** (DVDD = `3V45_D`; CPVDD/AVDD = `3V3_A`): its digital-core supply DVDD sits on the 3.45 V rail (per `dac-selection.md` — keeps DAC digital current off the analog LDO), so its digital inputs are driven at a matching 3.45 V. Input abs-max ≈ DVDD + 0.5 = **3.95 V** → the 3.45 V inputs sit ~0.5 V inside it, well above VIH. ⚠ confirm 3.45 V (+ rail tolerance) is inside the PCM5102A DVDD recommended-operating max; if not, DVDD moves to `3V3_A` (`dac-selection.md` §8). **Watch power-up:** don't let the MCU drive I2S into the DAC before `3V3_A` (CPVDD/AVDD) is up — STM32 GPIOs are Hi-Z at reset, `3V3_A` trails `3V45_D` by the LDO turn-on delay, and XSMT is held low.

### 6.3 Pickup cabling — 6-conductor, unshielded

Two pickups, 4 channels each. Per pickup: 6 conductors = GND, PWR (3.3 V analog), 4 amplified signals. Short runs; ohms-level source into 20 K ADC input, ~320 mVpp per channel.

No fundamental issue — the buffering (low-Z source) is what makes single-ended unshielded cable viable:

- **Crosstalk** ~ –65 dB at 20 kHz (few-pF coupling into a ~950 Ω node), better toward DC. Negligible.
- **Shared single ground** carries µA-level signal returns + near-constant buffer supply current → sub-µV signal-dependent drop. Negligible.
- **EMI ingress** is the only real risk (unshielded near magnetic pickups); low source-Z mitigates, and a DNP RF shunt cap (100–330 pF) at each channel's board entry is available (pole ~500 kHz at 1 K drive → safe to populate, well above audio band). Note the *primary* RF defence is not here — it is the RC at each amplifier input on the preamp boards, because 2.4 GHz rectifying at the input produces baseband artifacts that nothing downstream can remove (`bluetooth-constraints.md` §6.5, `preamp-board.md` §7). ⚠ That treatment was reasoned around a JFET gate junction and is **unvalidated against a CMOS input** — it is the identified risk in `analog-front-end.md` §8.
- Insertion loss of the 1 K/20 K divider ≈ –0.4 dB — already in `adc-netlist.md`, not new.

**Cable construction is 28 AWG loose round wire, not flat ribbon** (`preamp-board.md` §9 — driven by the 1 mm-pitch connector and the routing path through the pickup hole). An earlier revision of this section recommended a conductor ordering (`GND · S1 · S2 · PWR · S3 · S4`) and offered ground-interleaving as optional margin. **Both are withdrawn:** with loose round wires you do not control conductor adjacency, so ordering buys nothing. That reasoning only applies to ribbon or flat cable, where positions are fixed. If the cable ever changes to ribbon, reinstate it.

**Still applies:** keep the cable away from the SMPS/charger end.

## 7. Verification items carried into layout

Not open decisions — confirmations, placements, and cost calls to settle while laying the board out.

1. ⚠ **DAC-bus probeability** — probing PCM5102A TSSOP leads acceptable? Decides Cat 2 vs Cat 3 (4 pads) in `test-points.md`.
2. ⚠ **L3 plane discipline** — confirm `3V45_D` island extent under the MCU + ground-flood/stitch elsewhere (esp. analog end) so no L4 crossover references chopped power.
3. ⚠ **ADC5140 recommended-operating IOVDD max** at 3.45 V (abs-max already cleared).
4. **GND wire-loop placement** — one per region (MCU / analog / DAC output).
5. **DAC power-up ordering** — verify firmware keeps I2S Hi-Z until `3V3_A` is up (XSMT-low reinforces).
6. **Pickup cable** — 6 conductors of loose 28 AWG (§6.3, `preamp-board.md` §9). The ground-interleaving option is withdrawn as inapplicable to round wire.
7. ~~**MICBIAS star-route** to the 4 buffer feeds.~~ **Withdrawn** — the preamp boards take the 3.3 V analog rail (§6.1). Route that rail to the pickup connectors as a normal analog supply.
   - ⚠ **Main-board pickup connector is unresolved.** The preamp end is a 1.0 mm-pitch right-angle SMT header chosen partly because "there is very little space at the main board edge" (`preamp-board.md` §9), but the main board is currently placed with 2.54 mm vertical headers. Reconcile — either the edge-space constraint is not real on this board, or the main-board connector needs to change.
8. ⚠ **BLE antenna keep-out extent** — check the as-drawn void against the module manual's PCB-design drawing, particularly how far past the first pad row copper must be cleared (`bluetooth-constraints.md` §8).
9. **Radio-corner DRC** — the corner has sub-millimetre courtyard gaps and a through-hole part beside an SMT module; run the clearance rules that will actually be fabricated before committing.
10. **UART flow control** — confirm the module supports RTS/CTS before leaving two MCU pins committed to it (`bluetooth-constraints.md` §8).
11. Existing netlist-gate ⚠ items in the per-section docs still stand (crystal load caps, I2C pull-up/ADDR values, VCAP/AN5419 SMPS-direct wiring, tantalum polarity, etc.).

## 8. Contingency architectures (held in reserve)

The plan of record is **single-board, single-sided** (§1.1). These are documented fallbacks only — to reach for if the layout stops fitting (scope growth, a bigger connector set):

- **Components on both sides.** Push the decoupling sea, the input clamp diodes, and small passives to the back, directly under the pins they serve (where decoupling wants to be anyway); keep the ICs, inductors, crystal, and connectors on top. Roughly doubles usable area at the cost of double-sided assembly.
- **Split / mezzanine board along the SI partition.** The analog/digital/power zoning of §1 is already a physical partition — promote it to separate boards on a board-to-board stack (power at the bottom, MCU/DAC main, analog capture as its own board/wing). Improves analog/digital isolation as a side effect. The one constraint: the 12.288 MHz TDM bus (BCLK/FSYNC/SDOUT) crossing the connector must be short and flanked by ground pins. A rigid-flex version folds flat for bring-up (all components probeable) and folds into the stack for install.
- **Biggest single area lever, only if desperate:** drop to one ADC / 4 channels — halves the analog front end but changes what the instrument senses. That's a concept cut, not a layout tweak.
