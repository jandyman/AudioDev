# DSP board audit — risk list

**This is the single to-do list for the main DSP board.** The open-items table below is
the current state; everything after it is supporting detail or history. Every audit or
fix edits the table in place: add rows, change status, and move closed items to the
closed log at the bottom with the date and how each was closed. No new dated findings
sections. Supporting analysis goes under the item it supports. When a finding
contradicts another document (bring-up register, pin allocation, power supply), that
document is updated in the same session or a row here says it is out of date.

Canonical copy: `Onboard DSP Board HW/documentation/dsp-board-audit-risk-list.md` in the
repo. The project copy is a mirror, overwritten from the repo file after each edit.

Scope: the main DSP board, plus the pickup-board interface where the two must agree;
the string preamp is handled separately. Items are named by function and value, never
by reference designator. The list exists to catch defects that **pass ERC and DRC**.

---

## Open items

Blocking = must be closed before the order is paid for. IDs are stable; gaps are
closed items (see the log). IDs read AUD-n (audit item n); until 2026-11-12 they were
written R-n, which looked like resistor designators.

| ID | Item | Blocking | Status | To close |
|---|---|---|---|---|
| AUD-15 | Order-time placement check: every polarised or asymmetric part verified in JLCPCB's 3D preview (the layout has no polarity or pin-1 silkscreen, and rotation depends on how LCSC stores each part) | **Yes** | Open — at order time | Walk the [preview checklist](#jlcpcb-preview-checklist), fixing rotations and regenerating as many times as needed |
| AUD-26 | Buck-boost input capacitor is not at the power-input pins: the 10 µF reaches them through ≈12 mm of 0.25–0.35 mm trace and two vias, the 0.1 µF through ≈7 mm. `power-supply-netlist.md` specifies "10 µF to GND (at pin)" | No (strongly recommended; cheap while AUD-12 is being rerouted) | Open — found 2026-11-11 | Put a 10 µF directly at the power-input pins with its ground end at the converter's exposed pad; keep the existing one as bulk. [Detail](#aud-26--buck-boost-input-capacitor) |
| AUD-27 | Battery reading flat-lines below a cell voltage of ≈3.39 V: the ADC reference is the analog rail, which follows the cell once its LDO is in dropout, so sense ÷ reference stays ≈0.506 from 3.39 V down to 3.0 V | No (firmware; no board change) | Open — found 2026-11-11; added to the bring-up register (cell and battery-sense entry) | Firmware reads the MCU's internal reference alongside the sense channel to compute the actual analog-rail voltage. Needed for any low-battery warning or cutoff (`power-supply.md` §2a: devices leave their recommended window near 3.24 V) |
| AUD-29 | Reference buffer amplifier has no supply bypass at its pin — nearest capacitor on the analog rail is ≈8 mm away | No | Open — found 2026-11-11 | 0.1 µF at the supply pin if there is room |
| AUD-30 | Part numbers against values only spot-checked (the LCSC catalogue was unreachable from the audit; two of 38 lines confirmed). Voltage ratings unverified — notably the 4.7 µF 0402 on the 5 V charge input, where a ceramic input capacitor can ring toward twice the supply when a live charger is plugged in | No — done at order (AUD-15) | Open | In JLCPCB's parts-matching screen read every line's description against value, package, dielectric and voltage. Prefer ≥10 V on the charge-input capacitor |
| AUD-31 | MCU core-SMPS input decoupling is slightly outside the coverage rule in `layout-notes.md` §5.1: 100 nF at 3.0 mm (rule ≈2 mm), 4.7 µF at 6.0 mm (rule ≈5 mm) | No | Open — found 2026-11-11 | Move the pair closer if the AUD-12 rerouting frees space; otherwise accept |
| AUD-32 | Serial-data pull-down (10 kΩ on the shared converter data line): `adc-netlist.md` §5 and `pin-allocation.md` §6 say populated; the board has it marked do-not-populate and it is absent from the assembly files | No | Open — found 2026-11-11; needs a decision | Either clear the do-not-populate flag and assign the part, or change both documents to "footprint only". The converters have an internal bus keeper, so either is workable |
| AUD-16 | Bluetooth module land pattern not yet overlaid on the datasheet's mechanical drawing | No (recommended) | Pin table and outline verified | Overlay pad by pad |
| AUD-17 | MCU exposed-pad size not verified against the package drawing | No (recommended) | Open | Compare land pattern to the VFQFPN68 drawing |
| AUD-8 | Control pots: analog rail on terminal 1, ground on terminal 3 — wiper voltage falls as the knob turns clockwise | No | Open, unchanged | Swap the end terminals, or record the inversion in firmware; confirm against the physical part first |
| AUD-11 | DAC internal-regulator decoupler is 2.2 µF; datasheet and design say 0.1 µF | No | Open, unchanged | Make the board match one of them on purpose |
| AUD-18 | Charger drawn with a stand-in symbol (different manufacturer); "update symbol from library" would silently revert pin names | No | Copper correct | Copy the symbol into a project library under the TP4054 name |
| AUD-19 | Library tables: footprint table uses absolute personal paths; all five symbol-table entries unused or broken (one in `~/Downloads`); the three custom symbol libraries in use resolve only through the global table; buck-boost and radio 3D models use absolute paths | No | Open | Project-local libraries with `${KIPRJMOD}` paths |
| AUD-20 | Housekeeping: two orphan sheets (designators collide with live parts) and two `.kicad_sch_old` copies in the project folder; stale `Gerbers/` folder; test-point footprint names encode the wrong drill/pad sizes; core-SMPS inductor footprint still named for the Sunlord part (Murata part fitted) | No | Open | Move orphans to `superseded/`; delete stale outputs; rename footprints |
| AUD-21 | Test points not yet classified by geometry; category-2 exposed vias not checked against `test-points.md` | No | Open | One pass against `test-points.md` |
| AUD-22 | No operating-point or AC simulation of the reference generator and output network (either would have caught AUD-1 in one run) | No | Open | Run both |
| AUD-23 | Crystal load: stray capacitance assumed ≈4.5 pF | No | Open | Settle against the routed layout |
| AUD-24 | DRC missing-courtyard check is still ignored | No | Open | Enable, or record why not |

