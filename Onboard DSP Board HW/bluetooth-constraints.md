# Bluetooth — Requirements and Design

**Status:** **Ebyte E104-BT5032A**, integrated ceramic antenna, at the board's
far corner (the end away from the analog front end). Selected and placed.

Companion to `layout-notes.md` (the canonical layout doc) and
`placement-register.md` (generated placement/clearance facts). Distances quoted
here are stated as *requirements*; the register carries the measured values and
is the thing to re-read after any placement change.

---

## 1. Requirements

### 1.1 Hard constraints

- **Board outline ≤ ~30 × 90 mm**, no overhangs.
- **Fixed-profile module** — must ship with working UART/AT firmware. Sole reason:
  no board room for a debug/programming connector, so radio firmware cannot be
  flashed in place.
- **JLC must stock and place the part.** No consigned parts. (JLC global sourcing —
  pre-order with lead time — is acceptable if needed.)
- **No conventional screw-on external antenna.** An adhesive FPC antenna on a u.FL
  pigtail is acceptable.
- **No perpendicular mezzanine.** Parallel (stacked) mezzanine is acceptable.
- **Corner space available: ~11.5 × 16 mm.** Not much more — this is what sets the
  module size ceiling, and the selected part uses essentially all of it.
- Module lives in the instrument's control cavity alongside the main board.
- Single-sided assembly is the plan of record (`layout-notes.md` §1.1).

### 1.2 Environment and link requirements

- **Control cavity is unshielded.** No foil, paint, or foil-backed cover.
- **Required range: ~10 ft (3 m).**
- Cavity metal: the battery pack, pot bodies, output jack, bridge/string ground
  wire. The pack is off-board on a flying lead, so its position is set by the
  cavity, not by the layout — but the on-board battery connector and the lead
  leaving it are the nearest metal to the antenna end and are governed by §4.
- Volume and tone pots use **plastic cases**, so they are a dielectric load near
  the module rather than a conductive one.

### 1.3 Not constraints

- **Power budget.** BLE draws ~5–13 mA transmitting, well under 1 mA averaged,
  against the board's ~140 mA.
- **Pin count.** A full USART3 set with flow control is free on the STM32.
- **Module sleep current.** Invisible next to the H7.
- **Footprint, pad pitch, hand-solderability.** JLC assembles.
- **External 32.768 kHz crystal.** These modules are clock-complete.

## 2. Selected part — Ebyte E104-BT5032A

| Attribute | Value |
|---|---|
| LCSC/JLC # | C518912 — in stock (181 @ $5.72, 2026-07-30) |
| Size | 11.5 × 16 mm, castellated SMD, 24 pads on three sides |
| Radio | nRF52832, BLE 5.0, master or slave |
| Interface | AT / transparent UART (Ebyte fixed-profile firmware) |
| TX / RX | 4 dBm / −96 dBm |
| Antenna | ceramic chip at the pad-free end, 50 Ω, rated 60 m (see §3 conditions) |
| Supply | **1.7–3.6 V; ≥3.3 V for full output power** — the 3.45 V rail is in range |
| Logic | 3.3 V-class UART (5 V unsafe) — same-rail with the STM32 |
| Assembly | JLC SMT, MSL 3 |
| Certification | FCC modular grant (FCC ID 2ALPH-E104BT5032A); CE per vendor |

**Why this part:** in stock; supply range covers the rail at full power; strongest
rated antenna among stocked fixed-profile candidates; cheap; widely used (large
maker/industrial user base, active community).

**Known trade-offs (accepted for a personal build, re-examine for a product):**

- Ebyte AT-firmware documentation is thinner than Microchip-class and translated.
- Proprietary AT command set — keep a thin command-layer abstraction in firmware so
  a future vendor swap doesn't ripple.
- Faster model turnover than Microchip; availability horizon shorter.
- Community reports of difficulty *reflashing* the module are irrelevant here
  (fixed-profile use only) but confirm the stock firmware is protected.
- The footprint is generated from the LCSC/EasyEDA library so it matches JLC's
  placement data. Do **not** substitute a Raytac or other similar-outline
  footprint — pad count and pitch differ.

## 3. Antenna and metal — design rules

Two separate rules; do not merge them:

- **PCB copper keep-out** (integrated-antenna modules): copper-free on all layers
  under the antenna *end* plus margin. The module body wants solid ground under it —
  the keep-out is a small end-zone, not the whole module. Belongs at an extreme board
  corner, antenna edge on the board edge facing off-board, so no return path detours
  around the gap.
