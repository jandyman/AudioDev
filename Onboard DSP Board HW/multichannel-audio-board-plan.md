# Multichannel Audio Board — Project Plan

> **Session setup (Claude, read first):** At the start of every session on this project, connect the local **AudioDev** folder before doing any work — request `~/Dropbox/Developer/AudioDev` (or its `Python_STM32` subfolder). The local copy is the single source of truth; there is no synced GitHub mirror to fall back on. Do not answer hardware/firmware questions until this folder is connected.

**Goal:** Custom PCB with a discrete STM32H7, two TLV320ADC5140 codecs (8-ch TDM capture), optional Bluetooth, running the existing AudioDev firmware ecosystem (libDaisy already replaced).

> **Layout (Phase 2):** placement, stackup, grounding, and the analog-interface calls live in `layout-notes.md`; physical test points in `test-points.md`.

**Locked decisions:**

- Discrete STM32H7 on board (not Daisy Seed): **STM32H725RGV6** — VFQFPN68 8×8 mm, on-die core SMPS (H735RGV6 is the +crypto sibling if ever needed); see Phase 0 item 1 and `power-supply.md` §4
- No external SDRAM — internal SRAM only (564 KB; worst-case audio buffering is ~77 KB, see decision log)
- JLCPCB turnkey assembly
- Both ADC5140s share one TDM bus on **SAI4_B** (master RX — the only TDM-capable SAI on the VFQFPN68); DAC on **I2S1** (master TX), both kernel-clocked from PLL3 so capture and playback are frequency-locked by construction
- Stereo DAC for audio output (one channel required; stereo is the natural granularity)
- Lithium battery power, onboard cell. **No USB connector.** Charging via the **ring of the 1/4″ TRS output jack**: normal audio cable → audio sink; special charge cable → 5 V on the ring into the charger IC. Proven on a prior active-electronics board. (Amended 2026-07-13 from "USB charging"; see `power-supply.md`)
- Bluetooth: **moved off the main board to a future mezzanine daughterboard** (amended 2026-07; see `layout-notes.md` §1.2). The main board reserves only a small board-to-board connector footprint (UART + power + ground); the module and its antenna live on the daughterboard, populated in a later spin. Relocating it off-board is what enables single-sided fit. (Was: reserved on-board pre-certified-module footprint + antenna keep-out, unpopulated on spin 1.)
- Debug: SWD via 10-pin Cortex header for Segger J-Link; RTT for logging (no UART console needed)
- Budget: one respin expected; plan structured to make spin 2 small

---

## Phase 0 — Open decisions (resolve before schematic)

