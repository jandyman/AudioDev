# ADC Selection & Input Requirements — Multichannel Audio Board

**Status:** Decided — **TLV320ADC5140**, two devices, 4 single-ended analog channels each, on one shared TDM bus into `SAI4_B`. The part was chosen during the planning thread and is assumed by every downstream document; this file consolidates the rationale that was previously scattered across `adc-netlist.md` §1 and the `multichannel-audio-board-plan.md` decision log, and is the home for the device documentation links (§7).
**Scope:** the capture side — why this converter, what the design requires of it, and where its documentation lives. Netlist, pin-by-pin connections, cap values and BOM are **not** here — see `adc-netlist.md`. The playback DAC is `dac-selection.md`.

> **Note on method.** Unlike `dac-selection.md`, this is **not** a clean-slate survey. No priced/stock-checked candidate table was built, and no alternative converter was formally evaluated. What follows is the reasoning *as decided*, written down so the requirements are auditable and so a future respin can re-open the choice against a stated spec rather than against memory. §6 lists what that leaves open.

---

## 1. Requirements

- **8 simultaneous analog capture channels**, one per pickup, sample-aligned across all eight — the per-string / multi-pickup DSP depends on inter-channel phase, so channels must be simultaneously sampled, not muxed.
- **Source:** low-impedance magnetic pickups, each buffered at the pickup by a JFET source-follower. Buffer output impedance ~1 kΩ; signal level **< 0.1 Vpp (≈ 12 mVrms)** — roughly **30–40 dB below** a 1 Vrms single-ended full scale.
- **The buffers need a supply.** Multi-conductor cable from each pickup group carries one power line plus one signal line per channel. The board must originate a regulated, low-noise rail for them.
- **Near-DC low-frequency response** — the sensing target includes the **onset transient of finger pressure** on the string, so the input high-pass corner must sit as close to DC as the coupling scheme allows (single-digit Hz).
- **Single 3.3 V-class supply**, battery-powered. No negative rail, no boost, no external analog reference.
- **One MCU serial-audio peripheral for all eight channels.** The VFQFPN68 package has exactly one TDM-capable SAI (`SAI4_B`); eight channels must arrive on one bit-clock/frame-sync/data trio.
- **No MCLK distribution.** The MCU is the audio-bus master and supplies BCLK/FSYNC only; the converters must derive their internal clocks from those. Board sample rate is **32 kHz**.
- **Space-constrained, minimal external parts.** No external gain stage, no external anti-alias filter, no external voltage reference.
- **JLCPCB (LCSC) stocked**, turnkey-assemblable package.

---

## 2. What the architecture demands of the part

These derived requirements do the actual selecting:

**Gain must live inside the converter.** The source sits 30–40 dB below full scale and its exact level is not yet known — it depends on the JFET buffer, which is characterized on the bench, not on paper. Putting a discrete preamp on the board would commit to a gain before that measurement, add parts to a space-constrained layout, and add a noise contributor ahead of the converter. The converter must therefore provide **enough programmable analog gain (channel PGA) plus digital volume** to lift a ~12 mVrms source to full scale, so the analog board path stays **unity** and all level-setting is a register value that can change after bring-up. *This was the primary reason for the choice.*

**The converter must supply the preamps.** A dedicated MICBIAS-class output — regulated, low-noise, with a documented current budget — lets the pickup buffers run off the converter itself. That removes an LDO, keeps the buffer supply referenced to the converter's own analog domain, and means the cable carries one power conductor instead of a separate rail. The output must be quiet enough to sit directly on a buffer's Vdd (µV-class noise) and carry the buffers' combined current.

**Multi-device bus sharing must be a designed-in feature, not a hack.** Eight channels on one SAI means several converters driving one data line. The part must support **per-channel programmable slot assignment** and must **tri-state the slots it does not own**, so devices coexist on a single data net without external bus arbitration. Equally, two identical parts must be addressable on one control bus — i.e. **strappable I²C addresses**.