---

## Detail

### AUD-12 — MCU core supply (closed)

**Resolved in the layout 2026-11-11.** One net now joins the inductor output, VFBSMPS,
the two output capacitors and all three VCAP pins with their 100 nF capacitors. Trace
length from the inductor output: ≈12 mm to the nearest VCAP pin, 27–30 mm to the other
two, 0.2 mm wide with four vias — about 70 mΩ on the long runs, a few millivolts at the
core's current. The new copper stays 1.2 mm from the crystal nets. Making room moved
parts of the debug, radio-UART, control-bus and supply routing; every net was re-traced
for continuity afterwards and no part moved. The paragraphs below record how the
problem was found and argued.

As built, the 2.2 µH inductor runs from VLXSMPS to a node that carries only VFBSMPS and
two 10 µF capacitors. The three VCAP pins are three separate nets, 100 nF each, with no
link to that node or to each other. The bring-up register (core-SMPS entry) records this
as intended, reading AN5419 Figure 2 as showing VCAP fed inside the die.

The text of AN5419 disagrees: §2.1.7, direct SMPS supply — *"The SMPS is directly
connected to the VCAP pin and provides the regulated supply to the Vcore."* Table 2
lists VFBSMPS only as *"SMPS feedback voltage sense"*, and for VCAP *"All VCAP connected
together"*, with any third VCAP pin *"connected to the other VCAP pins"*. The physics
agree: the inductor is off-die, so its current must enter the die somewhere, and a sense
pin is not a supply input. As built, it can only charge two capacitors.

