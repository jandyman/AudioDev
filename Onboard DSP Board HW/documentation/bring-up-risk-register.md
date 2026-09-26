# Main Board — Risk Register

**Status:** Working punch list. Last reviewed 2026-09-24.
**Scope:** the main DSP board through first working audio. Parts are named by function,
never by reference designator.

Each entry opens with **Pending** — the actionable items, which together form the punch
list — followed by **Analysis**, the reasoning and evidence behind them. **Closed items
are deleted, not annotated**, so the pending lists stay readable. Each entry also carries
a **Gate**: what must work before the risk can be evaluated at all.

> 🔴 **The power section is being re-entered.** The buck-boost feedback divider was found
> **inverted** — the rail would have regulated to 0.585 V and nothing on the board would
> have started (BU-P1). Investigating it showed the 3.45 V rail target was itself
> unworkable, and the resolution was architectural: **the analog LDO now feeds from the
> switched battery node and the digital rail drops to 3.3 V** (`power-supply.md` §2a).
> BU-P1 and BU-P5 carry the action items. Nothing in the signal path changes.

**Related:** `multichannel-audio-board-plan.md` (Phase 5 bring-up order);
`dsp-board-audit-risk-list.md` in the project docs (symbol-against-footprint audit);
the per-section docs and their ⚠ checklists, which are inputs to this register.

---

## 1. The gating chain

A risk behind a closed gate is **unevaluated**, which is not the same as **passed**.
Audio performance in particular cannot be measured until the capture path delivers
samples, so those risks stay open through most of bring-up.

```
G0  Board physically sound            (fab/assembly correct)
 └─ G1  Rails at spec
     └─ G2  MCU alive and debuggable
         └─ G3  Clock tree correct
             ├─ G4  I2C enumerates
             │   └─ G6  Capture path
             │       └─ G7  Audio performance
             ├─ G5  Playback path
             └─ G8  Radio link
```

G5 sits beside G4 because the DAC is strap-configured and not on the control bus — the
one audio subsystem provable without I2C, which is why the plan brings it up first.

| Tag | Meaning |
|---|---|
| **BU** | Bring-up: a subsystem does not come up |
| **FA** | Fab/assembly: wrong or dead before power-on |
| **PF** | Performance: works, but not well enough |
| **DX** | Debuggability: the failure cannot be diagnosed |
| **PG** | Programmatic: schedule, sourcing, respin, documentation |

---

## 2. Power

### BU-P1 — Digital rail doesn't start, or comes up at the wrong voltage
*Gate: G0*

**Pending**

- [ ] 🔴 **Correct the feedback divider and retarget the rail to 3.25 V.** Enter **1.10 MΩ
      from the output to the feedback pin** and **200 kΩ from the feedback pin to ground**
      (0.5 V × (1 + 1100/200) = 3.250 V). **The two resistors on the board are currently
      transposed**, which sets the rail to 0.585 V and stops every device from starting —
      see the analysis. Put the arithmetic in the schematic as a text note beside the
      divider; no automated check will catch a transposition, because both arrangements are
      electrically legal.
      *Why 3.25 V:* worst case is setpoint × 1.089 (±1 % reference, ±2 % divider, ±1 % line
      and load, +5 % power-save lift) = 3.54 V against a 3.6 V ceiling; at 3.30 V it would
      be 3.59 V. The floor is 3.13 V, set by the capture converters' 3.0 V I/O minimum.
      Sitting near the top preserves radio output power and drive margin into the playback
      converter, and going lower saves under 1 % — both big digital loads contain their own
      switching regulators, so they draw constant power.
      *The fixed 3.3 V sibling was evaluated and rejected* on cost and sourcing (~$3.50
      assembled vs ~$0.49, lower stock, niche SKU).
- [ ] **Move the analog LDO's input and enable to the switched battery node.** Not the
      cell node, which sits ahead of the power switch and would drain the battery with the
      instrument off.
- [ ] **Move the playback converter's digital supply to the analog rail.** Its 3.46 V
      ceiling cannot live under a switched rail, whatever the setpoint (BU-P5).
- [ ] **Rename the digital-rail net** `3V45_D` → `3V3_D`, and the feedback midpoint
      `FB_3V45` → `FB_3V3`. A net named for a voltage it no longer carries is exactly the
      kind of stale label that causes the next error.
- [x] ~~Decide the power-good pin.~~ **Closed 2026-09-24: it stays tied to ground.** The
      pin reports only the digital rail, and the MCU executing code already proves that rail
      is up — so there is nothing for firmware to learn from it. Anything finer, such as
      detecting a rail that is running but out of regulation, is better done by the MCU's own
      programmable voltage detector, which needs no pin and no trace. The rail that actually
      gates audio is the analog one, and since its LDO moved to the battery the converter's
      power-good says nothing about it. Grounding an open-drain output is harmless — the
      datasheet also sanctions leaving it open — so no current path is created either way.
- [ ] State the dielectric and voltage rating in the value fields of the two output bulk
      capacitors (X7R/X5R ≥ 10 V).
- [ ] **Add the analog LDO's own input capacitor** at its pin on the switched battery
      node — separate from the converter's, not shared across the net.

**Analysis**

Pin table verified against SLVS916I: VINA 1, GND 2, FB 3, VOUT 4/5, L2 6/7, L1 8/9,
VIN 10/11, EN 12, PS/SYNC 13, PG 14, exposed pad 15. Power-save strap to ground and
enable tied to the post-switch battery node are both correct per the datasheet.

The exposed pad is the device's **only** PGND connection, so it carries full switching
return current — its via stitching is electrically load-bearing, not merely thermal.

Input capacitance (10 µF + 0.1 µF) is present. Inductor is adequate: 1.5 µH, Isat well
above anything this converter draws at a 500 mA load.

**The output-voltage divider is wired backwards.** SLVS916I §8.2.3 is explicit about
which resistor goes where: *"The resistor divider must be connected between VOUT, FB, and
GND. The feedback voltage is 500 mV nominal. The low-side resistor R2 (between FB and GND)
must be kept in the range of 200 kΩ,"* with the high-side resistor R1 = R2 × (VOUT/VFB − 1).

For the 3.45 V rail the board was entered for, that gives a **220 kΩ low-side** and a
**1.3 MΩ high-side** (220 k × (3.45/0.5 − 1) = 1.298 MΩ). Both parts are on the board at
exactly those values —
but the 220 kΩ spans output-to-FB and the 1.3 MΩ spans FB-to-ground, which is the
inversion. The resulting setpoint is

    0.5 V × (1 + 220 k / 1.3 M) = **0.585 V**

The converter would regulate happily to 0.585 V. Nothing downstream runs, and the symptom
is a board that appears dead with a converter that is working correctly. Confirmed on both
the schematic and the layout, so it is not a propagation artefact.

Note what this means for how the earlier review missed it: the pin table was verified
against the datasheet and passed, because every pin *is* on the right net. The fault is in
which of two resistors sits on which side of a node — invisible to a pin-by-pin check and
invisible to ERC and DRC, since both topologies are electrically legal. It is only visible
by computing the setpoint. **Every resistor divider on the board deserves that arithmetic
done once.** The battery-sense divider and the bias divider have both since been checked
and are correct.

### BU-P2 — MCU core SMPS doesn't come up
*Gate: G1.* The most opaque failure on the board — the core has no rail until the
internal converter runs, so the symptom is a part that draws current and offers no debug
access to explain itself.

**Pending**

- [ ] **Swap the SMPS inductor for a lower-DCR part.** Fitted part is 216 mΩ against
      AN5419's 110 mΩ (saturation and thermal ratings are fine, nothing is stressed).
      **Murata DFE252012F-2R2M=P2, LCSC C576403** — 82 mΩ, Isat 3.6 A, and the *same*
      2.5 × 2.0 × 1.2 mm body, so no layout change. Worth ~2% of core power.
