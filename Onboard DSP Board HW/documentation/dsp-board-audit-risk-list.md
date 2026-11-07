# DSP board audit — risk list

Opened 2026-08-20. Updated 2026-09-26. **Regression pass 2026-11-05**, follow-up 2026-11-06, against the
schematic and layout as they stand (layout last saved 2026-10-10, with uncommitted
changes since the 2026-09-26 commit). Scope is the main DSP board, plus the pickup-board interface where
the two must agree; the string preamp itself is handled separately.

This list exists to catch defects that **pass ERC and DRC**. Items are named by
function and value, never by reference designator.

**Decided, not risks — do not raise in this list:** connector polarity and keying
(unkeyed, colour-coded cable, single builder — `preamp-board.md` §10); cable-entry
protection and hot-plugging (none fitted; cables connected with the power off);
standalone operation of the pickup boards (that is what the test board is for).
This is a one-builder prototype, not a released product. No silkscreen polarity or
pin-1 marks — the layout has no room; polarity is checked in the JLCPCB preview.

**BOM and position-file exclusions are managed in the JLCPCB tool, not the
schematic** (decided 2026-11-07). `AudioDev/kicad-tools` copies them into the schematic before each Update PCB from Schematic (Sync) and checks the output (Check project); LCSC numbers live only in the JLCPCB tool. The tool's toggles set footprint attributes, which a
schematic update or footprint refresh can reset, so the audit checks the tool's
**generated BOM and CPL** rather than schematic flags: every BOM row carries an LCSC
number, nothing hand-fitted is in either file, and the two files list the same parts.

**Family 1 — the symbol and the land pattern disagree.** KiCad connects a symbol to a
footprint by literal string match on the pin/pad number. Nothing validates that pin 2
and pad 2 mean the same thing.

**Family 2 — the topology or value is legal but wrong.** Where behaviour depends on
*which* part sits on *which* side of a node, or on a value nobody computed, both
versions are electrically legal and no automated check can tell them apart. The
buck-boost feedback divider was built transposed (0.585 V instead of the intended
rail) and survived a pin-by-pin datasheet review.

**Family 3 — stale paths and names.** A path or a value-encoding name written into a
file survives the thing it points at.

---

## Regression result, 2026-11-05

The regression turned up **four items that had to be settled before ordering**; as of 2026-11-06 three are closed and the fourth is an accepted risk under evaluation. One is
a genuine value error that predates the audit and was missed by it; one is a change
made since the last commit; two are places where the board and its design documents
have drifted apart on a decision that matters.

### Blocking before order — status 2026-11-06

**R1 — Output filter capacitor was 2.2 µF; design calls for 2.2 nF.** **Fixed
2026-11-06.** As built it put the output corner at 221 Hz (−13 dB at 1 kHz) instead
of 221 kHz. The original audit computed the attenuator's ratio and stopped; the
"generalise to RC corners" half of the rule had never been run. It now has been,
board-wide (Family 2 table). *Checked 2026-11-06:* 2.2 nF, 0603, LCSC C33353, C0G
confirmed.

**R2 — Battery connector pin order changed after the last commit.** **Intentional,
confirmed 2026-11-06:** corrected after the string preamp test board came back from
assembly with the battery reversed. Pin assignment now written into
`power-supply-netlist.md` (pin 1 cell positive, pin 2 ground). Copper checked
2026-11-06. No silkscreen mark — no room; accepted.

**R3 — Reference filter capacitor had no tantalum part.** **Fixed 2026-11-06.**
*Checked:* polarised symbol, LCSC C7171, positive pad on the divider tap — correct.
**Fixed 2026-11-07:** footprint
`CP_EIA-3216-18_Kemet-A` to match C7171, on board and schematic, part number in both. No silkscreen polarity mark — by design, the
layout has no room for silkscreen; polarity is verified in the JLCPCB preview instead
(list below).
Preferred part: Kyocera AVX TAJA106K016RNJ, 10 µF 16 V, EIA 3216 case A, LCSC C7171
(JLCPCB Basic); 0805 fallback TAJP106M010RNJ, LCSC C1952866. Positive terminal toward
the divider tap. Rationale: the piezoelectric (microphonic) path through a shared
reference node. Note that in the DC-coupled scheme, vibration picked up on this node
arrives largely as common-mode, so the stakes are lower than on the pickup boards;
it still matters if the input is ever reverted.