*Where the earlier conclusion came from (corrected 2026-11-10):* "SMPS-only" is right —
ST's moderator states this package is "only SMPS or bypass", with no LDO path to Vcore,
so the 400 MHz ceiling and 100 nF per VCAP pin both stand. But SMPS-only means the
on-chip LDO cannot supply the core; it does not mean the SMPS output is wired to the core
inside the package. Corroboration: an ST community answer on direct SMPS — "VCAP has to
be connected to the output of the SMPS block" — and an open-source board on this exact
part and package (Team-Micras MicrasPCB) that puts VCAP1–3, VFBSMPS and the inductor on
one core net.

Consequence if the earlier reading is wrong: a board with no core supply and no debug
access.

*How package-specific the evidence is (2026-11-10):* weaker than first presented.
AN5419 covers the whole family and never mentions the VFQFPN68 (its direct-SMPS figure
is marked "only for LQFP/BGA"); the forum answer that VCAP goes to the SMPS output
concerns the dual-core family; the ST evaluation board is BGA and its schematic has not
been read. The only source on this exact package showing the wiring is an unproven
hobby design (MicrasPCB). The package does bond VDDLDO to VDD internally, so an
internal VFBSMPS-to-core bond — the premise of the bring-up register entry — cannot be
ruled out.

*Why the link is still the right call:* it is correct under both readings. If the
package bonds VFBSMPS to the core internally, an external link parallels it and is
harmless. If it does not, the link is the only thing that powers the core. Leaving it
out is correct under one reading only, and the failure is a dead board with no debug
access. There is no mode on this package in which VCAP should be anything but the SMPS
output (no LDO; bypass means an external supply). Cheap ways to buy certainty: a 0 Ω
link footprint in each connection so the choice becomes a bench decision, or an ST
community question on this package quoting AN5419 §2.1.7.

*Single-pin option (2026-11-11):* the three VCAP pins share the on-die core grid, so
feeding one pin would very likely power the core, and no bulk capacitance is needed at
VCAP (the 2.2 µF values are for the LDO, which this package lacks). The cost: the
internal join is on-die metal plus one bond wire per pin, and in SMPS mode the pins
carry the whole core supply (≈150 mA typical, more at worst case) — which is why AN5419
says "All VCAP connected together" for this mode. One pin may exceed ST's per-pin supply
current rating (typically ≈100 mA; not verified for these pins), and the far side of the
die runs lower by the grid drop — a marginal-at-speed fault, not a dead board.
Acceptable on a prototype because it is measurable and reworkable: under full load, the
voltage difference between the fed pin's capacitor and the other two VCAP capacitors
is the on-die drop, and a bodge wire from the inductor node to those capacitors adds
the missing links. *Preferred:* nearest VCAP pin on a short solid trace, the other two
by any available route however thin (0.15 mm × 30 mm ≈ 0.1 Ω still shares current); if
no route exists, one pin plus the bring-up measurement.

*Specify:* one core-supply net joining VFBSMPS and all three VCAP pins; 100 nF at each
VCAP pin; 4.7–10 µF at VFBSMPS (settled 2026-11-12: 2 × 10 µF). Confirm against the STM32H735G-DK schematic before routing — the "take
it verbatim from a reference schematic" step `power-supply-netlist.md` asked for. The
VCAP pins sit on three sides of the package, so this is a routing job.

### AUD-25 — Capture converter regulator capacitors

Each converter has two on-chip regulators whose outputs need an external capacitor to
be stable: the 1.8 V analog regulator and the 1.5 V digital-core regulator. The design
documents specify 1 µF on each, with a ⚠ against the analog one that was never closed.
The datasheet's pin table gives no value. Its typical-application figure (text
extracted, not viewed) lists two 10 µF and one 0.1 µF among the capacitors around those
pins, and the evaluation board's parts list carries three 10 µF 0603 capacitors beside
1 µF and 0.1 µF parts — both consistent with 10 µF + 0.1 µF on each regulator output
and 1 µF on the reference. Not proven from here; the figure settles it at a glance.
An under-sized regulator output capacitor is a stability and noise risk on all eight
channels, and the fix is a value change on an existing land.