- [ ] Platform PWR init selects SMPS-direct. The configuration bits latch until the next
      power-on reset, so a mismatch is recoverable by power-cycling and reflashing, not a
      brick — but it must match the wiring.

**Analysis**

**VCAP is not externally connected to VFBSMPS.** AN5419 Rev 3 Figure 2, configuration
*2. Direct SMPS Supply*, shows the SMPS on, the internal regulator off, and VCAP as the
core node fed inside the die. The entered topology is correct and this is not a
dead-board scenario. (The 220 pF on VLXSMPS that appears in Table 2 is scoped to
*"LQFP/BGA packages"* and does not apply to the VFQFPN68.)

Everything else checks out: 2.2 µH between VLXSMPS and VFBSMPS, VDDSMPS on the digital
rail, VSSSMPS to ground, 100 nF at each VCAP pin, backup-domain pin tied to the digital
rail, analog supply through its ferrite, exposed pad to ground.

**The three VCAP pins are deliberately not tied together on the board** — 100 nF at each
pin, no external link. AN5419 Table 2 states "All VCAP connected together" for the
LDO-disabled case, but the pins land on three different sides of the package with a busy
bottom layer, and the same table row also covers bypass mode, where the VCAP pins carry
supply current and the tie is functional rather than advisory. In direct-SMPS mode the
pins are taps on an internally-fed core rail, so the external tie only shortens the path
between decoupling capacitors. Recorded as a deviation; a community question is open to
confirm. Bench-observable if it ever matters.

On firmware: the part cannot boot without a core supply, so firmware is not what starts
the SMPS — it comes out of reset with the regulators enabled. The risk is firmware
writing a supply configuration that doesn't match the wiring and dropping the core
mid-init. The bits latch until the next power-on reset, so that is recoverable by power
cycling and reflashing, and connect-under-reset if the code runs early.

### BU-P3 — Charger doesn't charge, or the charge input damages something
*Gate: G1*

**Pending**

- [ ] **Charge-status pin is unconnected.** No LED, no pad. Phase 5 calls for verifying a
      full charge cycle and termination, which currently needs a meter on the cell.
- [ ] Recompute the charge current once the cell is chosen — stay at or under 1C, noting
      that the thermal limit binds before 1C does.

**Analysis**

Thermal path measured on the current layout and it is good: ground pad set to a **solid**
zone connection rather than thermal relief, 114 mm² of top-layer ground pour within 8 mm,
a near-solid inner plane underneath (92–94% coverage), and the nearest ground via 0.40 mm
edge-to-edge from the pad. That is about as good as a SOT-23-5 gets — call it
130–160 °C/W.

At the fitted 300 mA the worst case is 0.6 W, giving ~105–120 °C junction, brushing the
~120 °C thermal-regulation threshold only with a flat cell in a warm room; it would
simply slow the first few minutes. Typical mid-charge dissipation is ~0.36 W.

**No TVS on the charge input — a decision, not an omission.** The 4.7 µF at the charger's
supply pin is the protection for the events that can reach this node: a 2 kV human-body
discharge carries ~200 nC, which into 4.7 µF is ~40 mV at the pin. The exposure path is a
metal plug sweeping the ring contact during insertion, carrying the handler's charge —
an HBM-class event the capacitor absorbs. A bulk capacitor stops helping only for fast
contact discharge, where its inductance rather than its capacitance sets the peak, and
that is the model for a directly exposed port rather than a recessed jack ring inside a
control cavity. The same interface has run without incident on a prior board.

The charger has no power path and no safety timer, so the convention remains power-off
while charging — enforced for audio by the shared jack, not for anything else.

### BU-P4 — Analog rail regulates but isn't quiet enough
*Gate: G1 for existence, G7 for quality*

**Pending**

- [ ] Confirm LDO dropout at the bottom of the discharge curve against the actual
      analog load.
- [ ] Confirm the analog-supply ferrite and local capacitors at the MCU analog pin.

### BU-P5 — Rail voltages against device ceilings
*Gate: G1. Resolved architecturally; what remains is confirmation and one bench item.*

**Pending**

- [ ] **Confirm the digital rail's ceiling on the bench** at light load, where the
      converter's power-save lift is largest. Expect 3.54 V worst case against a 3.6 V
      limit; measure it rather than trusting the stack-up.
- [ ] **Radio supply at the rail's minimum.** The module wants ≥3.3 V for full output
      power and the rail's floor is about 3.23 V, so transmit power may be marginally down
      at the bottom of tolerance. Range is 1.7–3.6 V so this is graceful, not a fault —
      but confirm it is acceptable rather than discovering it as a range complaint.
- [ ] **Bench the end-of-charge behaviour.** Below a cell voltage near 3.39 V the analog
      LDO enters dropout: its rejection falls away, so digital current steps on the battery
      node begin reaching the analog rail, and the bias reference — a divider from that
      rail — drifts down with it. Both appear in the same last few percent of discharge.
      Characterise it once; decide then whether it warrants a low-battery cutoff.

**Analysis**

**The ceilings, from the datasheets.**

| Device supply | Recommended max | Rail it sits on |
|---|---|---|
| Playback converter, digital | **3.46 V** | analog (moved here *because* of this number) |
| Playback converter, analog and charge pump | 3.46 V | analog |
| Capture converters, I/O | 3.6 V | digital |
| MCU VDD | 3.6 V | digital |
| Radio module | 3.6 V (≥3.3 V for full output power) | digital |

**Why no single switched rail could serve both the LDO and the playback converter.** The
LDO's floor is its worst-case output of 3.350 V plus dropout, about **3.40 V**, and that
floor applies at the rail's *minimum*. The playback converter's ceiling of 3.46 V applies
at the rail's *maximum*. The rail's own band is roughly 11 % wide once three things are
stacked: the feedback reference at ±1 %, the divider resistors at ±2 %, and — the term the
original analysis omitted — **Dynamic Voltage Positioning**, a documented feature that
lifts the output 3 % typically and 5 % at most above the setpoint at light load, in one
direction only. An 11 % band does not fit in a 60 mV window. No setpoint existed.

**The resolution was to remove the constraint, not to fit inside it.** The rail was only
held at 3.45 V to give the LDO headroom; every other device on it preferred 3.3 V. Feeding
the LDO from the battery instead drops the rail to 3.25 V, and the ceilings stop being
tight: 3.54 V worst case against 3.6 V. The playback converter's digital supply still has
to move to the analog rail, because 3.46 V is below even that. `power-supply.md` §2a
carries the full trade, including what it costs in runtime — about 0.8 %.

**Sequencing changed and is confirmed harmless.** The rails are now siblings rather than a
cascade, and the analog rail generally rises first. SBAS892A: *"The power-supply sequence
between the IOVDD and AVDD rails can be applied in any order."* It adds three constraints
that are met by construction — the shutdown pin held low until the I/O supply is stable
(its pull-down does that), a supply ramp slower than 1 V/µs, and at least 100 ms between a
power-down and the next power-up. For the playback converter the new order is the better
one: it is fully powered before the MCU's rail is up, so nothing can drive its inputs
before it is ready.

### BU-P6 — Cell, connector and battery sense
*Gate: G1*

**Pending**

- [ ] Cell choice, its connector and polarity.
- [ ] Sense divider accuracy against an analog reference that is internally tied to the
      analog supply on this package.

---

## 3. Debug access

### BU-D1 — The debugger will not connect
*Gate: G2. The master risk.* Programming and debug are exclusively through the debug
header — no USB, no bootloader connector, no serial fallback. If it is wrong, every risk
from G3 down becomes unevaluable at once.