**R4 — DC-coupled differential input: risk accepted, buffer isolation added.**
*Decision 2026-11-06:* proceed on the assumption that the converter supports DC
coupling with both pins near mid-rail. **No retrofit footprints** — the per-channel
series parts, cold-pin capacitors and straps (about 20 × 0402 around the converters)
cost more layout than the risk justifies. Instead, evaluate open check 1 more closely
before ordering (below).

*Fitted 2026-11-07* (100 Ω 0402, LCSC C25076, checked in the JLCPCB output): a series resistor between the reference buffer and each pickup header's
reference pin — **in the cable branch only**, not in the path to the converter cold
pins. It isolates the buffer from 100–200 pF of cable, and it is free because the
conductor carries no signal current. In series with the cold pins it would unbalance
hot against cold and cost rejection. **100 Ω, 0402, tolerance unimportant** (decided
2026-11-07), placed at the buffer output where the reference splits; a pole near
8 MHz with the cable.

*Evidence so far for open check 1:* the converter datasheet supports DC-coupled
inputs (per-channel register bit), recommends the pins stay between 0 V and the
analog supply, and draws DC coupling only with the cold pin grounded; it gives no
DC common-mode window and specifies input impedance as AC only. The nearest TI
material, SBAA499A, covers the newer two-channel x120 parts, not this one: in their
default mode they list a DC-coupled tolerance of 2.82 Vpp, and full 0-to-supply common
mode only in a high-rejection mode at 10 k/20 k input impedance. This converter has no
such mode register. Plausible, not proven.

*To close it:* bench test on an evaluation module — both pins of one channel at
1.34 V, DC-coupled, 10 kΩ input impedance (the planned setting); measure offset, clip level, THD. Or a TI
E2E question asking for the DC common-mode window of this specific part.

*Fallback, if it fails on the bench:* DC coupling with the cold pins **grounded**
(the configuration the datasheet draws) and the reference lowered to about 0.7 V, so
the signal sits in the positive half of the converter's range. Costs about 6 dB of
converter range and the common-mode rejection; the offset is removed by the digital
high-pass filter. Without footprints this means cutting the cold-pin node free of the
reference and tying it to ground — a rework, not a respin. Converter gain stays at
0 dB in that fallback, since it would multiply the offset.

*Gain plan (corrected 2026-11-06):* plan against the single-ended full scale — only
the hot pin swings, inside the 0 V to supply pin range — giving ≈19 dB of headroom
at 0 dB gain. Gain is not needed for level; it buys up to ≈2 dB of noise, because
the converter's input noise at 0 dB gain (≈8.9 µV A-weighted) roughly equals the
preamp's. Gain costs no headroom up to 6 dB (the hot pin's swing is the limit until then); 9 dB leaves ≈16 dB, 12 dB ≈13 dB. Start at ≈9–12 dB, set from the measured pick attack. `adc-netlist.md` §2.1
updated to match.

*Residual risks on the input path, with the series resistors in:*

1. **DC common-mode acceptance (open check 1)** — the only one that touches all
   eight channels at once. Close before ordering.
2. **Full scale under DC coupling** — both full-scale figures are specified
   AC-coupled only. Same bench test.
3. ~~Buffer driving the eight cold pins directly~~ — **closed 2026-11-07.** The
   pins feed a continuous-time gain stage through ≈10 kΩ, so the buffer sees a
   resistive load carrying near-constant current, not the modulator's sampling
   kickback. No signal current on the shared node, so no crosstalk path.

### Fix before order — lower stakes

**R5 — Bluetooth module mode and wake pins were left floating.** **Fixed 2026-11-06:** MOD to the digital rail, WKP to ground. The module datasheet
describes MOD and WKP as self-latching inputs that must be tied or driven. MOD selects
configuration mode (low) or transparent mode (high) once a link is up; WKP wakes on a
falling edge and sleeps on a rising one. Floating, the module's state after a
connection is undefined. *Specify:* MOD to the digital rail (or an MCU pin if firmware
needs AT configuration after pairing), WKP to ground (or an MCU pin). Reset can stay
open. The UART is crossed correctly — module receive to MCU transmit, module RTS to
MCU CTS and vice versa.

**R6 — Through-hole parts in the BOM and position file.** **Fixed 2026-11-07,
checked on the JLCPCB output:** 83 parts, every BOM row has an LCSC number, BOM and CPL
list the same parts, the only through-hole part in either is the battery connector
(intended). Schematic and board agree on all 95 parts' values, footprints and LCSC
numbers.

