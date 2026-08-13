# Multichannel Audio Board — Project Plan

> **Session setup (Claude, read first):** At the start of every session on this project, connect the local **AudioDev** folder before doing any work — request `~/Dropbox/Developer/AudioDev` (or its `Python_STM32` subfolder). The local copy is the single source of truth; there is no synced GitHub mirror to fall back on. Do not answer hardware/firmware questions until this folder is connected.

**Goal:** Custom PCB with a discrete STM32H7 and two TLV320ADC5140 codecs (8-ch TDM capture), running the existing AudioDev firmware ecosystem (libDaisy already replaced).

> **Layout (Phase 2):** placement, stackup, grounding, and the analog-interface calls live in `layout-notes.md`; physical test points in `test-points.md`.

**Locked decisions:**

- Discrete STM32H7 on board (not Daisy Seed): **STM32H725RGV6** — VFQFPN68 8×8 mm, on-die core SMPS (H735RGV6 is the +crypto sibling if ever needed); see Phase 0 item 1 and `power-supply.md` §4
- No external SDRAM — internal SRAM only (564 KB; worst-case audio buffering is ~77 KB, see decision log)
- JLCPCB turnkey assembly
- Capture converters: **two TLV320ADC5140**, 4 single-ended AC-coupled channels each. Chosen for in-device gain (channel PGA + digital volume + DRE) so the analog board path stays unity with no external preamp, a mic-bias rail that powers the pickup buffers, and designed-in shared-TDM multi-device operation. Rationale, requirements, and all device documentation links in `adc-selection.md`; register configuration and bring-up in `adc-firmware-init.md`
- Signal source: **two offboard 4-channel JFET preamp boards**, one per pickup, mounted under the bobbins — impedance conversion only, no gain, powered from their own device's MICBIAS. See `preamp-board.md`
- Both ADC5140s share one TDM bus on **SAI4_B** (master RX — the only TDM-capable SAI on the VFQFPN68); DAC on **I2S1** (master TX), both kernel-clocked from PLL3 so capture and playback are frequency-locked by construction
- Stereo DAC for audio output (one channel required; stereo is the natural granularity)
- Lithium battery power, onboard cell. **No USB connector.** Charging via the **ring of the 1/4″ TRS output jack**: normal audio cable → audio sink; special charge cable → 5 V on the ring into the charger IC. Proven on a prior active-electronics board. (Amended 2026-07-13 from "USB charging"; see `power-supply.md`)

---

## Phase 0 — Architecture decisions (all resolved)