**Pending**

- [ ] **Remove the pin at position 7.** The pad stays; the pin comes out at assembly. The
      standard makes that position the key — SEGGER: *"Position 7 has no pin and serves
      only as a key to properly orient the connector."* A fitted 10-pin header will not
      seat against a socket plugged at 7. Put it on the assembly drawing: the header is
      hand-fitted, so it is a step that can be forgotten.
- [ ] **Check which keying the probe cable uses.** Socket plugged at 7 → the removed pin
      polarizes it and nothing more is needed. Open socket keying against a shroud bump →
      there is no mechanical polarization on this board and it falls to silkscreen.
- [ ] **Mark pin 1 on silkscreen** either way.
- [ ] **Through-hole part** — standard assembly will not place it. Exclude it consistently
      from both the BOM and the position file, or hand-fit.
- [ ] **Check clearance against the socket body, not the header.** Nearest neighbour is
      5.55 mm from the header centre; an IDC socket is roughly 10 × 6 mm plus cable strain
      relief.

**Analysis**

Electrically correct as drawn, verified pad by pad against the Cortex Debug 10-pin
standard: VTref on the digital rail, SWDIO and SWCLK on their MCU pins, SWO wired, ground
on 3/5/9, and reset joining the header, the 100 nF and the MCU reset pad on one net.
BOOT0 is pulled down 10 kΩ to ground, selecting internal flash.

**The header is unshrouded by decision, not oversight** — no room in the corner, and the
prior Daisy-based work used bare headers throughout. That decision costs nothing provided
position 7 is depopulated, because reversal maps position n to 11−n and 7 lands on 4,
which is populated. The removed pin is the key; the shroud is belt-and-braces. Recorded
in `pin-allocation.md` §3, which had been carrying the pinout without the decision behind
it.

### DX-D2 — Probe access for diagnosis
*Gate: G0*

**Pending**

- [ ] Confirm three grabbers fit the codec-bus vias, which sit on a diagonal at ~1.06 mm
      centres. TDM decode needs bit clock, frame sync and data at once. Spread to ~2 mm if
      there is room.
- [ ] Rename the test-point footprints — both mix two notations in one name. The form
      `TestPoint_Loop_D0.7mm_Pad1.2mm` reads only one way.

**Analysis**

Coverage is complete, verified against the board rather than the doc. The three ground
points carry the 1.2 mm / 0.7 mm loop footprint, and the central one sits within 7 mm of
the codec bus, the DAC bus, I²C and the clock point. The codec
TDM bus, the DAC I²S bus and I²C all carry **Ø0.7 mm untented vias on 0.4 mm drills**,
distinguishable from the board's 200 Ø0.6 routing vias by size and tenting. The clock
output and three grounds have dedicated pads. The module's UART is probeable at its
castellated pad tabs — 0.9 × 0.8 mm of exposed copper per pin outside the module body,
larger targets than the test vias, which satisfies the requirement in
`bluetooth-constraints.md` §6. Rails are reachable at connectors and bulk capacitors.

Full detail in `test-points.md`, rewritten to match the board.

## 4. Clock

### BU-C1 — Crystal doesn't start
*Gate: G2. Closed on the board; one bench check remains.*

**Pending**

- [ ] Measure drive level at bring-up. The 1612 package is rated 100 µW, well below a
      larger can's. Known remedy if it is high: raise the drive-side load capacitor, which
      is a stuffing change.

**Analysis**

Verified on the board: NDK NX1612SA-24MHZ-STD-CIS-1 (LCSC C280834, CL 8 pF), load
capacitors **6.8 pF** on both legs, four-pin symbol with ground on pads 2 and 4 matching a
part whose ground pads tie to the can, each capacitor between one oscillator leg and
ground with nothing else on either net, and both sitting ~2 mm from the crystal.

**The risk here was starting, not accuracy.** Frequency error is irrelevant on this board:
the audio rate is derived internally, the DAC's rate detection tolerates ±4 %, the codecs
slave off the bit clock, and every interface is analog. What matters is negative-resistance
margin, which falls roughly as 1/CL². The earlier 15 pF pair presented ~12 pF to an 8 pF
crystal — a 50 % overload and a substantial cut in startup margin, the failure this entry
names. **So err small**: under-capping costs accuracy that is not needed and buys margin
that is.

**No damping resistor, by decision.** The usual series resistor at the drive pin guards
against excessive drive, and the same correction is available from a part already placed —
raising the drive-side load capacitor. That is a stuffing change rather than a respin, and
the frequency shift it causes does not matter for the reasons above. Against that, the
oscillator traces are 5.7 and 6.4 mm with the pads under 4.2 mm apart; inserting an 0402
in series lengthens the drive leg and opens the loop. Keeping the crystal tight is worth
more.

*Optional tidies, not defects:* the Value field reads `24Mhz` and does not carry the CL,
which is the parameter that sets the capacitors — the LCSC field makes it unambiguous for
ordering, so this only matters to a human reading the sheet. The capacitors do not state
C0G; at 6.8 pF nothing else is really manufacturable, but stating it guards against a
substitution.

### BU-C2 — PLL chain doesn't produce the intended audio clock
*Gate: G2. Low — firmware configuration with a graceful fallback.*

**Pending**

- [ ] Confirm `RCC_PLL3DIVR` DIVP3 accepts odd division factors, at firmware bring-up.
      The "odd division factors are not allowed" note is documented on the system-clock
      P divider (PLL1) and does not appear to apply to PLL2/PLL3, but that is unconfirmed.

**Analysis**

The intended chain is exact: 24.000 MHz, M=5, N=128, **P=25** → PLL3_P = 24.576 MHz, from
which ÷3 gives the 8.192 MHz codec bit clock and ÷12 the 2.048 MHz DAC bit clock, both
exactly 256× and 64× a 32 kHz sample rate.

P=25 is odd because 24.576/24.000 = 128/125 and 125 is 5³; the PLL's input-frequency and
VCO limits force those factors into P. There is no even-P solution that lands on 24.576 MHz
exactly.

**But exactness is not required on this board, and that is the whole reason this is a
minor item.** Every input and output is analog — no external device ever has to agree
about the sample rate. The codec's programmable range is 7.35–768 kHz, the DAC derives its
rate from the bit clock, and 32 kHz was itself chosen for DSP cost and bass bandwidth
rather than because it is a standard. So if DIVP3 rejects odd values, the fallback is
simply a nearby rate:

```
M=5, N=133, P=26 → VCO 638.4 MHz → PLL3_P = 24.554 MHz → fs = 31.971 kHz
```

0.09 % from nominal, VCO in range, ÷3 and ÷12 structure unchanged. The consequence is one
constant in the firmware.

*Correction, recorded because the mistake is easy to repeat:* this entry previously
claimed the remedy would be a different crystal frequency, and rated it as a pre-fab
blocker. That imported a "the audio clock must be exact" constraint from designs with
digital interfaces, which this board does not have. Nothing here is a board risk.

## 5. Capture — digital

### BU-A1 — Codecs don't enumerate on the control bus
*Gate: G2. Board items closed; three entry and firmware items remain.*

**Pending**

- [ ] The **status LED series resistor is still unvalued and unannotated** — it carries a
      placeholder value and a placeholder reference. `pin-allocation.md` resolves the value
      at 1 kΩ. Annotate, value, then *Update PCB from Schematic*.
- [ ] Also propagate the I²C pull-up values: the schematic reads 4.7 kΩ, the board still
      reads the placeholder. One *Update PCB from Schematic* covers both.