**Clock-slave with internal PLL, at 32 kHz.** With no MCLK routed, the part must generate its own internal clocks by observing BCLK and FSYNC. This is a hard gate: a part that needs MCLK costs a pin and a trace across the analog section.

**Programmable input impedance.** With a fixed coupling cap, making the high-pass corner a *register* choice rather than a resistor choice is what lets the near-DC goal be tuned after the buffers are measured — and it sets how hard the 1 kΩ buffer is loaded. A part with a fixed, low input impedance would force a much larger coupling cap for the same corner.

**Integrated anti-alias.** A sigma-delta front end with internal decimation filtering removes eight external filter networks from a board that does not have room for them.

So the target category is: **a multi-channel, simultaneously-sampling, single-3.3 V audio ADC with per-channel PGA, an integrated mic-bias regulator, BCLK-derived internal PLL, programmable input impedance, and explicit multi-device shared-TDM support.** In practice that is the TI ADCx140 / PCMx140 class of audio-capture converters.

---

## 3. Why the TLV320ADC5140

- **In-device gain covers the whole 30–40 dB deficit**, in three independent stages — **analog channel PGA, 0 to 42 dB in 1 dB steps**; **digital channel volume, −100 to +27 dB in 0.5 dB steps**; and optional DRE on top. The analog PGA alone covers the deficit, with the digital stage available for per-channel trim between pickups. Gain is deferred to bring-up as a register decision; the board carries no preamp. This is the deciding property.
- **MICBIAS is a usable supply rail, not just a bias tap:** programmable output (VREF × 1.096 = 3.014 V at the default full-scale setting), **1.6 µVRMS** noise, **20 mA** per device with a 30 mA over-current trip. Each device powers only its own pickup group, so the two groups stay on separate regulators and never share a supply conductor.
- **Shared-TDM operation is a documented, supported topology** with its own TI application note (SBAA383, §7) — per-channel slot mapping (`CHx_SLOT`, any channel to any of 64 slots), unused-slot tri-state (`ASI_OUT_CH_EN`), Hi-Z fill for unused cycles (`TX_FILL`), and an **internal bus keeper** (`TX_KEEPER`) that holds the data line between drivers. External bus discipline parts are therefore not required.
- **32 kHz with a 256× bit clock is explicitly in the supported clock table** (datasheet Table 6: FSYNC 32 kHz, BCLK/FSYNC ratio 256 → **8.192 MHz**). The auto-configuration block detects the FSYNC frequency and BCLK ratio and sets every internal divider and the PLL with no host programming — and flags an ASI clock-error interrupt if the combination is unsupported. No MCLK needed.
- **Programmable per-channel input impedance** (2.5 k / 10 k / 20 kΩ) makes the high-pass corner a register choice against a fixed coupling cap, reaching ~1.7 Hz at the 20 kΩ setting — the near-DC response the finger-pressure sensing needs — while loading the 1 kΩ buffer the lightest.
- **Everything analog is on-chip:** internal 1.8 V analog and 1.5 V core regulators (so the only external supplies are one analog and one I/O rail), internal voltage reference, sigma-delta anti-aliasing, integrated high-pass and biquad filters. External passive count per device is single-digit.
- **Small, assemblable, and stocked:** 24-pin WQFN 4×4 mm, LCSC-stocked, low per-channel power (~9 mW/channel at 48 kHz) which matters for a battery instrument.
- **Headroom that is not needed but is free:** 120 dB SNR and sample rates to 768 kHz. The application uses a small fraction of both; the part was not chosen for converter performance, and a lesser sibling would also clear the bar (§6).

---

## 4. Why two four-channel devices

Not a trade-off — a family property. **Every member of the ADCx140 family is four-channel on the analog side** (up to eight channels only in PDM digital-microphone mode, which does not apply to buffered analog pickups). Eight analog channels therefore means two devices, and the design is built around that rather than against it:

- Both devices sit on **one shared TDM data line** into the single TDM-capable SAI, so two converters cost the MCU nothing extra — one peripheral, one DMA stream, one frame.
- The **two mic-bias regulators are a benefit**: each pickup group gets its own supply and its own current budget, and the two groups are never tied together.
- The two devices are **identical apart from their address straps and slot maps** — one driver, one register-configuration table, called twice.

The cost is one extra device's worth of board area, decoupling and unit price, and the shared-bus discipline itself (slot map correctness and tri-state, which is the bring-up risk called out in the plan's risk register).

---

## 5. Consequences accepted

- **An I²C control driver is mandatory.** Unlike the strap-configured playback DAC, nothing works until registers are written — power-up sequencing, slot map, input source, gain, impedance, mic-bias enable. That driver is budgeted in the plan's firmware estimate and is the reason a control bus exists on the board at all.
- **Unit price is not optimized.** This is a ~$2-class part taken ×2, chosen for its front-end flexibility rather than its cost. A cheaper capture path would have had to move gain onto the board — the thing the design is specifically avoiding.
- **Converter performance is over-specified** for a bass-guitar-level source that is gained up in-device.
- **Shared-bus correctness is a firmware property, not a hardware one.** Two devices on one data net are safe only if both slot maps and both tri-state settings are right. Prove slot steering with one device before enabling the second.

---

## 6. Context for a future re-open

The part is decided. This section exists so that if cost, supply, or a later spin ever re-opens the question, the argument can be re-run against a written spec rather than memory.

1. **No candidate comparison was made.** §1–§2 are the spec to shop against if one is ever needed. The obvious first stop is the pin-compatible siblings in the same family — same 24-pin WQFN, same register model, lower converter performance, likely lower price — a drop-in on the same footprint the way the playback DAC's cost-down sibling is. **Not evaluated; noted as an option, not a recommendation.**
2. **LCSC stock at order time** is the live supply risk (plan risk register). Checked 2026-07-28: in stock, 24-WQFN 4×4, ~$1.93 (see §7) — recheck at order.
3. **Gain is uncharacterized.** The choice is validated only once the JFET buffer output level is measured and PGA/digital/DRE values are set without clipping at full scale (`adc-netlist.md` §11 item 9).
4. **Mic-bias current budget is unverified.** The four buffers per device must draw less than the device's 20 mA limit (`adc-netlist.md` §11 item 10). If they do not, the "converter supplies the preamps" premise in §2 fails and a separate rail comes back.

---

## 7. Device documentation

**Primary**

| Document | ID / Rev | Link |
|---|---|---|
| TLV320ADC5140 datasheet — quad-channel, 768 kHz, 120 dB SNR audio ADC | **SBAS892A**, Jul 2019 (rev Oct 2019) | https://www.ti.com/lit/ds/symlink/tlv320adc5140.pdf |
| Product folder — errata, related docs, package/ordering | — | https://www.ti.com/product/TLV320ADC5140 |

Datasheet sections that the design leans on: **§8.3.2** PLL and clock generation (Tables 6–7, the supported FSYNC/BCLK combinations — this is where 32 kHz at 256× is confirmed); **§8.3.3** analog input configuration (single-ended connection, Fig. 37; coupling-cap quick-charge); **§8.3.4** reference and mic bias; the ASI/TDM section for slot mapping and word length; and the register map for the configuration tables in `adc-netlist.md` §8.

**Multi-device operation — the key application note**

| Document | ID / Rev | Link |
|---|---|---|
| Multiple TLV320ADCx140 / PCMx140-Q1 / ADCx120 / PCMx120-Q1 Devices With Shared TDM and I²C Bus | **SBAA383C**, Jan 2020 (rev Jan 2024) | https://www.ti.com/lit/an/sbaa383c/sbaa383c.pdf |