*Further evidence (2026-11-13):* a TI applications engineer reviewing a customer
schematic for the sibling ADC6140 (same family and pinout) wrote "AREG: please connect
a 10uF and 0.1uF cap to GND here", and in the same review called 1 µF + 100 nF on AVDD
"sufficient". On an ADC5140 schematic review the same engineer asked for "a bulk
capacitor (10uF)" on the regulator output. So the 10 µF belongs on the two regulator
outputs, not on the supply inputs — the supply inputs on this board (0.1 µF at AVDD
plus the shared 10 µF; 1 µF at IOVDD) already match. The analog-regulator value is
well supported, the digital-core one probable. *Specify:* 10 µF, 6.3 V, X5R, 0402 on
each regulator output of both converters (four parts); the parallel 0.1 µF would need
new lands and is not worth adding.

### AUD-26 — Buck-boost input capacitor

The converter's power-input pins are fed from the 10 µF through a 0.35 mm trace, a via,
a bottom-layer hop, a second via, past the 0.1 µF, then ≈7 mm of 0.25 mm trace around
the package. The switching current's input loop therefore runs ≈12 mm each way instead
of closing at the pins. Expected effect at this board's load (≈150 mA): it will run,
but with more ringing on the battery node than necessary — and the analog LDO takes its
input from that same node, with little rejection at the switching frequency. The area
beside the power-input pins is free of parts and of other nets, and the exposed pad has
six ground vias for the return.

### JLCPCB preview checklist

**The 3D preview is the only authority on rotation.** The correction the fab needs
depends on how LCSC stored each part's orientation, so it varies part by part, not just
package by package; a correction that was right on one board is a starting guess on the
next (`jlcpcb-submission-notes.md`). Expect several regenerate-and-check passes. Judge
by the pin-1 / polarity marker, not the outline. Fix rotations in the plugin's rotation
manager (not the CPL by hand), regenerate gerbers, BOM and CPL, run Check project with
no warnings, re-upload, and re-check the preview, until every part below is right.
**Run the design-rule check in KiCad after any layout change and before the first
upload** — the 2026-11-11 core-supply routing left several traces at exactly the
0.15 mm clearance, the tightest beside the core-SMPS inductor's switch-node pad.

- **Reference filter tantalum** — positive end toward the reference buffer's input.
- **Reference buffer, SC-70-5** — pin 1 (non-inverting input) toward the divider.
- **LDO and charger, SOT-23-5** — pin 1 against the footprint.
- **Battery connector, JST PH horizontal** — pin 1 is cell positive.
- **MCU, QFN-68; both converters, WQFN-24; buck-boost, VSON-14; DAC, TSSOP-20;
  Bluetooth module; crystal** — pin-1 mark against the footprint.
- **LED** — cathode mark.
- **Parts list** — in the parts-matching screen, every line's description against value,
  package, dielectric and voltage rating (AUD-30).

---

## Design decisions — not risks, do not raise

- Connector polarity and keying: unkeyed, colour-coded cable, single builder
  (`preamp-board.md` §10).
- Cable-entry protection and hot-plugging: none fitted; cables connected with the power
  off.
- Standalone operation of the pickup boards: that is what the test board is for.
- One-builder prototype, not a released product.
- No silkscreen polarity or pin-1 marks — no room; polarity is checked in the preview.
- **BOM and position-file exclusions are managed in the JLCPCB tool, not the
  schematic** (2026-11-07). `AudioDev/kicad-tools` copies them into the schematic before
  each Update PCB from Schematic (Sync) and checks the output (Check project); LCSC
  numbers live only in the JLCPCB tool. The audit checks the tool's **generated BOM and
  CPL**: every BOM row carries an LCSC number, nothing hand-fitted is in either file, and
  the two files list the same parts.
- Battery connector pin 1 is cell positive, pin 2 ground (corrected after the string
  preamp test board came back reversed; recorded in `power-supply-netlist.md`).
