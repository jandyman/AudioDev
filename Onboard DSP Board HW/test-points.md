# Test Points — Multichannel ADC/DAC Board

**Specifies** what gets physical probe access and why. Single source of truth — supersedes
the per-doc test-point lists in `pin-allocation.md`, `adc-netlist.md` and
`power-supply-netlist.md`. Signals are named by net; no reference designators, since
those move on re-annotation.

## Categorization scheme

Three categories, by *what kind of access the signal needs* — not by importance:

- **Category 1 — wire-loop pad.** Looked at often, or needs a mechanical connection. Wants
  a hole big enough to pass a wire through and solder a loop, for a semi-permanent monitor
  lead or a scope-clip ground.
- **Category 2 — probe pad / exposed via.** Unreachable otherwise, because the net runs
  between leadless packages. Occasional access; an exposed via is enough.
- **Category 3 — no dedicated access.** Reachable at an SMT passive, a connector pin, a
  probeable IC lead, or a castellated module pad. Recorded here so nothing is lost, but
  given no board area.

## Package reachability — the deciding factor

| Part | Package | Leads probeable? |
|---|---|---|
| MCU | VFQFPN68, 0.4 mm pitch, exposed pad | **No** — leadless |
| Audio ADC ×2 | WQFN-24 4×4 | **No** — leadless |
| DAC | TSSOP-20, 0.65 mm | **Yes** — gull-wing leads |
| Bluetooth module | castellated SMD | **Yes** — pads straddle the body edge, leaving a
  0.9 × 0.8 mm tab of exposed copper outside the module on every pin |

A net between the MCU and either codec is unreachable at both ends and needs a pad. A net
from the MCU to the DAC or to the radio module is reachable at the far end.

---

## Category 1 — wire-loop pads

| Signal | Status |
|---|---|
| **GND** ×3 — one in the analog region, one in the DAC-output region, and **one placed within ~5 mm of the digital bus clusters** rather than at a region centroid | **1.2 mm pad on a 0.7 mm drill**, untented. Sized to pass two bare strands of 30 AWG wire-wrap wire (0.255 mm each, 0.51 mm together) so a loop can be threaded and soldered for a scope-clip ground. Solid Kynar-insulated wire is specified because it holds the formed loop and the insulation does not shrink back when soldered near. The central one is deliberately pulled in tight: it serves the codec bus, the DAC bus, I²C and the clock point, all within 7 mm, which is short enough to use a ground spring rather than a clip lead when edge quality matters rather than just decoding. |
| **MCO1** — clock-tree and PLL health, checked at every bring-up | Placed. MCU pin is leadless so a dedicated pad is mandatory. 0.4 mm drill is adequate here; it is a probe-tip signal, not a clip point. |

*Optional promotions:* the digital and analog rails could be promoted from Category 3 to
permanent monitor loops. Low cost; not done.

---

## Category 2 — exposed vias (otherwise unreachable)

Implemented as **Ø0.7 mm untented vias on a 0.4 mm drill**, against the board's Ø0.6 /
0.3 mm routing via. That size-and-tenting difference is what identifies a test point at
the bench — there are eight of them and two hundred routing vias.

| Signal | Runs | Status |
|---|---|---|
| Codec bit clock | MCU → both codecs | Placed |
| Codec frame sync | MCU → both codecs | Placed |
| Codec serial data | both codecs → MCU (shared bus) | Placed |
| DAC bit clock | MCU → DAC | Placed |
| DAC word select | MCU → DAC | Placed |
| DAC serial data | MCU → DAC | Placed |
| I²C clock | MCU → both codecs | Placed |
| I²C data | MCU → both codecs | Placed |

The DAC-bus probeability question is closed by these vias being fitted — the TSSOP leads
are a fallback, not the plan.

⚠ **Spacing.** The three codec-bus vias sit on a diagonal at ~1.06 mm centres, leaving
0.36 mm of bare board between pad edges. The diagonal stagger helps, but TDM decode needs
bit clock, frame sync and data *simultaneously* plus a ground. Confirm three grabbers fit
with the probes actually owned; if there is room, spread them to ~2 mm.

⚠ **Ground proximity.** The nearest ground test point is 13–19 mm from each bus cluster.
Adequate for decoding an 8 MHz bus, where the probe's own ground lead dominates. Not
adequate for looking at edge quality — that wants a ground spring at the point.

---

## Firmware timing probes — decided 2026-09-24

**Two probes**, which is enough to mark two things at once — interrupt entry on one, block
or DMA boundary on the other.