1. **MCU variant — RESOLVED: STM32H725RGV6** (VFQFPN68 8×8 mm, 1 MB flash / 564 KB SRAM). The H725 has the **on-die core SMPS** the H723 lacks; running 400 MHz SMPS-direct cuts MCU rail power ~75 % vs. an H723/LDO/550 MHz baseline — roughly halves total board draw, enabling a smaller cell. **On this package SMPS-direct is the only supply mode (VDDLDO is internal), so 400 MHz is a hard ceiling** — headroom analysis and the YIN burst rework are load-bearing; the exit if they fail is a respin to the LQFP-144 H725ZGT6 with SMPS→LDO cascade (`power-supply.md` §4). SMPS inductor + caps are on the MCU sheet. Sourcing: JLCPCB C5271073, 10 pcs secured; DigiKey fallback.
2. **Clocking scheme — RESOLVED.** System sample rate is **32 kHz** (bass content is negligible above ~10 kHz; the drop cuts YIN's cost ~56 %, since it scales as fs² — more than the 27 % clock cut the 400 MHz ceiling imposes). **HSE = 24.000 MHz** — a stock frequency picked for sourcing, not arithmetic: /M=5 → 4.8 MHz, ×N=128 → 614.4 MHz VCO, /P=25 → **PLL3_P = 24.576 MHz**, exact. SAI4_B masters the TDM capture bus (BCLK 8.192 MHz = PLL3_P ÷ 3, plus FSYNC to both codecs; codecs slave via their on-chip PLL from BCLK — no MCLK distribution); I2S1 masters the DAC (BCLK 2.048 MHz = PLL3_P ÷ 12). Both kernel muxes (`SAI4BSEL`, `SPI123SEL`) select PLL3_P → capture and playback frequency-locked by construction. 48 kHz stays reachable on the same tree (SAI ÷2, I2S ÷8). MCO1 (PA8) reserved as a clock test point. Note SAI4 is D3-domain: capture DMA via BDMA with buffers in SRAM4. **Crystal: NDK NX1612SA-24MHZ (JLC C280834), SMD1612-4P — 1.92 mm², CL 8 pF, ESR 150 Ω max, load caps 6.8 pF.** Package size is the governing constraint in the HSE corner, not frequency or price; see `layout-notes.md` §5.1.1 and `pin-allocation.md` §4.
3. **DAC selection — RESOLVED: PCM5102A**, line-out (no headphone amp), on I2S1, no MCLK, strap-configured; L-pad to instrument level + volume pot. Full rationale in `dac-selection.md`.
4. **Battery/power — RESOLVED, see `power-supply.md`.** **TPS63020** buck-boost → 3.45 V digital rail (the 1S cell straddles 3.3 V, so a plain buck won't do); **TPS7A20** low-noise LDO → 3V3_A; **TP4054** linear charger — no power path, power-off-while-charging convention. On/off is a hard switch in the battery line via the volume pot's integrated switch; the battery-sense divider hangs on the post-switch node, so it needs no disconnect. Cell: 1S Li-ion, ~1200 mAh planned, picked at build. Remaining items in that doc's §9 are datasheet verifications and two capacitance corrections, not decisions.
6. **Boot/programming.** BOOT0 strap; programming and debug exclusively via J-Link SWD. No USB on the board at all — charge power arrives via the output-jack ring (see locked decisions).

## Phase 1 — Optional firmware pre-validation (parallel with Phases 2–3)

Daisy-based validation is dropped — no throwaway carrier for a platform that isn't the plan. If pre-validation is wanted with zero custom hardware: Nucleo-H723ZG + TI ADC5140EVM on jumper wires (short leads; TDM at 12.288 MHz BCLK is marginal on jumpers but workable for functional validation). Validates the I2C config driver, SAI4/BDMA TDM setup (the D3-domain path the board will use), and ecosystem capture path on the same silicon family. Skip entirely if schedule favors going straight to the board — RTT makes on-board firmware debug tractable.

## Phase 2 — Schematic / netlist

- Crib the ST **Nucleo-H725** reference schematic for the MCU core (VCAP, decoupling, boot, reset, crystal, SWD, **SMPS inductor + caps**) — supply mode differs from the H723ZG Nucleo, so use the SMPS-variant reference (see `power-supply.md` §4 / AN5419)
- Power section: TP4054 charger (fed from output-jack ring), buck-boost for digital, LDO for analog, battery sense — netlist draft in `power-supply-netlist.md`
- Codec section: 2× ADC5140, shared TDM, distinct I2C addresses, analog input conditioning, AVDD filtering
- DAC section: stereo I2S DAC on its own SAI block, output filter/buffer
- 10-pin Cortex debug header (J-Link), oriented for probe clearance
- Test points: all rails, battery sense, BCLK/FSYNC/DOUT/DIN, I2C, plus a spare GPIO header
- **Review gate (Claude):** netlist review against checklist — power sequencing, charger straps/protection (the ⚠ list in `power-supply-netlist.md` §4), SMPS/VCAP wiring vs. AN5419, boot pins, SAI pin mux validity, I2C address conflicts, codec strap pins, clock tree vs. the recommended scheme, decoupling counts

## Phase 3 — Layout

Layout done in-house (KiCad). Estimated 25–40 hours.

- 4-layer stackup: Sig / GND / GND-dominant (with a local `3V45_D` island under the MCU) / Sig — every signal layer adjacent to a solid ground reference, return paths handled by construction. Layer table and reasoning in `layout-notes.md` §3
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
- This spin is also the template for the eventual product core

## Decision log (rationale from the planning thread, 2026-07-12)

**Discrete STM32H7 over Daisy Seed.** Daisy's core value was solved SDRAM layout, solved fine-pitch assembly, and libDaisy. All three are moot: no external RAM needed (internal SRAM suffices), JLCPCB turnkey handles the fine-pitch assembly (0.4 mm QFN is inside their standard PCBA class), and libDaisy is already replaced by the in-house ecosystem. Remaining discrete-path risk is schematic-level (power sequencing, boot, clock tree) — exactly what netlist review catches, cribbing the H725 Nucleo reference. Discrete is also the eventual product path.

**MCU class — H72x over H743 (final part: STM32H725RGV6, VFQFPN68).** The H72x was picked over the former H743ZIT6 default once the RAM budget was actually sized. Worst-case audio buffering is ~51 KB (4 channels × 4 B × 0.1 s × 32 kHz, and the pitch-shifter loop buffers are shared with the delay effects), a small fraction of the H723's 564 KB SRAM — the H743's extra 1 MB RAM headroom buys nothing here. The H723 is the better fit on the axes that matter for a battery product: 550 MHz vs 480, lower power (~264 µA/MHz in Run), and 1 MB internal flash that swallows the entire lean bare-metal ecosystem (startup/clock, hand-written I2C + codec drivers, C++/Faust DSP, serial parameter protocol — no RTOS, no FatFS; realistically ~150–350 KB), so there is no external QSPI flash and one fewer part on the board. The VFQFPN68 package (46 GPIO) fits because the design is compute-dense but pin-light — no FMC, no LCD, no Ethernet; the H735RGV6 sibling adds the crypto/hash block, a drop-in if secure boot ever calls for it.

**No fundamental HW-config risk in the audio architecture.** H7 SAI does 16-slot TDM (same IP as the H750 already running DMA bare-metal); ADC5140 explicitly supports multi-device TDM bus sharing with per-channel slot assignment and BCLK-derived PLL clocking. Failures that look like "HW won't work" are schematic errors (address straps, pull-ups, DOUT bus-hold) — findable on paper.

**FW risk estimate** (experienced bare-metal STM32 dev, Claude drafting, RTT, existing Daisy DMA model): I2C driver 1–2 days; ADC5140 driver 2–4 days (mostly datasheet time: power-up sequencing, ASI slot registers); SAI stereo→TDM rework 1–3 days; dual-codec shared-DOUT integration 1–3 days (the tail risk — can eat a week). Nominal 1–2 weeks, pessimistic 3. Biggest debug lever: logic analyzer with I2S/TDM decode on the bus test points. Prove slot steering with one codec before putting both on the bus. Review Claude-drafted register config tables against the datasheet — bit-field/sequencing details are the likely error class.

**Layout in-house, not outsourced.** Low routed content (most LQFP144 pins unused); $25–40/hr vendors supply labor, not the mixed-signal placement judgment that was the concern — that lives in the constraint doc and review gates either way. **Stackup: 4 layers (Sig / GND / GND-dominant / Sig)** — this decision log originally assumed 6. The case for 6 (BGA escape, high-speed between two planes) doesn't apply: no BGA, ~12 MHz top digital speed, routing-light single-sided layout. A solid L2 ground plane plus a GND-dominant L3 (with a local `3V45_D` island under the MCU) still makes return paths correct by construction, and is cheaper and thinner at JLCPCB. Full reasoning and layer table in `layout-notes.md` §3. Estimated 25–40 hours; skill transfers to productization.

**Other:** no USB on the board — charging via the output-jack ring (special charge cable). Debug is J-Link SWD + RTT exclusively. One respin budgeted; plan structured so spin 2 is small.

**Clocking — superseded.** This entry once flagged the clocking scheme as an untranscribed placeholder. It is now fully specified and resolved in Phase 0 item 2 (HSE 24.000 MHz → PLL3_P 24.576 MHz exact; SAI4_B masters the TDM bus at 8.192 MHz; I2S1 masters the DAC at 2.048 MHz; codecs slave from BCLK via their internal PLL, no MCLK distribution), and the 32 kHz / 256× combination is confirmed against the ADC5140 datasheet's supported-clock table (`adc-selection.md` §3). No action.

**Preamp-thread documentation merged (2026-08-11).** A separate thread covering the JFET pickup preamps and pickup design produced three documents — a design review, an ADC connection checklist, and a firmware-init note. They were folded into this doc set and deleted. **The host-side content in them was stale**: it assumed a Daisy Seed at 48 kHz on SAI2 Block B, an architecture this plan retired (see the Daisy entry above and Phase 0 item 2). It also assumed a single MICBIAS supplying all eight buffers at 2.75 V, and a signal coupling cap on the preamp board — both contradicted by the entered schematics, which use per-device MICBIAS at 3.014 V and put the blocking caps at the ADC inputs. The **analog** content was current and is now `preamp-board.md`; the register/driver content was rewritten for SAI4_B at 32 kHz as `adc-firmware-init.md`; the candidate comparison went to `adc-selection.md` §5.5, the RF-rectification mechanism to `bluetooth-constraints.md` §6.5, and the HPF/AGC/DRE-off requirement to `adc-netlist.md` §8. Two conflicts were **not** resolvable from documents and are carried as open items: the ~23 dB disagreement over source signal level (`adc-netlist.md` §11 item 9), and the main-board pickup connector (`layout-notes.md` §7 item 7b).

## Risk register

| Risk | Mitigation |
|---|---|
| H725RGV6 out of stock at JLC | 10 pcs secured in JLCPCB parts library; DigiKey/ST eStore fallback (consignment) |
| Clock tree mismatch with recommended scheme | Transcribe scheme from prior thread before schematic; netlist review; MCO test point |
| Power sequencing / VCAP error | Copy Nucleo values exactly; review gate |
| Buck/charger noise into codec inputs | LDO for AVDD, partitioned placement, minimized switch loops; spin-2 budget |
| Firmware + hardware debugged simultaneously | Optional Nucleo pre-validation; RTT logging from first power-up; DAC-first audio bring-up isolates TX from RX |