- Pickup interface, seven-way, straight-through: pin 1 ground, pin 2 reference, pin 3
  analog rail, pins 4–7 the four channel outputs, identical on both pickup boards.
  Header pin 4 lands on converter input 4 and pin 7 on input 1 — a firmware mapping.
- Pickup header names: "Pickup 1" is the converter at 0x4E, "Pickup 2" at 0x4D.

---

## Verified state (reference)

### Family 1 — symbol and land pattern agree

KiCad connects a symbol to a footprint by literal string match on the pin/pad number.
Nothing validates that pin 2 and pad 2 mean the same thing.

| Part | Status |
|---|---|
| Buck-boost, VSON-14 | ✓ Vendor land pattern; pins against SLVS916I: control and power inputs and enable on the switched battery, power-save pin low (power-save enabled), power-good to ground (open-drain, allowed unused), exposed pad to ground. Feedback 3.25 V |
| Audio ADC ×2, WQFN-24 | ✓ Vendor land pattern; pin table re-checked 2026-11-08; address straps decode to 0x4E and 0x4D |
| LDO, SOT-23-5 | ✓ Stock symbol for this package code; input and enable on the switched battery, output on the analog rail |
| Reference buffer, SC-70-5 | ✓ DCK numbering: 1 non-inverting input on the divider tap, 2 ground, 3 and 4 tied (follower) on the reference, 5 analog rail. Rotation: preview (AUD-15) |
| Audio DAC, TSSOP-20 | ✓ Mode straps (de-emphasis off, normal filter, internal PLL, I2S) all low |
| Bluetooth module | ✓ Pin table, all 24 pins; 1.27 mm pitch and 11.5 × 16 mm outline. MOD to the digital rail, WKP to ground; UART crossed (module receive to MCU transmit, module RTS to MCU CTS). Overlay: AUD-16 |
| Charger, SOT-23-5 | ✓ Copper against the TP4054 table. Symbol: AUD-18. PROG 3.3 kΩ ≈ 300 mA (0.25 C on the planned 1200 mAh cell); ≈0.6 W worst case, thermal foldback acceptable |
| Crystal, 4-pad | ✓ NDK 1612 (CL 8 pF) on the stock 1612 land pattern, an acceptable drop-in per `pin-allocation.md`. Diagonal pads 1/3 crystal, 2/4 ground |
| MCU, QFN-68 | Exposed pad to ground (required). Pad size: AUD-17. Core supply: AUD-12 |
| Potentiometers | Volume pot: hot end on terminal 3, switch on the battery line — clockwise-up. Control pots: AUD-8 |
| LED | Cathode to ground through 1 kΩ, anode from the MCU — 1.3 mA |

### Family 2 — every ratio and corner, computed

Where behaviour depends on *which* part sits on *which* side of a node, or on a value
nobody computed, both versions are electrically legal and no automated check can tell
them apart. **The rule:** for every node whose value is set by placement or by value,
compute the number — divider ratios, **RC corners**, gain, current set points, strap
codes, the polarity of every two-terminal connector, and every supply's path from
regulator to load (added 2026-11-08, AUD-12).

| Node | Design | Computed | Status |
|---|---|---|---|
| Buck-boost feedback | 1.1 MΩ high side, 200 kΩ low side, 0.5 V reference | 3.25 V | ✓ |
| Battery sense | 1 MΩ / 1 MΩ on the switched node | 2.10 V at 4.2 V | ✓ (separate 1 MΩ bleed documented) |
| Reference divider | 100 kΩ / 68 kΩ on the analog rail, 10 µF tantalum | 1.336 V; 40.5 kΩ source; τ = 0.40 s | ✓ |
| Output L-pad | 1.2 kΩ / 470 Ω into 10 kΩ pot | 0.272 → 0.572 Vrms; 327 Ω node | ✓ |
| Output filter corner | 2.2 nF C0G | 221 kHz | ✓ |
| Crystal load | 6.8 pF each, CL 8 pF | 3.4 pF + ~4.5 pF stray ≈ 7.9 pF | AUD-23 |
| Charger current | 3.3 kΩ PROG | ≈ 300 mA | ✓ |
| Converter addresses | strap pins | 0x4D, 0x4E | ✓ distinct |
| Battery polarity | pin 1 positive, pin 2 ground | matches harness | ✓ |
| MCU core supply | inductor → VFBSMPS → VCAP | no path to VCAP | ✗ AUD-12 |