**R7 — Gerbers were stale.** **Fixed 2026-11-06:** the plugin's set is regenerated from the current layout. `Gerbers.zip` deleted 2026-11-07; the old `Gerbers/` folder (with the stale layer name) is still there. The plotted set predates the last layout save by sixteen
days and the battery connector change. Regenerate from the final layout; do not reuse
the zipped set.

**R8 — Control pot sense is reversed.** Both control pots have the analog rail on
terminal 1 and ground on terminal 3. With standard terminal numbering the wiper voltage
**falls** as the knob turns clockwise. Either swap the end terminals or record the
inversion in firmware. Confirm against the physical part before deciding.

**R9 — Name the pickup headers.** **Fixed 2026-11-06:** "Pickup 1" (converter at 0x4E) and "Pickup 2" (0x4D). Both carry the value "Bridge Pickup". One is the
neck. Without that, the mapping from converter address to pickup cannot be stated
(R10).

**R10 — Converter address straps.** **Closed 2026-11-06:** `adc-netlist.md` §6 now
records the straps as built — 0x4D and 0x4E. Firmware probes those two.

**R11 — DAC internal-regulator decoupler is 2.2 µF; datasheet and design say 0.1 µF.**
Low risk, but the board should match one of them on purpose.

### JLCPCB verification list — at the placement preview, before payment

The layout carries no silkscreen polarity or pin-1 marks, so the fab's 3D preview is
the only polarity check. Judge by the pin-1 / polarity marker, not the outline.

- **Reference filter tantalum** — positive end toward the reference buffer's input.
  Submission notes: the plugin database shipped +180 for EIA-3216 tantalum; correct
  is 0.
- **Reference buffer, SC-70-5** — database shipped +180 for SOT-353, which lands 90°
  out.
- **Both SOT-23-5 parts** (LDO, charger) — −90 was correct on the test board.
- **Battery connector, JST PH horizontal** — +180 was correct on the test board; pin 1
  is cell positive.
- **MCU, QFN-68; both converters, WQFN-24; buck-boost, VSON-14; DAC, TSSOP-20;
  Bluetooth module; crystal; LED** — first time through the preview for these
  packages. Check each pin-1 mark against the footprint.

### Interface with the pickup boards

The seven-way connection agrees end to end: pin 1 ground, pin 2 reference, pin 3
analog rail, pins 4–7 the four channel outputs, identical on both pickup boards. Straight-through cable.

---

## Family 1 — status

| Part | Status |
|---|---|
| Buck-boost, VSON-14 | **Verified** — vendor land pattern; pins against SLVS916I pin table: control and power inputs and enable on the switched battery, power-save pin low (power-save enabled), power-good tied to ground (open-drain, datasheet allows it unused), exposed pad to ground |
| Audio ADC ×2, WQFN-24 | **Verified** — vendor land pattern, pin table unchanged |
| LDO, SOT-23-5 | **Closed** — stock symbol drawn for this exact package code; input and enable on the switched battery, output on the analog rail |
| Reference buffer | **Changed part, verified.** The dual SOT-23-8 amplifier is gone; the buffer is now a single amplifier in SC-70-5. Against the DCK numbering: 1 non-inverting input on the divider tap, 2 ground, 3 and 4 tied (follower) on the reference, 5 analog rail |
| Audio DAC, TSSOP-20 | **Verified** — unchanged |
| Bluetooth module | **Narrowed.** Pin table in the symbol matches the module datasheet's pin definition, all 24 pins. Pitch 1.27 mm and the 11.5 × 16 mm outline match the family land pattern in use. **Remaining:** overlay the datasheet's mechanical drawing on the land pattern pad by pad. Plus R5 |
| Charger, SOT-23-5 | **Copper correct, symbol still wrong.** Stock symbol for a different manufacturer's part; its pin 1 carries the TP4054's name in the schematic's embedded copy but the stock part's name in the library, so "update symbol from library" would silently revert it. Copy into a project library under the right name. PROG is 3.3 kΩ ≈ 300 mA (0.25 C on the planned 1200 mAh cell); `power-supply-netlist.md` updated to match. Dissipation ≈ 0.6 W at a deeply discharged cell; the part thermally folds back, which is acceptable |
| Crystal, 4-pad | **Closed.** Ordered part is the NDK 1612 (CL 8 pF); placed on the stock 1612 land pattern rather than the project's NDK footprint, which `pin-allocation.md` names as an acceptable drop-in. Pads 0.75 × 0.60 mm on 1.05 × 0.80 mm centres against NDK's 0.75 × 0.65 on 1.05 × 0.75. Diagonal pads 1/3 carry the crystal, 2/4 ground. Doc item "load the NDK footprint" is superseded |
| MCU, QFN-68 | Exposed pad to ground (ST confirms this is required). **Exposed-pad size still unverified** against the package drawing |
| Potentiometers | Volume pot: hot end on terminal 3, switch on the battery line — correct for clockwise-up. Control pots: R8 |
| LED | Cathode to ground through 1 kΩ, anode from the MCU — 1.3 mA. Check the land pattern's cathode mark against the part at order |