- [ ] **Firmware must set the analog-regulator select bit.** SBAS892A: the internal 1.8 V
      analog regulator is used *"when AVDD is 3.3 V"*, but the bit that selects it (page 0,
      register 2, bit 7) **resets to the external-supply setting**. This board has no
      external 1.8 V supply and does not short that pin to the analog rail, so leaving the
      default means the analog section has no regulator behind it. Set it while exiting
      sleep mode, per the datasheet's own sequence.

**Analysis**

**The bias outputs are deliberately unconnected.** Their power-control bit resets to
"powered down" and SBAS892A states the output is off by default, so the pins are never
driven and need no capacitor. The only firmware obligation is to leave that bit alone.

**The reset line is deliberately shared between the two devices.** The output-channel-enable
register resets with every slot tri-stated, and the shutdown line is held low by its
pull-down until firmware drives it, so releasing both devices together creates no
contention window — BU-A3 carries that reasoning. Per-device recovery survives via the
software-reset bit over I²C, so nothing is lost by sharing. No spare MCU pin is reserved
for splitting it.

**Addresses, settled against SBAS892A Table 50.** The five MSBs are fixed at `10011`; the
two LSBs come from the strap pins, which the datasheet requires be tied to VSS or IOVDD —
the pull-ups go to the digital rail, which *is* IOVDD here.

| | ADDR1 | ADDR0 | Address |
|---|---|---|---|
| ADC-A | IOVDD | GND | **0x4E** |
| ADC-B | GND | IOVDD | **0x4D** |
| broadcast (`I2C_BRDCAST_EN`) | — | — | **0x4C** |

Both devices are distinct from each other *and* from the broadcast address, so a single
write can configure both identically — worth having with two codecs on a shared TDM bus —
without one device's individual address colliding with it.

**Resistor values, and why they differ.** Straps are 10 kΩ; pull-ups are 4.7 kΩ. These are
not the same kind of resistor. The straps are static — they hold a DC level against a CMOS
input's leakage, so anything from 1 kΩ to 100 kΩ behaves identically and 10 kΩ is
convention. The pull-ups are dynamic: on an open-drain bus they charge the bus capacitance
on every rising edge, and that rise time sets the speed limit, giving a real window of
about 1 kΩ (sink current) to ~11 kΩ (rise time at 400 kHz). 10 kΩ lands at 254 ns against
a 300 ns limit — 15 % margin against an estimated rather than measured capacitance. 4.7 kΩ
gives ~120 ns.

*One-value alternative if part-count tidiness ever matters more:* 10 kΩ everywhere with
the bus at 100 kHz, where the limit is 1000 ns and 10 kΩ has 4× margin even at 50 pF.
Costs tens of milliseconds at startup, once.

**Capacitors — two unrelated families, and only one of them went away.** The
input coupling and matching capacitors went with the DC-differential change and are
correctly absent: every `INxP` runs straight to its connector pin and every `INxM` straight
to the bias net, on all eight channels. Separately, AREG, VREF and DREG are *outputs* of
on-chip regulators and a reference; their capacitors are mandatory for loop stability and
reference settling regardless of input topology, and all six are fitted at 1 µF.

**Decoupling** is adequate but not as specified: the analog supply has 0.1 µF at 1.63 and
1.75 mm, while neither IOVDD pin has a 0.1 µF at it — nearest same-net part is a 1 µF at
1.20 mm on one device and 2.57 mm on the other. In the same package a 1 µF is no worse at
high frequency, so this is accepted rather than fixed.

### BU-A2 — TDM bus doesn't clock, or clocks wrong
*Gate: G3. No board content — firmware effort, and self-announcing.*

**Pending**

- [ ] Verify SAI4_B master-**receiver** TDM configuration against RM0468, plus BDMA
      request routing for the D3 domain, buffers in SRAM4, and D-cache coherency for that
      region. This is the substantive work in the entry.
- [ ] Spot-check the six audio-pin alternate-function numbers against DS13311 at firmware
      bring-up. Low: they come from two independent machine-derived sources that agree,
      and a wrong AF produces no signal at all on a bus that now has test points on it.

**Analysis**

**The copper is verified.** All six audio signals sit on the pads the plan documents —
frame sync and bit clock and serial data for the codec bus, and bit clock, word select and
data for the DAC. The master-clock reserve pin is unconnected, correct for a scheme that
distributes no master clock. Nothing here can be wrong in a way that fab would make
permanent.

**The codec auto-configures its clocking.** `AUTO_CLK_CFG` defaults to enabled, deriving
every internal divider and the PLL from the observed FSYNC frequency and BCLK-to-FSYNC
ratio. This board runs 32 kHz at a 256× ratio — listed as a supported combination in SBAS892A
Table 6, which gives exactly 8.192 MHz for that pairing, against an 18.5 MHz timing
ceiling. So there is no manual PLL
programming to get wrong in the normal case, and TI recommends leaving the PLL in rather
than clocking directly from BCLK, which is what the plan does.

**And an unsupported combination announces itself.** SBAS892A: *"If the device finds any
unsupported combinations of FSYNC frequency and BCLK to FSYNC ratios, the device generates
an ASI clock-error interrupt and mutes the record channels accordingly."* The fault latches
in a read-only status register, so it is pollable over I²C — the interrupt pin itself is
unconnected, which is fine. A clocking error therefore presents as a readable fault code
rather than as silence, which is unusual and worth relying on during bring-up.

**What remains is effort, not uncertainty.** The plan's own firmware estimate puts the
SAI stereo-to-TDM rework at 1–3 days and dual-codec shared-bus integration at 1–3 days,
calling the latter the tail risk that can eat a week. The mitigations are already in place:
test points on all three bus signals so a logic analyser can decode them, and the
instruction to prove slot steering with one codec before putting both on the bus.

### BU-A3 — The two codecs fight on the shared serial-data line
*Gate: G6*

**Pending**

- [x] ~~Decide the bus-float treatment before fab.~~ **Done 2026-09-24: a 10 kΩ pull-down to
      ground is fitted on the shared data net.** Chosen over the ~100 kΩ originally sketched
      and over relying on the codecs' bus-keeper alone: 10 kΩ costs 325 µA of DC load when
      the bus is driven high, which is nothing against CMOS drive, and it settles the net in
      about 150 ns — inside the region of a 122 ns bit period, where 100 kΩ would have taken
      longer than a bit to define anything.
- [ ] Set the unused-cycle bit to Hi-Z on **both** codecs before enabling either. It
      defaults to drive-zero (see analysis) — this is the one default that guarantees
      contention.
- [ ] Assign distinct slots before enabling any output channel. Every channel on both
      devices defaults to slot 0.
- [ ] Bring up one codec at a time, then both. Enable the second only after the first
      is producing correct data in its own slots.
- [ ] Note for the fallback plan: the secondary data-lane pin is **unconnected on both
      codecs**. If the shared lane proves troublesome there is no second lane without a
      bodge wire. Decide now whether that is acceptable.
- [ ] Run *Update PCB from Schematic* — the I²C pull-ups read 4.7 K in the schematic and
      still read `R` on the board.

**Analysis**

Confirmed from the board: both codecs' data outputs sit on the same net as the MCU
receive pin, they share bit clock, frame sync and I²C, and they share one shutdown line
that carries a 10 K pull-down to ground and is driven by an MCU GPIO.

**There is no power-up contention window.** The ASI output channel enable register resets
to 0x00, which puts *every* output slot in a tri-state condition, and the shared shutdown
line is held low by its pull-down until firmware drives it. Nothing drives the data net
until firmware deliberately enables a channel. That also settles the shared-versus-split
reset question carried over from BU-A1: shared is fine. Per-device recovery is still
available — the software-reset bit (page 0, register 1, bit 0) restores one device's
defaults over I²C — so a wedged bus never needs a power cycle.