This is the authority for the two-device bus: shared-TDM vs. daisy-chain topologies, the ADDR strap options for coexisting devices on one control bus, slot assignment via `ASI_CHx`, unused-slot tri-state via `ASI_OUT_CH_EN`, unused-cycle Hi-Z via `TX_FILL` (`ASI_CFG0`), and the bus keeper / LSB-hold controls in `ASI_CFG1` (`TX_KEEPER`, `TX_LSB`, `TX_OFFSET`) that prevent contention at slot boundaries. It also carries worked I²C configuration scripts for multi-device shared TDM — the closest thing to a reference for the firmware's register table.

| Document | ID | Link | Relevance |
|---|---|---|---|
| Operating the TLV320ADCx140 as an audio bus master | SBAA382 | https://www.ti.com/lit/an/sbaa382/sbaa382.pdf | **Opposite of this design** — here the MCU is master and the converters are slaves. Useful only as background on the ASI clocking model. |

**Evaluation & tooling**

| Item | Link | Note |
|---|---|---|
| ADC5140EVM-PDK evaluation board | https://www.ti.com/tool/ADC5140EVM-PDK | Ships with the AC-MB motherboard. This is the board the plan's optional pre-validation path would jumper to a Nucleo. |
| ADCx140EVM-PDK user's guide — **SBAU335**, May 2019 | https://www.ti.com/lit/ug/sbau335/sbau335.pdf | Schematics and layout of TI's own implementation — useful cross-check for the regulator-output cap values (`AREG` / `DREG` / `VREF` / `MICBIAS`) that the datasheet states only as minimums. |
| PurePath Console 3 | https://www.ti.com/tool/PUREPATHCONSOLE | GUI configuration/evaluation suite; can emit register scripts that are a useful sanity check against a hand-written driver. |
| Linux ASoC driver `tlv320adcx140.c` | https://github.com/torvalds/linux/blob/master/sound/soc/codecs/tlv320adcx140.c | Independent, working register-level implementation (TI-authored, in mainline). Good for confirming reset/power-up sequencing, gain-range encodings, and bit-field interpretation when the datasheet is terse. Its companion `tlv320adcx140.h` is a clean register-name header. |
| TI E2E audio forum | https://e2e.ti.com/support/audio-group/audio/f/audio-forum | Existing threads cover two-device shared-TDM/daisy-chain confusion specifically. |

**Sourcing**

| Source | Link | Checked 2026-07-28 |
|---|---|---|
| LCSC — TLV320ADC5140IRTWR, C2876368 | https://www.lcsc.com/product-detail/adcs-dacs-special-purpose_texas-instruments-tlv320adc5140irtwr_C2876368.html | In stock (379), WQFN-24 4×4, from ~$1.93 |
| JLCPCB parts library — C2876368 | https://jlcpcb.com/partdetail/3084980-TLV320ADC5140IRTWR/C2876368 | Confirm assembly class at order time |
| SnapMagic symbol/footprint/3D | https://www.snapeda.com/parts/TLV320ADC5140IRTWR/Texas%20Instruments/view-part/ | Alternative to the KiCad library symbol — verify pin numbers against the datasheet pin table either way |

⚠ **Order-part-number note.** The reel part is **TLV320ADC5140IRTWR** (leading **T**, not X). A transposed leading character corrupts BOM lookup silently — check it at BOM export.

---

## 8. Where the rest lives

| Topic | Document |
|---|---|
| Input stage, coupling caps, corner frequency, nets, per-pin connections, decoupling, BOM, open netlist items | `adc-netlist.md` |
| Register-configuration intent (kept in sync with the netlist) | `adc-netlist.md` §8 |
| SAI/I²C/GPIO assignment and the PLL3 clock tree | `pin-allocation.md` |
| Analog and digital rails feeding the converters | `power-supply.md`, `power-supply-netlist.md` |
| Decoupling rules per device | `decoupling-checklist.md` |
| Analog-section placement and bus routing constraints | `layout-notes.md`, `placement-register.md` |
| Probe points on the capture bus | `test-points.md` |
| Phase gates, bring-up order, risk register | `multichannel-audio-board-plan.md` |
| Playback DAC decision | `dac-selection.md` |