## Family 2 — every ratio and corner, computed

| Node | Design | Computed | Status |
|---|---|---|---|
| Buck-boost feedback | 1.1 MΩ high side, 200 kΩ low side, 0.5 V reference | 3.25 V | ✓ orientation correct |
| Battery sense | 1 MΩ / 1 MΩ on the switched node | 2.10 V at 4.2 V | ✓ (separate 1 MΩ bleed is documented) |
| Reference divider | 100 kΩ / 68 kΩ on the analog rail | 1.336 V; 40.5 kΩ source; τ = 0.40 s | ✓ matches doc; capacitor is R3 |
| Output L-pad ratio | 1.2 kΩ / 470 Ω into 10 kΩ pot | 0.272 → 0.572 Vrms; 327 Ω node | ✓ |
| Output filter corner | 2.2 nF | 221 kHz (was 221 Hz before the fix) | ✓ fixed — R1 |
| Crystal load | 6.8 pF each, CL 8 pF | 3.4 pF + ~4.5 pF stray ≈ 7.9 pF | ✓ settle stray against routed layout |
| Charger current | 3.3 kΩ PROG | ≈ 300 mA | ✓ doc updated |
| Converter addresses | strap pins | 0x4D, 0x4E | ✓ distinct; doc updated |
| Battery polarity | pin 1 positive, pin 2 ground | matches harness per test-board correction | ✓ intentional — document it (R2) |

**The rule, restated so the gap cannot recur:** for every node whose value is set by
placement or by value, compute the number — divider ratios, **RC corners**, gain,
current set points, strap codes, and the polarity of every two-terminal connector.

## Family 3 — status

| Item | Status |
|---|---|
| `placement_register.py` paths | ✓ still relative |
| Project footprint table | **Improved, not done.** The vendor library is now declared and the KiCad 6 entry is gone — but both entries are absolute paths into a personal library tree. The project-local library holding the NDK crystal footprint is not declared (now unused) |
| Project symbol table | **All five entries are unused or broken** — one points into `~/Downloads`, one at a directory rather than a library file. The three custom libraries the schematic actually uses (vendor, the pot-with-switch library borrowed from the test board, and the radio module's) resolve only through the global table, if at all |
| 3D models | Buck-boost and radio module reference absolute paths |
| Inner copper layer named "3V45" | ✓ Renamed "3V3D" 2026-11-06 |
| Test-point footprint names | "ID7_OD1.2mm" is a 0.7 mm drill / 1.2 mm pad; "ID4_OD7.0mm" is 0.4 / 0.7. Names encode the wrong numbers |
| Orphan schematic files | Two sheets sit in the project folder outside the hierarchy, with designators that collide with live parts. Move to `superseded/` |
| `adc-netlist.md` §2.1 | ✓ Stale "no second buffer here" paragraph corrected 2026-11-06 |

## Board-wide checks

- ✓ ERC footprint-filter and DRC footprint-filter checks are now enabled (were ignored).
  Missing-courtyard is still ignored.
- ✓ Schematic and layout are in sync: same 95 parts, same values, same footprints.
- ✓ The only net change since the last commit is the battery connector (R2).
- Open: classify test points by geometry, and verify the category-2 exposed vias
  against `test-points.md` — not repeated in this pass.
- Open: operating point and AC sweep of the reference generator and output network.
  Either would have caught R1 in one run.

---

## Standing method

For each part: symbol pin table, footprint pad list and the datasheet's pin-function
**table**, side by side; pin 1 location checked independently of numbering. Then the
Family 2 pass — compute every value set by placement. Then the Family 3 pass — resolve
every path and every encoded name. Then diff the netlist against the last committed
version, because changes made after an audit are exactly what the audit has not seen.

**Vendor footprints** carry the package code in their name, so verifying one is a
string comparison; substituting a stock footprint means checking pin count, body,
pitch and exposed pad by hand. Library-generator footprints arrive without 3D models —
point them at a stock model of the same body.