Contention is therefore purely a configuration fault, and two specific defaults cause it:

1. **Unused-cycle behaviour defaults to drive-zero.** ASI configuration register 0, bit 0,
   resets to 0 = "always transmit 0 for unused cycles". With both devices enabled at their
   defaults, both drive the entire frame. This must be set to 1 (Hi-Z) on both.
2. **All channels default to slot 0.** The per-channel slot registers all reset to 0, so
   without explicit assignment the two devices collide on the same slots.

Once unused cycles are Hi-Z the net is undriven outside a device's own slots. In steady
state that window is empty — eight channels of 32-bit slots exactly fill the 256-cycle
frame — but it is real during bring-up when only one device is enabled. The bus-keeper
field (ASI configuration register 1, bits 6:5) holds the last driven value; the
LSB-only options exist precisely so two keepers on one net do not fight each other. The
half-cycle LSB release (bit 7) gives turnaround between adjacent slots owned by different
devices. These are the settings to reach for if the bench shows a dirty handoff.

The clean enable sequence uses I²C broadcast. Setting the broadcast-enable bit makes a
device answer at address 1001100 (0x4C) so one write reaches both. The straps on this
board give 1001110 (0x4E) and 1001101 (0x4D) — neither is 0x4C, so the broadcast address
is free and conflict-free, and both devices' outputs can be enabled in a single
transaction rather than through a window where one is driving and the other is not.

Everything above is a register value. This risk cannot consume the respin budget; only the
pull-down footprint decision is a board-level choice, and it is a decision to add a part,
not to move one.

### BU-A4 — Capture runs but the data is wrong
*Gate: G6*

**Pending**

- [ ] Fix and record the slot map. Proposal: the 0x4E device takes slots 0–3, the 0x4D
      device takes slots 4–7, channels in ascending order. Keep every channel's output-line
      bit at 0 (primary pin) — the secondary pin is not routed.
- [ ] Configure the MCU receiver to match the codecs' default framing: TDM, no slot
      offset, MSB first, 32-bit slots, 8 slots per frame, data starting on the frame-sync
      edge. Both ends must agree on frame-sync polarity, bit-clock edge and offset; all
      four are register fields on both sides.
- [ ] **Choose the decimation filter deliberately** — see analysis. The default is the
      slowest one. This is a latency decision, not a quality one, and belongs with the
      playback-side and block-size choices rather than being left at reset.
- [ ] Leave the high-pass at its default and record why. Confirm on the bench that the
      corner behaves as calculated at the actual sample rate.
- [ ] Verify inter-device sample alignment on the bench: excite one string, capture both
      devices, confirm no frame-level skew between them.
- [ ] Select the DC-coupled input impedance explicitly (10 kΩ or 20 kΩ) — the 2.5 kΩ
      default is not supported for DC-coupled inputs. Carried from PG-A5 because it shows
      up as wrong data, not as a dead channel.

**Analysis**

**The clock plan is a documented supported combination** — SBAS892A Table 6, covered
under BU-A2. The auto-configuration block accepts it without host programming, so the
fault mode where a codec raises a clock error and refuses to run does not apply here.

**The slot budget is exactly full.** Eight channels at the default 32-bit slot length
consume 256 bit-clock cycles, which is the whole frame. There is no spare slot. If the
word length is ever reduced the slot map must be recomputed, and anything needing a ninth
slot forces the ratio to 512 and a new clock tree.

**The high-pass is benign at this sample rate, and that is worth stating rather than
assuming.** The filter selection field defaults to a corner of 0.00025 × fs, which at
32 kHz is **8 Hz**. The lowest note in scope — low B at 30.87 Hz — sits nearly two octaves
above a first-order 8 Hz corner: roughly −0.3 dB and about 14° of phase. The next setting
up is 0.002 × fs = 64 Hz, which is *above* the low E fundamental and must not be selected.
Equally important for a per-string array: the high-pass is a **global** setting, not a
per-channel one, so all eight strings receive identical magnitude and phase and the
inter-string phase relationships survive intact. The concern that opened this item — a
filter whose loss nothing downstream can undo — resolves to "correct at the default, one
click away from wrong".

**The decimation filter is a real latency choice and the default is the worst one for an
instrument.** The filter-response field defaults to linear phase, whose group delay is
17.1 / fs — **534 µs** at 32 kHz. The low-latency option gives 11.9 / fs ≈ 372 µs with a
passband to 0.3 × fs (9.6 kHz), and the ultra-low-latency option 5.9 / fs ≈ 184 µs with a
passband to 0.113 × fs (3.6 kHz). For a plucked instrument, a third of a millisecond on
the capture side alone is a meaningful share of the round-trip budget before the playback
path and the processing block are counted, and the bass content in question sits far below
even the narrowest passband on offer. This is a deliberate trade to make, not a default to
inherit.

**Inter-device alignment comes from the shared clocks.** Both codecs take bit clock and
frame sync from the same master and derive their internal clocks by monitoring those
signals, and the shared shutdown line releases them together — so they sample on the same
frame by construction. The datasheet lists simultaneous sampling across devices as an
explicit multi-device feature. Worth confirming on the bench rather than assuming, but
there is no mechanism here that would let them drift.

Every item in this entry is a register value on one side of the bus or the other. Like
BU-A2 and BU-A3, it cannot cost a spin.

---

## 6. Capture — analog

### PG-A5 — DC-coupled differential input topology
*Gate: G7 for the blocking check*

**Pending**

- [ ] **Close the blocking check: the converter's DC-coupled common-mode window.**
      SBAS892A states none — confirmed by search. Needs TI application material or a
      bench measurement on the real board.
- [ ] **Rewrite `adc-netlist.md` §2.1 as adopted rather than proposed.** The topology is
      committed: the main board generates the bias, buffers it, and routes it to both
      converters and — through the pickup connectors — to the preamp boards, which
      re-buffer it locally. The pin and power tables in that document have been corrected
      against the board; §2.1's prose has not.
- [ ] **Correct the cable-capacitance figure in `adc-netlist.md`.** 50–100 pF per conductor
      is instrument-cable territory; a few inches of loose parallel wire is roughly 1 pF per
      inch, so the buffer's cable load is single-digit pF. That figure is the whole basis of
      the buffer-stability item, which closes with it.
- [ ] Reconcile the reference buffer part — §2.1 names an OPA376, the board carries a
      TLV9001.
- [ ] Cold-pin high-frequency bypass: **DNP footprint per converter**, unpopulated, plus
      a 0 Ω position at the buffer output. Not fitted now.

**Analysis**

The topology is committed. Reference generator is a 100 kΩ / 68 kΩ divider from the
analog rail giving **1.336 V**, filtered by a 10 µF tantalum and buffered by a unity-gain
follower (pin map verified against the TLV9001 datasheet — divider into IN+, output tied
back to IN−). That is 2.8 % under the converter's VREF/2, comfortably inside VREF's own
tolerance, with a 40 kΩ source and a 0.39 Hz filter corner.

The buffer sits on the analog side, symmetric between the two converters and between the
pickup connectors, ~12 mm from the cold pins — so both converters see matched reference
impedance, and 12 mm over a solid plane is ~10 nH, which is 1.3 mΩ at 20 kHz. The cold
pins are already on a low-impedance node, which is why the local bypass is a DNP footprint
rather than a fitted part.

One firmware constraint follows from the topology: SBAS892A states that *"the input
impedance value of 2.5 kΩ is not supported for the DC-coupled input."* That is the
default setting, so the driver must select 10 kΩ or 20 kΩ before the inputs are usable.

### BU-A6 — Input bias and power-up behaviour
*Gate: G1*

**Pending**