- **External-metal clearance**: enclosure-level vendor guidance, 10–30 mm depending
  on vendor, for best range. Not a cliff — degradation from nearby metal is graceful.

Margin picture: the part is rated 60 m (open area, 5 dBi far-end antenna at 2 m; a
phone link is less) against 3 m required — over 20 dB of margin, some of which the
cavity metal will consume. An RSSI walk-through with the Nordic dev board at the
intended corner, battery in place, is the cheap pre-layout check.

## 4. Placement and copper keep-out

**Requirements:**

- Module at the far corner, **antenna end on the board edge**, radiating off-board.
  The antenna end is the pad-free ~4 mm of the module's 16 mm length.
- **Copper cleared on every layer** across the antenna end, carried out to the two
  board edges it faces so the void has no copper island in it and no return path is
  forced to detour. Roughly 1 mm of margin beyond the module outline on the sides,
  and the keep-out boundary pulled no further past the first pad row than it has to
  be — the ground pads immediately behind it need a short path to the plane (§4.1).
- **Solid ground under the module body**, everywhere the keep-out does not apply.
- Nothing tall, conductive, or high-dV/dt in the antenna end's line of sight where
  the layout has any choice about it. The board is short on room, so the standing
  rule is: when something must be close, put it beside the module *body*, never off
  the antenna end.

**Deliberate concessions, given there is no room to do better:**

- The buck-boost inductor sits close to the module's long side. Accepted: the pins
  it faces are unused GPIO and status lines flanked by ground (§6), the converter's
  switching fundamental is ~2.4 MHz so there is no in-band mechanism at 2.4 GHz, and
  the inductor is shielded. Keep the switch node's copper short and pointed away from
  the module; that, not the inductor body, is the aggressor.
- The volume pot sits close to the module's opposite short side, at the far end from
  the antenna, and has a plastic case.
- The battery connector is the nearest metal to the antenna end. This is the one
  worth revisiting if any room ever appears in that corner.

### 4.1 Ground bonding

The module's three ground pads carry the RF ground into the host plane, which acts
as the antenna's counterpoise. **Via each ground pad into the plane as close to the
pad as the keep-out allows** — at the pad where there is copper beneath, and
immediately past the boundary for the pad that sits inside the cleared end-zone.
That puts two of the three within ~1.3 mm; the pad inside the keep-out is
necessarily longer, around 2 mm. A millimetre or two of 0.2 mm trace is ~1–2 nH
each, and three in parallel puts the aggregate well below anything the antenna will
notice — but there is no reason to spend it.

## 5. Supply

- **Module VCC on `3V45_D`**, the same digital rail as the STM32 and the codec
  digital supplies. At 3.45 V the module is inside its 1.7–3.6 V range and above the
  3.3 V needed for full output power.
- **No local decoupling capacitor at the module.** The corner has no room for one —
  the module is boxed in by the board edge, the pot, and the inductor — and it does
  not need one. The rail reaches the module as a ~22 mm run of 0.35 mm trace on the
  top layer over the ground plane below it: ~50 Ω microstrip, so ≈6.6 nH and ≈31 mΩ
  back to the 47 µF bulk at the converter output. Against a TX burst of 7.5–16 mA
  ramping over microseconds that is ~0.5 mV of IR drop and ~50 µV of L·di/dt.
  Everything fast —
  the PA envelope, the module's internal DC/DC — is handled by the module's own
  on-board decoupling millimetres from the die, which is what a certified module is
  for: its modular grant was obtained running from an arbitrary host supply.
  Confirm against the vendor's typical application circuit (§8) so the deviation is
  a recorded decision rather than an oversight.

## 6. Host interface

- **UART on USART3**, at 3.3 V-class logic on the shared rail — no level shifting.
- **Data pair crossed:** MCU TX → module RXD, module TXD → MCU RX.
- **Flow-control pair crossed the same way:** MCU RTS (an output) → module CTS (an
  input), module RTS (an output) → MCU CTS (an input). Straight-through wiring here
  shorts two drivers together and leaves two inputs floating — the net names describe
  the MCU end, so the crossover is invisible in the netlist unless checked pin by pin.
- **Pad-side routing discipline:** VCC and the UART are on the module's outer column,
  facing the board edge and away from the converter. The column facing the inductor
  carries only ground and unused GPIO/status pins. Preserve this if the corner is
  ever re-laid.