1. **MCU variant — RESOLVED: STM32H725RGV6** (VFQFPN68 8×8 mm, 1 MB flash / 564 KB SRAM). The H725 has the **on-die core SMPS** the H723 lacks; running 400 MHz SMPS-direct cuts MCU rail power ~75 % vs. an H723/LDO/550 MHz baseline — roughly halves total board draw, enabling a smaller cell. **On this package SMPS-direct is the only supply mode (VDDLDO is internal), so 400 MHz is a hard ceiling** — headroom analysis and the YIN burst rework are load-bearing; the exit if they fail is a respin to the LQFP-144 H725ZGT6 with SMPS→LDO cascade (`power-supply.md` §4). SMPS inductor + caps are on the MCU sheet. Sourcing: JLCPCB C5271073, 10 pcs secured; DigiKey fallback.
2. **Clocking scheme — RESOLVED.** HSE = 24.576 MHz crystal → PLL3 (integer-N for the 48 kHz family, e.g. VCO 393.216 MHz, PLL3_P = 49.152 MHz). SAI4_B masters the TDM capture bus (BCLK 12.288 MHz + FSYNC to both codecs; codecs slave via their on-chip PLL from BCLK — no MCLK distribution); I2S1 masters the DAC (BCLK 3.072 MHz, I2SDIV = 16). Both kernel muxes (`SAI4BSEL`, `SPI123SEL`) select PLL3_P → capture and playback frequency-locked by construction. MCO1 (PA8) reserved as a clock test point. Note SAI4 is D3-domain: capture DMA via BDMA with buffers in SRAM4.
3. **DAC selection — RESOLVED: PCM5102A**, line-out (no headphone amp), on I2S1, no MCLK, strap-configured; L-pad to instrument level + volume pot. Full rationale in `dac-selection.md`.
4. **Battery/power details — IN DISCUSSION, see `power-supply.md`.** Regulator topology recommended there (buck-boost → 3.45 V digital rail, low-noise LDO → 3V3_A; TPS63020 + TPS7A20 leaning; **TP4054 linear charger** — no power path, power-off-while-charging convention, per that doc's §8) — note this supersedes the plain "buck" wording here, since the 1S cell straddles 3.3 V. Still open: cell size and connector; on/off strategy (load switch vs. always-on with sleep); battery-sense divider disconnect; plus the datasheet verifications listed in that doc.
5. **Bluetooth module target.** Pick the module now (even though DNP on spin 1) so the reserved footprint, UART routing, and antenna keep-out match a real part. **Amended (2026-07): BT relocated to a future mezzanine daughterboard — the main board carries only the board-to-board connector, so module/antenna selection now sizes the daughterboard (and its Z-height in the instrument cavity), not a main-board keep-out. See `layout-notes.md` §1.2.**
6. **Boot/programming.** BOOT0 strap; programming and debug exclusively via J-Link SWD. No USB on the board at all — charge power arrives via the output-jack ring (see locked decisions).

## Phase 1 — Optional firmware pre-validation (parallel with Phases 2–3)

Daisy-based validation is dropped — no throwaway carrier for a platform that isn't the plan. If pre-validation is wanted with zero custom hardware: Nucleo-H723ZG + TI ADC5140EVM on jumper wires (short leads; TDM at 12.288 MHz BCLK is marginal on jumpers but workable for functional validation). Validates the I2C config driver, SAI4/BDMA TDM setup (the D3-domain path the board will use), and ecosystem capture path on the same silicon family. Skip entirely if schedule favors going straight to the board — RTT makes on-board firmware debug tractable.

## Phase 2 — Schematic / netlist

- Crib the ST **Nucleo-H725** reference schematic for the MCU core (VCAP, decoupling, boot, reset, crystal, SWD, **SMPS inductor + caps**) — supply mode differs from the H723ZG Nucleo, so use the SMPS-variant reference (see `power-supply.md` §4 / AN5419)
- Power section: TP4054 charger (fed from output-jack ring), buck-boost for digital, LDO for analog, battery sense — netlist draft in `power-supply-netlist.md`
- Codec section: 2× ADC5140, shared TDM, distinct I2C addresses, analog input conditioning, AVDD filtering
- DAC section: stereo I2S DAC on its own SAI block, output filter/buffer
- BT module footprint + UART, DNP, antenna keep-out per module datasheet
- 10-pin Cortex debug header (J-Link), oriented for probe clearance
- Test points: all rails, battery sense, BCLK/FSYNC/DOUT/DIN, I2C, plus a spare GPIO header
- **Review gate (Claude):** netlist review against checklist — power sequencing, charger straps/protection (the ⚠ list in `power-supply-netlist.md` §4), SMPS/VCAP wiring vs. AN5419, boot pins, SAI pin mux validity, I2C address conflicts, codec strap pins, clock tree vs. the recommended scheme, decoupling counts

## Phase 3 — Layout

Layout done in-house (KiCad). Estimated 25–40 hours.

- 6-layer stackup: sig / gnd / sig / pwr / gnd / sig — every signal layer adjacent to a solid plane, return paths handled by construction
- Partitioning decided before routing: buck + charger in one zone, codec analog in another, digital between; buck inductor loop minimized and far from codec inputs
- Decoupling adjacent to pins, vias at the pad; VCAP caps tight to MCU; crystal loop area minimized; AVDD LDO local to the codecs
- BCLK/FSYNC short and away from analog inputs; solid unbroken ground planes, no splits
- **Review gate 1 (Claude): placement approved before any routing** — screenshot of placed, unrouted board
- **Review gate 2 (Claude):** routed-board pass from screenshots or Gerber renders — decoupling proximity, clock routing, pour issues. Not DRC; run JLCPCB DFM check as well.

## Phase 4 — Fab & assembly (JLCPCB)

- Re-confirm parts availability at order time; consign H7/codecs if needed
- Order 5 boards, 2–3 assembled
- Include: fiducials, JLC tooling requirements, panelization per their rules

## Phase 5 — Bring-up (ordered, one subsystem at a time)

1. Visual inspection + continuity on rails (before power)
2. Power: bench supply on battery input first, then real cell; all rails at spec, current draw sane; charger behavior (full charge cycle with system off, CHRḠ LED, termination)
3. J-Link SWD connect → blinky → RTT logging up → clock tree verified (MCO output to test point)
4. I2C: read codec and DAC IDs/registers
6. DAC output: known test signal out (proves TX clocking independently)
7. Single ADC5140, capture path through ecosystem
8. Dual codec TDM, all 8 channels; loopback ADC→DSP→DAC end-to-end
9. Battery life sanity measurement

Log every anomaly for the spin-2 list even if worked around.

## Phase 6 — Spin 2

- Fold in bring-up findings + any analog performance fixes (noise floor, crosstalk)
- Populate/finalize BT if deferred
- This spin is also the template for the eventual product core

## Decision log (rationale from the planning thread, 2026-07-12)

**Discrete STM32H7 over Daisy Seed.** Daisy's core value was solved SDRAM layout, solved fine-pitch assembly, and libDaisy. All three are moot: no external RAM needed (internal SRAM suffices), JLCPCB turnkey handles the fine-pitch assembly (0.4 mm QFN is inside their standard PCBA class), and libDaisy is already replaced by the in-house ecosystem. Remaining discrete-path risk is schematic-level (power sequencing, boot, clock tree) — exactly what netlist review catches, cribbing the H725 Nucleo reference. Discrete is also the eventual product path.

**MCU class — H72x over H743 (final part: STM32H725RGV6, VFQFPN68).** The H72x was picked over the former H743ZIT6 default once the RAM budget was actually sized. Worst-case audio buffering is ~77 KB (4 channels × 4 B × 0.1 s × 48 kHz, and the pitch-shifter loop buffers are shared with the delay effects), a small fraction of the H723's 564 KB SRAM — the H743's extra 1 MB RAM headroom buys nothing here. The H723 is the better fit on the axes that matter for a battery product: 550 MHz vs 480, lower power (~264 µA/MHz in Run), and 1 MB internal flash that swallows the entire lean bare-metal ecosystem (startup/clock, hand-written I2C + codec drivers, C++/Faust DSP, serial parameter protocol to the BT module — no RTOS, no FatFS; realistically ~150–350 KB), so there is no external QSPI flash and one fewer part on the board. The VFQFPN68 package (46 GPIO) fits because the design is compute-dense but pin-light — no FMC, no LCD, no Ethernet; the H735RGV6 sibling adds the crypto/hash block, a drop-in if secure boot or a secured BT link ever calls for it.

**No fundamental HW-config risk in the audio architecture.** H7 SAI does 16-slot TDM (same IP as the H750 already running DMA bare-metal); ADC5140 explicitly supports multi-device TDM bus sharing with per-channel slot assignment and BCLK-derived PLL clocking. Failures that look like "HW won't work" are schematic errors (address straps, pull-ups, DOUT bus-hold) — findable on paper.

**FW risk estimate** (experienced bare-metal STM32 dev, Claude drafting, RTT, existing Daisy DMA model): I2C driver 1–2 days; ADC5140 driver 2–4 days (mostly datasheet time: power-up sequencing, ASI slot registers); SAI stereo→TDM rework 1–3 days; dual-codec shared-DOUT integration 1–3 days (the tail risk — can eat a week). Nominal 1–2 weeks, pessimistic 3. Biggest debug lever: logic analyzer with I2S/TDM decode on the bus test points. Prove slot steering with one codec before putting both on the bus. Review Claude-drafted register config tables against the datasheet — bit-field/sequencing details are the likely error class.

**Layout in-house, not outsourced.** Low routed content (most LQFP144 pins unused); $25–40/hr vendors supply labor, not the mixed-signal placement judgment that was the concern — that lives in the constraint doc and review gates either way. 6-layer stackup (sig/gnd/sig/pwr/gnd/sig) makes return paths correct by construction and buys out most noise-craft risk for a modest upcharge. Estimated 25–40 hours; skill transfers to productization.

**Other:** no USB on the board — charging via the output-jack ring (special charge cable). Debug is J-Link SWD + RTT exclusively. BT module footprint reserved but DNP on spin 1 — pick the real module now so routing/keep-out match. One respin budgeted; plan structured so spin 2 is small.

**Open item:** clocking scheme from prior thread (claude.ai/share/d6f60836-1338-4660-b872-9f7a08425532) not yet transcribed — Phase 0 item 2 holds a placeholder assumption (H7 SAI master via PLL3 from HSE; codecs slave from BCLK via internal PLL; no MCLK distribution). Verify against the thread before schematic.

## Risk register

| Risk | Mitigation |
|---|---|
| H725RGV6 out of stock at JLC | 10 pcs secured in JLCPCB parts library; DigiKey/ST eStore fallback (consignment) |
| Clock tree mismatch with recommended scheme | Transcribe scheme from prior thread before schematic; netlist review; MCO test point |
| Power sequencing / VCAP error | Copy Nucleo values exactly; review gate |
| Buck/charger noise into codec inputs | LDO for AVDD, partitioned placement, minimized switch loops; spin-2 budget |
| Firmware + hardware debugged simultaneously | Optional Nucleo pre-validation; RTT logging from first power-up; DAC-first audio bring-up isolates TX from RX |
| BT footprint doesn't fit real module later | Pick the target module now; route UART + antenna keep-out per its datasheet |