| Probe | Access |
|---|---|
| **Spare MCU GPIO** (pad 60) | **Untented via** on a short stub, ~1 mm below the pad. Routing drill (0.6 / 0.3) because there is no room for a larger one here, so it is **probe-tip access, not solderable** — but it is still unambiguous at the bench: it is the only 0.6 mm via on the board with a tenting override, against a board default of tented both faces. Front untented, back left tented, since probe access is front-side only. Placed in layout only, carrying the auto-generated unconnected net, which is durable — updating the PCB from the schematic syncs footprints and pad nets and does not touch tracks or vias. It appears in neither the netlist nor the BOM, so this table is its only record. |
| **Status LED line** | **Untented 1.2 / 0.7 via** — an existing routing via on this net, enlarged in place rather than a new point added, so it costs no area. The larger drill makes it the probe that can carry a **soldered wire-wrap lead** for a long session; 0.7 mm takes two 30 AWG strands where one is enough. Electrically clean: the series resistor is on the LED's *cathode* side, so this net is the MCU output driving the anode directly — full logic swing, ~1.4 mA of load, no clamping. It also drives the LED, so blink activity appears in the trace; leave the LED idle while reading one. |

Additional pins brought out as surface pads were considered and dropped: at 0.4 mm pitch
they need to fan out before a probe tip will land, and the area was not worth it for a third
marker.

**Tenting and drill do two independent jobs, and it is worth keeping them separate.**

- **Untenting is what identifies a test point.** The board default is tented on both faces,
  so an exposed via is unmistakable among two hundred covered ones — at any drill size.
- **Drill is what decides whether a wire-wrap wire can be soldered in.** 0.4 mm takes one;
  0.3 mm does not.

So a cramped location still gets a useful test point: untent it at routing size and accept
probe-tip access. Only spend the larger drill where a soldered lead is actually wanted, and
tent the back face unless access is needed from both sides.

Both of these are **layout-only properties** — a via's size and tenting have no schematic
representation, so nothing is owed to the schematic when a routing via is promoted to a test
point. Where the net already exists, as on the LED line, promoting an existing via in place
costs no area at all. ⚠ Re-check clearance after enlarging one: going from 0.6 to 1.2 mm
doubles the annular radius. (Done for the LED via — nearest foreign copper is 0.53 mm clear.)

The MCU is leadless, so without these two there is no way to see firmware timing against the
audio buses at all.

## Category 3 — no dedicated access

| Signal | Where to touch it |
|---|---|
| Digital rail | the two 22 µF output capacitors |
| Analog rail | LDO output side; also both pickup connectors |
| MCU analog supply | its ferrite and local capacitors |
| Core supply | the core-decoupling capacitors at the MCU |
| Battery, pre- and post-switch | cell connector, bulk capacitor, converter input capacitors |
| Charge input | charger input capacitor, or the jack-ring pin |
| Battery sense | sense-divider midpoint |
| **Module UART ×4** (TX, RX, RTS, CTS) | **the module's castellated pad tabs** — 0.9 × 0.8 mm of exposed copper per pin outside the module body, at 1.27 mm pitch. Larger targets than the Category 2 vias. This satisfies the requirement in `bluetooth-constraints.md` §6 for probing the serial link independently of the BLE link. |
| Codec shutdown | its pull-down resistor |
| DAC soft-mute | DAC lead, or its routing vias. Static line — verify the startup transition once |
| **Bias reference** | both pickup connectors, and the divider and buffer pads. The node every channel's common mode rests on; measuring it on a cold pin is what closes the DC-coupled common-mode check in `adc-netlist.md` |
| DAC output, post-attenuator | L-pad resistors, volume pot, output jack |
| **Switch nodes** (both converters) | probe tip on the node, ground spring on the **adjacent capacitor's ground pad** a millimetre or two away. No ground test point is wanted here — the dedicated grounds are 10 mm and 19 mm off, and a cap ground pad is both closer and exposed copper by definition. |
| Codec master-clock reserve | reserve pad, DNP — populate only if a master clock is ever distributed |

---

## Open items

1. **Codec-bus via spacing** at ~1.06 mm — confirm three grabbers fit, against the probes
   in hand. Spread to ~2 mm if there is room.
2. **Test-point footprint naming.** Both variants mix two notations in one name — an inner
   diameter written in tenths without a decimal point, alongside an outer diameter in
   millimetres with one. Rename to the form `TestPoint_Loop_D0.7mm_Pad1.2mm`, which reads
   only one way.