- **Test points on the UART lines** so the serial link can be debugged independently
  of the BLE link (see `test-points.md`).

## 7. Alternatives — recorded, open

**The candidate list is not exhaustive; nothing outside it is ruled out.** Other
fixed-profile families (u-blox NINA/ANNA, Infineon EZ-Serial, Ezurio BL65x, Telit,
Panasonic, ESP32-AT, other transparent-UART parts) may be surveyed if the selection
is reopened.

| Part | LCSC/JLC # | Size (mm) | Antenna | Supply | Stock 2026-07-30 |
|---|---|---|---|---|---|
| Microchip RN4871U-V/RM118 | C633444 | 6.0 × 8.0 | none — 50 Ω RF pad | 1.9–3.6 V | 28 ($9.41) |
| Microchip RN4871-V/RM118 | C633943 | 9.0 × 11.5 × 2.1 | ceramic chip, ≤10 m rated | 1.9–3.6 V | **out** ($13.69) |
| u-blox NINA-B112-02B | C6614835 | 10 × 14 | internal PIFA | ~1.7–3.6 V | **out** ($19.67) |

- **Remote antenna (u.FL + FPC):** RN4871U + u.FL receptacle + adhesive FPC antenna
  (~40–48 × 7–8 mm, e.g. Taoglas FXP831) on the cavity wall. Eliminates the
  cavity-metal question; costs a short 50 Ω microstrip (routine over solid ground —
  the RF pad is specified for exactly this), an unshielded module (keep away from the
  switcher), a ~30-mating-cycle connector, and unverified certification. The fallback
  if the RSSI check shows the corner is hostile.
- **RN4871 (integrated):** the original profile fit — well documented, shielded,
  MSL 1 — but out of stock and its small antenna is rated only 10 m, marginal against
  3 m with cavity metal nearby. Reconsider only if restocked *and* the RSSI check
  passes with margin.
- **Parallel mezzanine:** vertical separation from main-board copper; costs cavity
  height. Dormant.

**Part-number decoding (Microchip):** base name carries the antenna option — RN4871 =
integrated chip antenna, shielded; RN4871U = no antenna, bare 50 Ω RF pad, unshielded.
The `-V/RM118` tail is temperature grade / firmware revision. The two are the same
firmware and command set but **not pin-compatible** — switching is a board spin.

**Screening criteria, priority order:** (1) working UART/AT firmware; (2) JLC
assembles it; (3) supply covers 3.45 V; (4) size and antenna interface;
(5) certification documentation; (6) cost.

## 8. Open items

1. **Antenna keep-out extents** — read the manual's PCB-design drawing (not
   text-extractable) and check the as-drawn void against it, particularly how far
   past the first pad row the vendor wants copper cleared:
   <https://www.rcscomponents.kiev.ua/datasheets/e104-bt5032a+usermanual_en_v1_5.pdf>
2. **Hardware flow control** — confirm the module's UART actually supports RTS/CTS.
   Two MCU pins are committed to it; if the firmware doesn't use it, free them and
   drop the pair.
3. **Typical application circuit** — check what the manual specifies at VCC, against
   the no-local-cap decision in §5.
4. **RSSI check** — Nordic dev board at the intended corner, battery in place (§3).
5. Cavity internal depth and cover clearance (relevant to the u.FL fallback).
6. What the link carries — only matters if audio; parameter control and telemetry
   are trivially within BLE UART throughput.
7. Recheck stock at order time.

## 9. Sources

- Ebyte E104-BT5032A product/parameters — <https://www.cdebyte.com/products/E104-BT5032A/1>
- E104-BT5032A user manual v1.5 — <https://www.rcscomponents.kiev.ua/datasheets/e104-bt5032a+usermanual_en_v1_5.pdf>
- E104-BT5032A at LCSC — <https://www.lcsc.com/product-detail/C518912.html>
- E104-BT5032A FCC filing — <https://fccid.io/2ALPH-E104BT5032A>
- RN4871U-V/RM118 at LCSC — <https://www.lcsc.com/product-detail/C633444.html>
- RN4871-V/RM118 at LCSC — <https://www.lcsc.com/product-detail/C633943.html>
- Microchip RN4870/71 datasheet DS50002489 —
  <https://ww1.microchip.com/downloads/en/devicedoc/rn4870-71-data-sheet-ds50002489e.pdf>
- NINA-B112-02B at LCSC — <https://www.lcsc.com/product-detail/C6614835.html>