### Family 3 — stale paths and names

A path or a value-encoding name written into a file survives the thing it points at.
Done: `placement_register.py` paths relative; inner copper layer renamed "3V3D"; stale
`adc-netlist.md` §2.1 paragraph corrected; ERC and DRC footprint-filter checks enabled.
Open: AUD-19, AUD-20, AUD-24.

---

## Standing method

For each part: symbol pin table, footprint pad list and the datasheet's pin-function
**table**, side by side; pin 1 location checked independently of numbering. Then the
Family 2 pass — compute every value set by placement. Then the Family 3 pass — resolve
every path and every encoded name. Then diff the netlist pad by pad against the last
committed version and the last audited version, because changes made after an audit are
exactly what the audit has not seen. Run Check project first.

**Vendor footprints** carry the package code in their name, so verifying one is a
string comparison; substituting a stock footprint means checking pin count, body, pitch
and exposed pad by hand. Library-generator footprints arrive without 3D models — point
them at a stock model of the same body.

---

## Closed log

| ID | Item | Closed | How |
|---|---|---|---|
| AUD-1 | Output filter capacitor was 2.2 µF (corner 221 Hz, −13 dB at 1 kHz) instead of 2.2 nF | 2026-11-06 | 2.2 nF C0G 0603, LCSC C33353. The original audit computed the attenuator ratio but never the RC corner; the rule now names RC corners explicitly |
| AUD-2 | Battery connector pin order changed after the last commit | 2026-11-06 | Intentional (test board came back reversed); pin 1 cell positive, recorded in `power-supply-netlist.md`; copper checked |
| AUD-3 | Reference filter capacitor had no tantalum part | 2026-11-07 | Kyocera AVX TAJA106K016RNJ, 10 µF 16 V, EIA 3216-A, LCSC C7171, on `CP_EIA-3216-18_Kemet-A`; positive on the divider tap. Fallback 0805 TAJP106M010RNJ, LCSC C1952866. Reason: microphonic path through the shared reference node |
| AUD-5 | Bluetooth module MOD and WKP floating (self-latching inputs) | 2026-11-06 | MOD to the digital rail (transparent mode), WKP to ground |
| AUD-6 | Through-hole parts in the BOM and position file | 2026-11-07 | Excluded in the JLCPCB tool; only the battery connector remains (intended). 85 parts after the AUD-4 resistors |
| AUD-7 | Gerbers stale | 2026-11-06 | Regenerated by the plugin; zipped set deleted. Leftover `Gerbers/` folder moved to AUD-20; ongoing freshness is AUD-14 |
| AUD-9 | Pickup headers indistinguishable | 2026-11-06 | Named "Pickup 1" (0x4E) and "Pickup 2" (0x4D) |
| AUD-10 | Converter address straps undocumented | 2026-11-06 | `adc-netlist.md` §6 records 0x4D and 0x4E |
| AUD-4 | DC-coupled differential input: converter's DC common-mode acceptance near mid-rail unproven | 2026-11-10 | Not a pre-order item. Committed on spin 1 as an accepted risk (`dc-coupling-conversion.md` decision 4); no retrofit footprints; 100 Ω cable-branch isolation resistors fitted. Measured on spin 1 at bring-up (bring-up register PG-A5); fallback is grounding the cold pins and lowering the reference to ≈0.7 V by rework. Analysis, gain plan and fallback: `adc-netlist.md` §2.1 |
| AUD-13 | Reference buffer rotation in the CPL was the +180 the submission notes call wrong | 2026-11-10 | Merged into AUD-15 — rotation is checked part by part in the 3D preview, not predicted from a table |
| AUD-14 | JLCPCB output older than the saved board | 2026-11-10 | Merged into AUD-15 — regeneration is part of every preview pass |
| AUD-12 | MCU core supply: the SMPS output was not connected to the VCAP pins | 2026-11-12 | One net now joins the inductor output, VFBSMPS, the output capacitors and all three VCAP pins (routed 2026-11-11, checked from the saved files: continuous, no other netlist change, schematic and board agree). Output capacitance settled at 2 × 10 µF, matching the reference designs found on the ST forum; design documents updated. Electrical-rule check not run, by decision — the only expected complaint is the VCAP pins' power-output pin type. Design-rule check moved to the order checklist. ST community question still open, informational only. [Detail](#aud-12--mcu-core-supply-closed) |
| AUD-25 | Capture converters' on-chip regulator outputs had 1 µF; TI guidance is 10 µF + 0.1 µF | 2026-11-13 | All four capacitors changed to 10 µF 6.3 V X5R 0402 (LCSC C15525), verified on the saved board and in the JLCPCB tool's database. Parallel 0.1 µF judged unnecessary beside a same-size 10 µF ceramic. `adc-netlist.md` and `decoupling-checklist.md` updated. [Detail](#aud-25--capture-converter-regulator-capacitors) |
| AUD-33 | Schematic still carried LCSC numbers on 84 symbols (written in 2026-11-07, never stripped), four of them stale after the regulator-capacitor change | 2026-11-13 | All 86 LCSC fields removed from the two schematic sheets (backups beside them, `.bak-20261113-lcsc`); nothing else in the files changed, verified token by token. Check project now reports any LCSC number left in the schematic as an error, and names any that disagrees with the board. The four BOM-versus-board errors Check project still shows are the stale assembly files — cleared by regenerating (AUD-15) |
| AUD-28 | `pin-allocation.md` and `decoupling-checklist.md` out of date against the board | 2026-11-11 | `pin-allocation.md`: control pot 1 moved to PB0, status LED to PB10, radio UART rows added (PB13/PB14/PC10/PC11) and the "pins do not exist" note corrected, address straps as built, pull-up and strap values, reset-net and crystal-footprint items closed. `decoupling-checklist.md`: every status re-checked against the board with measured distances. The one disagreement that was not purely documentation became AUD-32 |

### Pass history

- 2026-08-20 opened; 2026-09-26 updated (commit `a2d4c95`).
- 2026-11-05 regression, follow-ups 2026-11-06/07: AUD-1–AUD-11.
- 2026-11-08 regression against commit `8de6dcb`, diffed pad by pad against
  `a2d4c95` and each 2026-11-07 commit: every change since 2026-09-26 was already
  recorded; found AUD-12, AUD-13.
- 2026-11-11 full re-audit of the saved board (unchanged since 2026-11-07): Check
  project; pad-level netlist; MCU pin functions against `pin-allocation.md`; every
  routed net traced for continuity (74 signal nets, both plane nets); supply-pin to
  capacitor distances; track and via sizes (0.2–0.5 mm, 0.6/0.3 mm vias); low-battery
  behaviour. Found AUD-25–AUD-30. AUD-12 single-pin/two-pin analysis added.
- 2026-11-13 AUD-25 closed (regulator capacitors to 10 µF); AUD-33 opened and closed
  (LCSC numbers stripped from the schematic; Check project extended).
- 2026-11-12 AUD-12 closed (output capacitance 2 × 10 µF; electrical-rule check waived).
  Item IDs renamed from R-n to AUD-n.
- 2026-11-11 AUD-12 routed (all three VCAP pins); routing checked from the saved files;
  bring-up register, pin allocation, power-supply documents and decoupling checklist
  updated to the new wiring.
- 2026-11-10 AUD-12 evidence re-checked (SMPS-only confirmed; an earlier claim that the LDO
  exists on this package withdrawn). List restructured into this form. AUD-4 moved to
  bring-up; AUD-13 and AUD-14 merged into AUD-15.