- [ ] **Decide whether hot-plugging a preamp board is permitted**, and if so confirm the
      housing enforces the mating order. Ground sits on the end pin of the 7-way connector,
      so a straight insertion mates it first — but that is a property of how the shell is
      keyed, not of the pinout, and it is the only remaining path to an out-of-range input.
- [ ] At first power-up, scope one hot pin against its own cold pin through the first
      second and confirm they rise together. This is a two-minute confirmation of the
      argument below, not an open question.

**Analysis**

**The window this item was written about does not exist, because there is only one rail
and one reference.** Each pickup connector carries ground, the bias reference, the analog
rail and four signals. The bias reference is derived from the analog rail; the preamp
boards are powered from that same rail, arriving on that same connector. There is no
sequencing between "bias up" and "preamps up" to get wrong — they are the same event.

**Both sides of every differential pair are referenced to the same node.** Each cold pin
ties straight to the bias net. On the preamp board the incoming bias is re-buffered
locally, and each channel's feedback network returns to that buffered node, so every
preamp output's DC level *is* the bias voltage. Hot and cold therefore track each other
by construction rather than by matching.

**The slow ramp is common mode, not differential.** The bias node is deliberately the slow
one — 10 µF against a 40 kΩ source is a 0.4 s time constant, against milliseconds for the
rail itself. Because both sides of each pair follow that node, the codec sees the ramp as
common mode and the differential voltage stays near zero throughout.

**The absolute-maximum case is closed by construction.** SBAS892A rates the analog input
pins from AVSS − 0.3 V to AVDD + 0.3 V. AVDD here is the analog rail, and a preamp output
cannot exceed its own supply — which is that same rail, reaching the preamp board through
the same connector. A rail-powered source cannot overdrive a pin rated to its own rail.

**And nothing is listening during the transient in any case.** The ADC power-control bit
and every output-channel enable reset to off, so the codecs are not converting while the
rail comes up; firmware brings them up long after it has settled. There is no path to an
audible thump.

The clamp diodes that went with the AC-coupled design protected against a differential
offset between two independently referenced sides. That condition was removed along with
the topology — it was not left uncovered.

### BU-A7 — Pickup connector and harness
*Gate: G0*

**Pending**

- [ ] **Correct `layout-notes.md` §7 item 7b.** It still describes the preamp end as a
      1.0 mm right-angle SMT header and the main board as carrying 2.54 mm vertical
      headers. Both halves are stale; the boards agree with each other and with
      `preamp-board.md` §10.
- [ ] **Reconcile `preamp-board.md` §10 with the main board.** §10 weighs the termination
      choice against "the main-board end, which is soldered already" — but the main board
      carries the *same* header footprint as the preamp board, so the main-board end has
      the same three terminations available and the same decision to make. Either fit a
      header there too and make the harness detachable at both ends, or record that the
      main-board end is soldered into the holes and say why.
- [ ] **Specify the harness.** Both ends are male pin headers, so the mating part is a
      double-ended female cable — currently not specified anywhere. It follows the same
      crimp-versus-solder evaluation §10 has open for the preamp end, and it needs a
      length, a conductor count and a decision on whether both ends are detachable.
- [ ] **Confirm edge clearance on the main board** for the right-angle body plus the cable
      exit — the constraint that drove the original fine-pitch selection was main-board
      edge space, and that claim has never been checked against the placement as it now
      stands.
- [ ] **Record the string-to-channel map.** A straight-through harness maps the preamp
      board's first channel to the first converter input; confirm that is what the
      pin ordering actually produces on both neck and bridge, and write down which physical
      string each channel is, so firmware inherits a map rather than discovering one.

**Analysis**

**The connectors agree — this is no longer a respin candidate.** Both the main board and
the preamp board carry a 1×7 through-hole right-angle header at 2.00 mm pitch, which is
exactly what `preamp-board.md` §10 specifies, including its seventh position for the bias
reference. The inconsistency this entry was opened for lives in `layout-notes.md`, not in
the boards.

**Pinout, verified on both boards:** ground, bias reference, analog rail, then four signal
positions. Straight-through, position for position, at both ends.

**Polarity is already decided and is not re-opened here.** `preamp-board.md` §10 records
the connector as unkeyed with no reverse-polarity protection, mitigated by a colour-coded
cable, a silkscreen pin-1 indicator and a single builder. Worth noting only that the
pinout as built lands on the *recoverable* side of that document's own analysis: supply
and ground do not sit at mirror positions, so a reversed insertion leaves the preamp board
unpowered and drives the rail into two amplifier outputs through their output protection,
rather than applying the rail backwards across the board.

What remains in this entry is a harness that does not exist yet and two documents that
disagree with the boards. None of it is a board change.

### PF-A8 — Gain staging and level
*Gate: G7*

**Pending**

- [ ] **Measure the pick-attack transient** on a real string and set the static channel
      gain from it, not from the sustained level. The arithmetic below says ~19 dB closes
      the gap to nominal full scale; the useful setting is that minus whatever headroom the
      attack needs, which on a plucked string is easily 10 dB.
- [ ] **Confirm the full-scale figure survives DC coupling.** The 1 VRMS and 2 VRMS
      numbers below are both specified for an *AC-coupled* input; SBAS892A gives no
      DC-coupled equivalent. This is the same gap PG-A5 is blocked on, and the gain plan
      inherits it.
- [ ] Verify the preamp feedback resistor tolerance is 1 % — see the matching argument
      below, which depends on it only weakly but should not rest on an assumption.
- [ ] Record the firmware constraint: **channel gain must be set before the ADC channel is
      powered up and must not change while it is running.** Runtime level control belongs to
      the digital volume control, which is a different register and is designed to move.

**Analysis**

**The gap is about 19 dB, and it is comfortably inside the available range.** The coil
measures 40 mVpp (`analog-front-end.md` §1). The preamp is non-inverting with a 15 kΩ
feedback and 2.2 kΩ to the bias node, so its gain is 1 + 15/2.2 = **7.82×, or 17.9 dB**,
putting roughly 313 mVpp — about 111 mVRMS — at the converter pin. That matches the
≈320 mVpp already carried in `adc-netlist.md`, from an independent estimate.

Against the converter's single-ended full-scale AC signal voltage of 1 VRMS at 3.3 V AVDD,
that leaves **19.1 dB**. The single-ended figure is the right one to plan against even
though the input is wired differentially: the cold pin is held at a fixed bias and only the
hot pin swings, so the drive is one-sided. (The 2 VRMS differential figure assumes both
pins swinging in antiphase, which this topology does not do.)

**The converter's gain range covers it in the low-noise way.** Channel gain is 0–42 dB in
1 dB steps, and TI states the internal logic maximises the front-end low-noise analog PGA
first and only then applies residual gain in the digital block — so a request in this range
lands mostly in the analog PGA, which is where it belongs. 19 dB of the 42 available also
means the setting can be backed off substantially for attack headroom without running out.

**Channel matching needs no trim worth worrying about.** Per-channel gain calibration
covers ±0.8 dB in 0.1 dB steps. The preamp gain is set by a 15 kΩ / 2.2 kΩ ratio; at 1 %
that ratio varies about ±0.9 %, which is ±0.08 dB — two decimal places below the trim's
resolution. Even at 5 % the spread stays inside the trim range. Matching is effectively
free here; the trim exists for cases far worse than this one.

**Runtime level is a separate mechanism.** Digital volume control spans −100 dB to +27 dB
in 0.5 dB steps, is changeable while the channel is running, and soft-steps to avoid
artefacts. That is the knob firmware moves. Channel gain is the one it sets once, before
power-up, and leaves alone.

The noise consequence of putting ~19 dB in the converter rather than in the preamp belongs
with `preamp-noise-analysis-by-hand.md` and is not re-derived here; the relevant point for
this entry is that the gain lands in the analog PGA rather than in the digital block.

