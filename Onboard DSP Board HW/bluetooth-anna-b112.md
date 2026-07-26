# Bluetooth — u-blox ANNA-B112 decision & integration notes

**Status:** Decision of record (2026-07-24), captured from the module-selection / placement discussion.
Companion to `layout-notes.md` §1.2 (placement/keep-out) and `multichannel-audio-board-plan.md`
(locked decisions / Phase 0 item 5). Supersedes the earlier "generic on-board DNP module" and the
interim "mezzanine daughterboard" plans.

## Decision

BT is a **u-blox ANNA-B112 (nRF52832, SiP, 6.5 × 6.5 × 1.2 mm)** reflowed onto the **main board, in a
corner** at the power/MCU end. Plain BLE serial link (u-connectXpress Serial Port Service) is the
target use — a control/parameter channel to a companion app, not audio streaming.

**Why the ANNA:** small enough to fit a board corner without a daughterboard, pre-certified (modular
approval, integrated antenna), Nordic silicon (familiar), and a plug-and-play AT/serial interface.
The whole appeal is size — it's the only pre-certified path that fits on-board.

**Plan of record:** at **minimum carve the corner keep-out** (ground cutout + tuning-strip area) so the
rest of the layout is compatible. **Full footprint prep is optional**, depending on how involved the
copy-exact reference layout turns out to be.

## Why not the ANNA — honest caveats

- **Not in the JLC assembly library; intermittently out of stock at LCSC.** So JLC turnkey won't place
  it. Either **consign** reels (buy from Digi-Key/Mouser/u-blox, ship to JLC) or **hand-reflow** it
  yourself after JLC builds the rest. This is the single biggest practical strike.
- **nRF52832, not 52840** — BT 5.0, 1M/2M PHY (no LE Coded long-range), 512 KB flash / 64 KB RAM.
  Fine for a serial control link; a ceiling only if the role grows into heavy streaming.
- **Fine-pitch LGA (52 pads, bottom-terminated).** No visual joint inspection, no iron touch-up —
  hot-air/hotplate rework only. Order 3–5 spares (~$7.50 ea) and verify by function.
- **Internal antenna is copy-exact.** Corner ground cutout + tuning strip must reproduce the u-blox
  reference design or the modular cert is void (can't retune a certified module).

If the sourcing/rework friction is a dealbreaker, the fallback is the mezzanine **daughterboard**
(`layout-notes.md` §8) carrying an **in-stock, JLC-assembled** module (Raytac MDBT42Q / Fanstel
BT832, ~16 × 10 mm) — bigger, but placeable by JLC and off the main-board floorplan.

## Link performance (BLE serial / u-connectXpress SPS)

- **Throughput:** ~**21–608 kbit/s** in u-blox's own SPS measurements, depending on connection
  interval, payload/MTU, and PHY. Realistic sustained for a control link is comfortably in the mid
  hundreds of kbit/s on the 1M PHY with reasonable parameters.
- **Latency:** governed by the **BLE connection interval** (min **7.5 ms**). Expect single-digit-to-
  tens-of-ms one-way for parameter updates. Fine for knob/preset changes; **not** sample-accurate and
  not for real-time audio.
- **Expected traffic:** the fastest is periodic **VU-meter / level updates** (tens of ms cadence) plus
  occasional knob/preset changes — well within the connection-interval budget; the link is not the
  bottleneck.
- **Verdict:** more than adequate for a parameter/control channel. If the role ever became "stream
  scope/waveform data or fast FOTA," revisit toward a 52840 + 2M PHY.

## Interface (already reserved — see `pin-allocation.md`)

| Signal | MCU pin | Note |
|---|---|---|
| USART3_TX / RX | PC10 / PC11 | to ANNA RX / TX |
| USART3_RTS / CTS | PB14 / PB13 | HW flow control |
| BT reset/enable (`BT1`) | PB12 | control line |
| BT status/wake (`BT2`) | PB15 | control line |
| Power | `3V45_D` | 3.45 V digital rail (within ANNA VDD range) |
| GND | — | unified plane |

Confirm the ANNA's UART pinout maps to these and that it uses HW flow control.

## Placement & keep-out (detail in `layout-notes.md` §1.2)

- Corner at the **noisy end**, farthest from the analog inputs, steered off the TPS63020 switcher.
- Costs ~8 mm MCU travel toward analog (MCU ≈ 27 mm vs ≈ 35 mm on-center from nearer ADC) — acceptable;
  the unified ground plane and analog-trace discipline govern ADC noise, not this 8 mm.
- Corner **ground-plane cutout (all layers) + tuning strip**, copy-exact from the u-blox reference.
  Deliberate hole in the unified ground, at the extreme corner so no analog return detours around it.
- Keep the **audio-output corridor + its ground guard out of the keep-out** (no ground there) and
  ≥ ~20 mm from the radiator; small RF shunt cap at the high-Z audio node covers rectification.

## Hand-reflow recipe (if not consigning)

- Buy a cheap **preheater/hotplate** (~$40–80) — not an iron; you can't iron an LGA. Preheat is the
  lever that lets you use gentle airflow and stops passives blowing around.
- **Leaded paste (Sn63Pb37, melts 183 °C)** for the ANNA, peak **~200–210 °C**. That's below SAC305's
  217 °C liquidus, so JLC's existing lead-free neighbor joints **can't remelt** — they stay anchored
  regardless of airflow (parts fly only when *their* solder is molten).
- Board on preheater ~130–150 °C; kapton over parts within a few mm (kapton is good to ~260 °C, won't
  melt); wide nozzle, **low airflow**, hot-air setpoint ~270–290 °C aimed to bring the joint to ~200 °C.
- **Watch the solder, not the display** — it goes shiny/liquid and the module self-centers ("snap");
  pull heat then. ~30–60 s total in the zone.
- No visual joint inspection (bottom-terminated) → verify by current draw + BLE advertising. Optional:
  K-type thermocouple by the module to confirm ~200 °C, not 217+.
- Give the ANNA a 1–2 mm passive-free keep-out ring in layout so no tiny 0402 sits at the rework zone.

## Reference links

- ANNA-B112 product page: https://www.u-blox.com/en/product/anna-b112-module
- Data sheet (UBX-18011707): https://download.mikroe.com/documents/datasheets/ANNA-B112_DataSheet.pdf
- **System Integration Manual (UBX-18009821)** — footprint, antenna keep-out (Fig. 30), tuning-strip
  reference design, reflow profile. Pull from u-blox (also has downloadable reference-design Gerbers).
- u-connectXpress Low Energy Serial Port Service protocol spec (UBX-16011192) — the AT/serial interface.
- LCSC listing (part **C6124128**, ANNA-B112-01B): https://www.lcsc.com/product-detail/bluetooth-modules_u-blox-anna-b112-01b_C6124128.html
- Open-CPU variant (if custom Nordic-SDK firmware ever wanted): https://www.u-blox.com/en/product/anna-b112-open-cpu

## Open items

- ⚠ Reproduce the u-blox internal-antenna reference layout exactly (cutout + tuning strip); grab the Gerber.
- ⚠ Decide consign vs. hand-reflow before BOM/assembly.
- ⚠ Confirm ANNA UART pinout + flow-control mapping to the reserved pins.
- Decide full footprint prep vs. keep-out-only for this spin.
