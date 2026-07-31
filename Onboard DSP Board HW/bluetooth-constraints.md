# Bluetooth — Requirements and Options

**Status:** Leaning toward **Ebyte E104-BT5032A** in a board corner. **Not final.**
**Last revised:** 2026-07-30

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
- **Corner copper clearance available: ~10 × 16 mm, all layers.** Not much more.
- Module lives in the instrument's control cavity alongside the main board.
- Single-sided assembly is the plan of record (`layout-notes.md` §1.1).

### 1.2 Environment and link requirements

- **Control cavity is unshielded.** No foil, paint, or foil-backed cover.
- **Required range: ~10 ft (3 m).**
- **Battery sits ~20 mm from the candidate module corner** — inside typical vendor
  30 mm metal keep-away recommendations; consumes some link margin.
- Other cavity metal: pot bodies, output jack, bridge/string ground wire.

### 1.3 Not constraints

- **Power budget.** BLE draws ~5–13 mA transmitting, well under 1 mA averaged,
  against the board's ~140 mA.
- **Pin count.** A full USART3 set with flow control is free on the STM32.
- **Module sleep current.** Invisible next to the H7.
- **Footprint, pad pitch, hand-solderability.** JLC assembles.
- **External 32.768 kHz crystal.** These modules are clock-complete.

## 2. Antenna and metal — design rules

Two separate rules; do not merge them:

- **PCB copper keep-out** (integrated-antenna modules): copper-free on all layers
  under the antenna *end* plus margin. The module body wants solid ground under it —
  the keep-out is a small end-zone, not the whole module. Belongs at an extreme board
  corner, antenna edge on the board edge facing off-board, so no return path detours
  around the gap.
- **External-metal clearance**: enclosure-level vendor guidance, 10–30 mm depending
  on vendor, for best range. Not a cliff — degradation from nearby metal is graceful.

Margin picture: the leading part is rated 60 m (open area, 5 dBi far-end antenna at
2 m; a phone link is less) against 3 m required — over 20 dB of margin, part of which
the battery at 20 mm will consume. An RSSI walk-through with the Nordic dev board at
the intended corner, battery in place, is the cheap pre-layout check and should
happen before copper is committed.

## 3. Leading option — Ebyte E104-BT5032A, integrated antenna, board corner

| Attribute | Value |
|---|---|
| LCSC/JLC # | C518912 — in stock (181 @ $5.72, 2026-07-30) |
| Size | 11.6 × 16 mm, castellated SMD |
| Radio | nRF52832, BLE 5.0, master or slave |
| Interface | AT / transparent UART (Ebyte fixed-profile firmware) |
| TX / RX | 4 dBm / −96 dBm |
| Antenna | ceramic chip, 50 Ω, rated 60 m (see §2 conditions) |
| Supply | **1.7–3.6 V; ≥3.3 V for full output power** — 3.45 V rail in range |
| Logic | 3.3 V-class UART (5 V unsafe) — same-rail with the STM32 |
| Assembly | JLC SMT, MSL 3 |
| Certification | FCC modular grant (FCC ID 2ALPH-E104BT5032A); CE per vendor |

**Plan sketch:** corner placement, antenna edge on board edge facing off-board;
vendor keep-out reproduced at the antenna end; UART on the free USART3 set; test
points on the UART lines so the link debugs independently of BLE.

**Why this part:** in stock; supply range covers the rail at full power; strongest
rated antenna among stocked fixed-profile candidates; cheap; widely used (large
maker/industrial user base, active community).

**Known trade-offs (accepted for a personal build, re-examine for a product):**

- Ebyte AT-firmware documentation is thinner than Microchip-class and translated;
  verify hardware-flow-control support in the manual before pinning UART.
- Proprietary AT command set — keep a thin command-layer abstraction in firmware so
  a future vendor swap doesn't ripple.
- Faster model turnover than Microchip; availability horizon shorter.
- Community reports of difficulty *reflashing* the module are irrelevant here
  (fixed-profile use only) but confirm the stock firmware is protected.

## 4. Alternatives — recorded, open

**The candidate list is not exhaustive; nothing outside it is ruled out.** Other
fixed-profile families (u-blox NINA/ANNA, Infineon EZ-Serial, Ezurio BL65x, Telit,
Panasonic, ESP32-AT, other transparent-UART parts) may be surveyed if the lean
changes.

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
  if the RSSI pre-check shows the corner is hostile.
- **RN4871 (integrated):** the original profile fit — well documented, shielded,
  MSL 1 — but out of stock and its small antenna is rated only 10 m, marginal against
  3 m with the battery at 20 mm. Reconsider only if restocked *and* the RSSI check
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

## 5. Open items

1. **E104-BT5032A antenna keep-out extents** — read the manual's PCB-design drawing
   (not text-extractable):
   <https://www.rcscomponents.kiev.ua/datasheets/e104-bt5032a+usermanual_en_v1_5.pdf>
2. **Hardware flow control** — confirm the module's UART supports (or doesn't need)
   RTS/CTS before pinning USART3.
3. **Footprint** — generate from the EasyEDA/LCSC library. In Terminal (inside the
   `scipy` conda env): `pip install easyeda2kicad` once, then
   `easyeda2kicad --full --lcsc_id=C518912 --output <path>` — yields `.kicad_sym`,
   `.pretty` footprint, and 3D model, matching JLC's placement data. Do **not** reuse
   a Raytac footprint despite the similar outline — pad count/pitch differ.
4. **RSSI pre-check** — Nordic dev board at the intended corner, battery in place,
   before layout is committed (§2).
5. Cavity internal depth and cover clearance (relevant to the u.FL fallback).
6. What the link carries — only matters if audio; parameter control and telemetry
   are trivially within BLE UART throughput.
7. Recheck stock at order time.

## 6. Sources

- Ebyte E104-BT5032A product/parameters — <https://www.cdebyte.com/products/E104-BT5032A/1>
- E104-BT5032A user manual v1.5 — <https://www.rcscomponents.kiev.ua/datasheets/e104-bt5032a+usermanual_en_v1_5.pdf>
- E104-BT5032A at LCSC — <https://www.lcsc.com/product-detail/C518912.html>
- E104-BT5032A FCC filing — <https://fccid.io/2ALPH-E104BT5032A>
- RN4871U-V/RM118 at LCSC — <https://www.lcsc.com/product-detail/C633444.html>
- RN4871-V/RM118 at LCSC — <https://www.lcsc.com/product-detail/C633943.html>
- Microchip RN4870/71 datasheet DS50002489 —
  <https://ww1.microchip.com/downloads/en/devicedoc/rn4870-71-data-sheet-ds50002489e.pdf>
- NINA-B112-02B at LCSC — <https://www.lcsc.com/product-detail/C6614835.html>