---

## 7. Playback

Lower risk than capture and brought up first, because it proves the clock tree and a
transmit path without the control bus or the codecs.

### BU-DA1 — Strap configuration
*Gate: G3*

**Pending**

- [ ] **Pair the filter strap with the converter's decimation-filter choice (BU-A4).** The
      strap is at ground, selecting the normal-latency interpolation filter; tying it high
      selects low latency. Capture and playback should be decided together against one
      round-trip budget, not separately at their defaults.
- [ ] Record the firmware ordering requirement the clock strap creates — see analysis. It
      is 0.5 ms at this sample rate, but it is a *requirement*, not a guideline.

**Analysis**

**All four straps verified against SLAS859C and all four are correct.**

| Strap | Board | Meaning |
|---|---|---|
| Format | ground | I²S — matches the transmitter |
| De-emphasis | ground | off; de-emphasis is a 44.1 kHz feature and this board runs 32 kHz |
| Filter | ground | normal-latency interpolation filter |
| System clock | **ground** | selects the internal PLL — see below |
| Soft mute | MCU GPIO | under firmware control |

**The clock strap is the one that was worth checking, and it is right.** No master clock
is routed, so the part must derive its own. SLAS859C §9.3.5.3 documents exactly this:
*"The device starts up expecting an external SCK input, but if BCK and LRCK start
correctly while SCK remains at ground level for 16 successive LRCK periods, then the
internal PLL starts, automatically generating an internal SCK from the BCK reference."*

That sentence contains a firmware requirement: **the bit clock and word clock must be
running and correct for at least 16 word-clock periods before the PLL will start** —
0.5 ms at 32 kHz. Starting the transmitter and immediately expecting audio does not work,
and the failure looks like silence from a part that is otherwise alive. Un-mute belongs
after that window, not before it.

### BU-DA2 — Playback clock outside the rate-detection window
*Gate: G3*

**Pending**

- [ ] Nothing. Retained because the reasoning is worth keeping; delete at the next pass if
      the bench agrees.

**Analysis**

**The planned combination is listed explicitly.** SLAS859C Table 11 gives the bit-clock
rates that let the internal PLL generate a master clock, and **32 kHz at 64 × fs =
2.048 MHz is a row in that table** — exactly what the clock tree produces. Table 2
independently constrains the bit-clock rate to 64, 48 or 32 × fs; the board uses 64.

**This entry's stated dependency on BU-C2 was wrong and is removed.** The PLL locks to
whatever bit clock it is given; Table 11 constrains the *ratio*, not the absolute
frequency. If BU-C2 lands on 31.971 kHz instead of 32.000 kHz, the ratio is still 64 and
the part still locks.

**And the failure mode is self-announcing and self-clearing.** SLAS859C: if the word-clock
to system-clock relationship moves by more than ±5 system-clock periods, or the word-clock
to bit-clock relationship is invalid for more than 4 word-clock periods, the device
reinitialises within one sample period and holds the outputs at bipolar zero until it
resynchronises. A clocking glitch therefore presents as a brief mute followed by recovery,
not as a latch-up needing a power cycle.

### BU-DA3 — Charge pump and mute
*Gate: G1/G3*

**Pending**

- [ ] **Add a pull-down on the soft-mute line.** It is driven only by an MCU GPIO, with no
      passive. Through power-up and through every MCU reset that pin is a high-impedance
      input, which leaves the mute control **floating, not low** — and floating on a
      Schmitt-trigger input is undefined, so the part may come up un-muted. A 10 kΩ to
      ground makes muted the default state. This is a part to add, so it is a pre-fab item.

**Analysis**

**The mandatory capacitor set is complete.** Charge-pump flying capacitor 2.2 µF across
the two flying terminals, negative-rail reservoir 2.2 µF to ground, internal-LDO output
2.2 µF to ground. Supply decoupling is good: 0.1 µF within 1.1 mm of the charge-pump
supply pin, 1.7 mm of the analog supply pin and 1.4 mm of the digital supply pin.

*Recorded so it is not re-raised:* the LDO output pin description in SLAS859C says
"should be used with a 0.1-µF decoupling cap", while the board carries 2.2 µF. TI's own
typical-application schematic in §10.1.1 shows 2.2 µF there. The larger value is the
reference design's, not an error.

**The soft-mute pin is the one real gap.** The pin is active-low — low mutes, high
un-mutes — so the safe default is low, and nothing on the board holds it there. The pin is
specified as a failsafe input, which means it tolerates voltage with the supply off; it
does not mean it defaults to a level.

This also connects to BU-P1's open power-good decision: with power-good tied to ground
there is no hardware interlock available to gate un-mute on the rail being up, so the
ordering rests entirely on firmware plus whatever passive default the mute pin has.

### PF-DA4 — Output level and load
*Gate: G5*

**Pending**

- [x] ~~Raise the L-pad shunt resistor from 62 Ω.~~ **Done: 470 Ω.** One resistor, same
      footprint. Takes the jack from ~0.10 Vrms to **0.572 Vrms** at full rotation, and as a
      side effect raises the converter's load from 1.26 kΩ to 1.65 kΩ against a 1 kΩ minimum.
      The series resistor stays at 1.2 kΩ — it is what guarantees the converter never sees
      less than that whatever happens downstream. (390 Ω was the first pick; it proved
      Extended-only at assembly, and the value is loose enough that the substitution was free.)
- [x] ~~Ultrasonic shunt capacitor across the shunt resistor.~~ **Fitted: 2.2 nF** — TI's own
      value in that network — giving a **221 kHz** corner at the pad's 327 Ω node impedance and
      −0.04 dB at 20 kHz. Populated rather than DNP, which is fine: it is far above audio and
      avoids do-not-populate handling at assembly. 10 nF was rejected: it would pull the corner
      to 49 kHz and put −0.68 dB at 20 kHz, an in-band deviation for nothing.
- [ ] Pick the audio-taper pot part (carried from `dac-selection.md` §8).
- [x] ~~Rename or drop the label on the unused right output.~~ **Done 2026-09-24 — the label
      is removed in the schematic.** A test pad there was checked against the layout and there
      was no room; nothing is lost, because the converter is a TSSOP with accessible gull-wing
      leads, so the *left* output is directly probeable at its own lead. ⚠ Needs *Update PCB
      from Schematic* to clear the old net name from the layout.
- [ ] Confirm the level on the bench against the amplifier actually used, and adjust the
      shunt if wanted — 330 Ω gives 0.44 V, 560 Ω gives 0.64 V, 680 Ω gives 0.73 V, 1 kΩ gives
      0.91 V.

**Analysis**

**Full scale is 2.1 Vrms single-ended, ground-centred**, with gain error specified as
−6 % to +6 % — tighter than the ±10 % this entry previously assumed. The negative-rail
charge pump is what buys the ground-centred output, which is why there is no coupling
capacitor anywhere in the chain.

**The pad as originally entered was too quiet.** 1.2 kΩ into 62 Ω (in parallel with the
10 kΩ volume pot) is −26.2 dB, giving 0.103 Vrms — roughly 10 dB under consumer line
nominal and at the quiet end of *passive* pickup territory, on an instrument whose whole
purpose is an active front end.

**470 Ω puts it at 0.572 Vrms, −11.3 dB.** That is squarely in active-instrument range,
about 5 dB above consumer line nominal, and leaves any padding to the amplifier input that
is designed to do it. The volume pot sits *after* the pad, so raising the maximum costs
nothing in control — it only adds range the player previously did not have.

**Raising the shunt resistor improves two things at once,** which is the part worth
noticing: the level goes up *and* the converter's load resistance goes up. At 62 Ω the load
was 1.26 kΩ against a 1 kΩ recommended minimum — 26 % of margin, tighter than it needed to
be. At 470 Ω it is 1.65 kΩ.

**Everything else about the chain is unchanged.** Source impedance at the jack is still the
pot wiper, worst case ~2.5 kΩ at mid-rotation, giving a ~127 kHz pole into 500 pF of cable.
Short-circuit behaviour is unchanged: a shorted jack grounds the wiper and the converter
still sees the 1.2 kΩ series resistor alone. The pad's own Johnson noise at 327 Ω is
0.33 µVrms over 20 kHz — 125 dB below the output.

**Why not remove the pad entirely.** 2.1 Vrms is +4.6 dBu, above pro line level; it would
clip most instrument inputs at full rotation, and dropping the series resistor would give
up the short-circuit protection it provides. The pad stays; only its ratio changes.

**On sourcing.** The shunt resistor and the filter capacitor are both deliberately loose
values, which is why an Extended-part problem at assembly cost nothing: 390 Ω → 470 Ω and
3.9 nF → 2.2 nF, both improving the numbers slightly. The one part on the board where no
such substitution exists is the buck-boost feedback divider's high-side resistor — see
BU-P1.

**One consequence of the analog rail moving to the battery, checked 2026-09-24.** The output
is ground-centred by the negative charge pump, whose rail tracks the charge-pump supply —
now the analog rail, which follows the cell down below about 3.39 V. Full scale is
±2.97 V peak, characterised at a 3.3 V supply, so the maximum output falls roughly in
proportion: about 2.04 Vrms at a 3.2 V rail and 1.94 Vrms at 3.05 V, an **8 % loss of
maximum output at the very bottom of the discharge**. Inaudible in practice — the pad takes
12.5 dB off after it and a bass signal does not sit at full scale — but it is the concrete
mechanism behind "reduced headroom" at end of charge, and it is worth knowing it is a
*graceful* reduction rather than a cliff.

**The centre point does not move with it.** Ground-centring comes from the internal
reference, not from the supply rails, so a sagging rail shrinks the available swing
symmetrically and puts no DC offset on the jack. No coupling capacitor becomes necessary.

---

## 8. Radio — deferred

Not on the critical path; parked by decision. Two items are layout-time and cannot be
revisited after fab.

**Pending**

- [ ] **Check the module footprint geometry against the manual's PCB-design drawing.**
      Same page as the antenna keep-out, so one read closes both.
- [ ] **Antenna keep-out** — check the as-drawn void against that drawing, particularly
      how far past the first pad row copper must be cleared. Irreversible after fab.
- [ ] **Add footprint filters to the module symbol** — it has none, so nothing can ever
      flag a wrong land pattern on this part.
- [ ] Confirm the module firmware supports hardware flow control; two MCU pins are
      committed on the assumption.
- [ ] Verify the data and flow-control pairs are crossed, **pin by pin against the module
      pin table** — the net names describe the MCU end, so a straight-through error is
      invisible in the netlist and shorts two drivers together.
- [ ] Confirm the no-local-capacitor decision against the vendor's typical application
      circuit.
- [ ] RSSI check at the intended corner with the battery in place.

**Analysis**

The footprint is named for a different member of the module family, but it carries LCSC
part C518912, which **is** the specified module. That name is the converter library's own
naming — it draws one land pattern per family — so this is not evidence of a wrong part
selection. It is still unverified geometry, because "same family" is not "same land
pattern."

---

## 9. Fab and assembly

### FA-F1 — Symbol and land pattern disagree
*Gate: pre-fab*

**Pending**

- [ ] **MCU exposed pad** reads 6.4 × 6.4 — verify against DS13311.
- [ ] Spot-check the DAC's TSSOP-20, the crystal, and the SOT-23 parts.
- [ ] Add the library prefix to the Footprint property of the merged library's codec and
      buck-boost symbols. Latent, not live: the schematic instances are already qualified,
      so this bites on the next placement.
- [ ] Unregister and delete the superseded codec symbol library.

**Analysis**

The check that catches this cheaply: **the package code appears in the orderable part
number**, and vendor footprints are named after it. Where a stock footprint is
substituted the code is absent by construction, and four numbers are the only common
language — pin count, body, pitch, and **exposed pad**, which is the discriminator and
the one dimension that lives on a separate datasheet page.

Buck-boost and both codecs are now verified against their TI drawings and corrected.

### FA-F2 — Polarized part placed backwards or on the wrong land
*Gate: pre-fab*

**Pending**

- [ ] **Move the reference filter capacitor off the 1.0 mm EIA-3216 case onto the 1.8 mm
      case** — the mainstream part, pads the same within 40 µm, no routing change. The
      low-profile case is a specialty part with a thin catalogue; this is the same item
      the preamp test board hit.
- [ ] Check tantalum rotation in the plugin's rotation manager before ordering. The fab's
      position-file convention frequently sits 180° from the design tool's, and this is
      the one part where backwards destroys something.

### FA-F3 — Fine-pitch assembly and exposed pads
*Gate: pre-fab*

**Pending**

- [ ] Review paste aperture and voiding under the thermal pads, and thermal via stitching,
      for the 0.4 mm MCU and the leadless codecs and converter.

### FA-F4 — Parts not available at order time
*Gate: pre-fab*

**Pending**

- [ ] Re-confirm stock for the MCU (low stock, small quantity secured), codecs, DAC and
      module.
- [ ] Confirm the converter's reel part number — it differs from the sample number by a
      single leading character, which corrupts a lookup silently.

### FA-F5 — Bill of materials and position file disagree
*Gate: pre-fab*

**Pending**

- [ ] **Add per-part distributor numbers to the schematic** — there are none, so nothing
      in the BOM can be matched on.
- [ ] **Put full orderable part numbers in the Value fields.** The DAC's reads `PCM5102`
      with no package suffix.
- [ ] Exclude hand-fitted parts (pots, connectors, headers) consistently from both files.
- [ ] Keep simulation-only parts out of the export.

---

## 10. Performance

All gated behind G7. Listed so bring-up reserves time rather than declaring victory when
the first samples arrive.

**Pending**

- [ ] Switcher coupling into the analog section — two switching loops, instrument-level
      signals, and a light-load mode producing bursty rather than continuous ripple.
- [ ] Noise floor. The converter's input-referred noise is the system limit at this signal
      level, and the figure the design leans on was read off an axis range rather than a
      specified number.
- [ ] Crosstalk between the eight channels.
- [ ] **RF rectification from the radio into the front end.** The treatment was reasoned
      around a JFET gate junction and is unvalidated against the CMOS input that replaced
      it. The plan names this as the one result that could send the design back — and it
      is gated behind the entire capture path. Decide explicitly whether to buy an earlier
      answer with a bench rig.
- [ ] Battery life against the estimate that justified the MCU choice and the cell size.

---

## 11. Programmatic

**Pending**

- [ ] **No board-level recovery from the clock ceiling.** This package supports one core
      supply mode, capping the MCU at 400 MHz. The DSP headroom analysis and the
      pitch-detector burst rework are load-bearing; the exit is a respin to a larger
      package.
- [ ] **Hardware and firmware are debugged simultaneously**, with no known-good side.
      DAC-first ordering and logging from first power-up attack this; DX-D2 decides
      whether it is tractable.
- [ ] **Documentation divergence.** Check each document's cross-reference table before
      treating any analog section as current.
- [ ] **One respin is budgeted**, so the pre-fab items — FA-F1 through FA-F5, PG-A5,
      BU-A7 and the radio's two layout-time items — deserve more attention than their
      individual likelihoods suggest. They consume the respin rather than being fixed at
      the bench.
