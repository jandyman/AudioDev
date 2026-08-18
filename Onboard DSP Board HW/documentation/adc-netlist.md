# Codec (ADC) Section — Netlist + BOM

**Status:** Draft for schematic entry (started 2026-07-14). Implements the codec section of Phase 2 in `multichannel-audio-board-plan.md`; consumes the SAI/I2C/GPIO allocation from `pin-allocation.md` §1–§4 and the `3V3_A` / `3V45_D` rails from `power-supply-netlist.md`. Connections are given **by pin name** — take pin *numbers* from the KiCad symbol / datasheet at entry, don't trust memory. Items marked ⚠ go on the netlist-review-gate checklist. Datasheet: TI **SBAS892A** (TLV320ADC5140), 24-pin WQFN.

**Scope:** two TLV320ADC5140 codecs, each configured as **4× single-ended, AC-coupled** analog inputs → 8 channels on one shared TDM bus into `SAI4_B` (RX). Analog input conditioning, coupling/blocking caps, shared clock/data bus, distinct I²C addresses, per-device power + decoupling. The stereo DAC (`I2S1` TX) is a separate section — see `dac-selection.md`.

**Why this part** — requirements, rationale, and all device documentation links (datasheet, the shared-TDM application note SBAA383, EVM, tooling, sourcing) live in **`adc-selection.md`**. This file assumes the choice and implements it.

**What feeds it** — the offboard per-string preamp boards (circuit, values, connector, cable, their own layout) are **`preamp-board.md`**; why that front end amplifies rather than buffers is **`analog-front-end.md`**. **What configures it** — register map, SAI driver, and bring-up order are **`adc-firmware-init.md`**.

---

## 1. Design inputs (confirmed with user 2026-07-14)

- **Source per channel:** low-impedance magnetic pickups, each **amplified at the pickup by an operational amplifier with a gain of approximately eight** (`preamp-board.md`). Source impedance presented to the converter is an amplifier output — **ohms**, not kilohms — so converter input loading is no longer a design consideration. Signal level is **≈ 320 mV peak-to-peak**, roughly **17 dB below** the ADC's single-ended full scale, derived from a measured coil output of 40 mV peak-to-peak (`analog-front-end.md` §1).
- **Gain:** the front end supplies the bulk of it. The converter's channel PGA and digital volume trim the remainder and absorb the residual channel-to-channel spread, which is now resistor tolerance rather than a semiconductor distribution. The PGA requirement is far lower than originally specified — set it against the measured level, not against the earlier ~12 mVrms assumption. (Rationale: `analog-front-end.md` §2; register values `adc-firmware-init.md`.)
- **Preamp powering:** each pickup preamp is powered from the **3.3 V analog rail**, one power conductor per board. **MICBIAS is not used.** It was originally chosen for noise isolation, which was necessary only because a source follower ties its drain to its supply and rejects almost nothing; the specified amplifier rejects more than 80 dB across the audio band, so a rail shared with digital loads is acceptable (`analog-front-end.md` §4). Wiring is **multi-conductor** (one power line + one signal line per channel + ground) through a per-device pickup connector (one for ADC-A, one for ADC-B). Board current is approximately **3.1 mA per board**. Retiring MICBIAS also removes the bring-up ordering dependency, the single-device fault mode, and the mic-bias current budget as an open question — and gives up MICBIAS's current limiting and firmware power switch, restorable with a load switch or resettable fuse if wanted.
- **Coupling:** **AC-coupled** to reject the preamp's 1.0 V output bias while passing near-DC audio. **Signal blocking cap (INxP) = 4.7 µF tantalum, 16 V or higher, positive terminal toward the converter, with a parallel silicon clamp diode** — sized to push the high-pass corner as low as practical (~1.7 Hz at 20 kΩ input impedance) so the **onset transient of finger pressure** on the string is captured; see §2 for the polarity argument and why ceramic is rejected. It taps the preamp's signal line into INxP. **Matching cap (INxM) = 1 µF X7R preferred** (the 4.7 µF currently drawn is also fine — it carries no signal; see §2).
- **Channels:** all 8 identical single-ended AC-coupled, unless a per-channel exception is called out later.

### Why single-ended AC-coupled here (datasheet basis, SBAS892A §8.3.3)

Each ADC5140 has four `INxP`/`INxM` analog pin pairs. In single-ended mode (`CHx_INSRC = 01`) the signal enters **INxP through the blocking cap**, and **INxM is grounded through a matching cap** — *not* directly to ground (Fig. 37). The INxM cap is required because the front end is internally differential and biased to an internal common-mode; a hard ground on INxM would fight that bias. Four pairs → **4 single-ended channels per device**, ×2 devices = **8 channels**, matching the board plan.

---

## 2. Input stage — coupling caps, impedance, corner

The high-pass corner is set by the blocking cap and the **programmable input impedance** `CHx_IMP` (2.5 k default / 10 k / 20 k, I²C-selectable per channel, SBAS892A Table 9), not by an external resistor:

```
fc(-3dB) = 1 / (2π · R_imp · C_in)
```

With **C_in = 4.7 µF** fixed, the impedance setting directly picks the corner. Source impedance is an amplifier output — ohms — so **input loading is no longer part of this decision** and the corner is set by `C_in` and `R_imp` alone:

| `CHx_IMP` | Corner @ 4.7 µF | Source loading | Noise / DR |
|---|---|---|---|
| 2.5 kΩ | ~13.5 Hz | negligible | lowest noise |
| 10 kΩ | ~3.4 Hz | negligible | slightly higher |
| **20 kΩ (recommended)** | **~1.7 Hz** | negligible | slightly higher still |

> **Note on what changed.** An earlier revision weighed a **−3.8 dB to −0.6 dB** insertion loss across these settings, because the source was a follower with ~1.4 kΩ of output impedance. With an amplified, low-impedance source that column is gone: every setting passes full level, and the choice is purely corner frequency against converter dynamic range. The recommendation below is unaffected, but the reason it is cheap has changed.

**Recommendation: 20 kΩ.** The setting is free — source loading no longer enters the choice, and the "slightly higher noise" of the 20 kΩ setting is immaterial against a source amplified at the pickup, where converter noise dominates. Taking the lowest available corner costs nothing, so take it: 20 kΩ × 4.7 µF ≈ **1.7 Hz**. **10 kΩ** (~3.4 Hz) is a fallback if a touch more dynamic range is ever wanted. ⚠ **user-confirm** — §11 item 1.

> **What this corner is and is not for.** Earlier revisions justified it as "near-DC response to capture the onset transient of finger pressure", implying that reaching lower recovers more of the pluck. It does not. A magnetic pickup is a velocity transducer with a first-order zero at DC of its own, so a statically displaced string produces no output at any frequency and there is no near-DC pedestal for this network to pass or block. What the release event presents is a velocity transient, and the useful question is whether its slow portion arrives with usable signal-to-noise, not how close to DC the network reaches. The full argument, and the consequence that the low-frequency shaping is recovered digitally rather than bought with analog parts, is `analog-front-end.md` §6. **Do not re-open the cap value or the input impedance on low-corner grounds.**

**Blocking-cap charge time.** 4.7 µF exceeds the device's default coupling-cap quick-charge window (default sized for **≤ 1 µF**). No hardware cost — firmware raises `INCAP_QCHG` (P0_R5_D[5:4]) so the caps charge to the common-mode at power-up without a long settle (SBAS892A §8.3.3). Captured in §8.

**Matching cap (INxM) = 1 µF X7R preferred; 4.7 µF as currently drawn is also acceptable.** INxM carries no signal (it's only the AC-ground reference for the internally-differential front end), so its value does not enter the signal transfer — the passband and the ~1.7 Hz corner are set entirely by the INxP cap. At **4.7 µF** it simply matches the signal cap and gives the best low-frequency common-mode reference (its own AC-ground corner also ~1.7 Hz). At **1 µF** that node's AC-ground corner rises to ~8 Hz (at 20 k `R_imp`), slightly reducing common-mode rejection below ~8 Hz — subsonic, negligible common-mode content from instrument pickups, so **inaudible** — in exchange for a smaller/cheaper part. X7R is fine either way (low swing). **The schematic currently uses 4.7 µF (the INxM matching caps on both ADCs);** pick one value and make doc + schematic agree.

### Signal blocking cap — dielectric, polarity, and clamp

**Use 4.7 µF tantalum, positive terminal toward the converter input, rated 16 V or higher.**

**Polarity is resolved, with margin.** In AC-coupled mode the converter self-biases its own input pins to **VREF/2 ≈ 1.375 V** (VREF = 2.75 V at `ADC_FSCALE = 00`; TI's SBAA583 states VREF/2 for the sibling ADCX120 family, and TI applications give ~1.45 V for the ADCx140). The preamp presents its output bias point, specified at **1.0 V** and set by a resistor divider (`preamp-board.md` §5). The converter side is therefore the higher side by **375 mV** on every channel. Positive terminal toward the converter.

**The bound that makes this safe is now a resistor ratio rather than a semiconductor distribution.** The preamp's output rests wherever its bias divider puts it, to the tolerance of two resistors and an amplifier offset of tens of microvolts — there is no part-to-part spread to bound, and the 1.0 V value was chosen specifically to preserve this polarity with a healthy bias on the dielectric.

> **Selection rule for any future device or supply change:** the preamp's bias point must sit **below** the converter's input bias, with margin. Verify it as a divider calculation at design time and as a DC measurement at bring-up (`preamp-board.md` §12 item 4).

⚠ **The clamp diode remains required.** It is no longer covering a part-distribution edge case — it covers the power-sequencing window, in which the preamp boards and the converter now come up independently because they no longer share a supply. That is a *wider* window than the MICBIAS arrangement it replaces, not a narrower one.

**A clamp diode covers the power-sequencing window.** The only state in which the sign could invert is a transient one: the preamp rail live while the converter's input common-mode has not yet come up. Fit a **small-signal silicon switching diode in parallel with each blocking cap, cathode toward the converter input** — reverse-biased by ~0.375 V in normal operation. Silicon rather than Schottky: the reverse excursion is bounded at well under a volt by the argument above, so a harder clamp buys nothing, while Schottky leakage into a low-level 20 kΩ node is a real cost. Silicon leakage is nanoamps, well under a millivolt of offset across `R_imp`, and calibrated out downstream regardless. Junction capacitance of a few pF in parallel with 4.7 µF is immaterial.

⚠ **The clamp is now the primary defence, not insurance.** It previously backed up a firmware ordering — input channels powered before MICBIAS — that guaranteed the converter's common-mode was up before the preamps had a rail. With the preamps on the 3.3 V analog rail that guarantee is gone and firmware cannot restore it (`adc-firmware-init.md` §3.4). Do not omit these diodes.

**Distortion is not a concern at this level, in either dielectric.** At 20 Hz the blocking cap's reactance is ~1.7 kΩ against a 20 kΩ input impedance, so under 10% of the signal appears across the dielectric — a few tens of millivolts at the level this front end delivers. Voltage-coefficient distortion is driven by the AC volts across the dielectric, and the published capacitor-distortion measurements that make dielectric choice matter were taken at volts, not millivolts.

**Class II ceramic (X7R/X5R) was considered and rejected**, despite being non-polar and thus sidestepping the polarity question entirely. The reason is **not** distortion — see above — but **piezoelectricity**. Barium-titanate dielectrics generate charge under mechanical stress, injecting a series voltage into the signal path. Unlike distortion, that mechanism does not scale down with signal level; it is additive, so it gets relatively *worse* as the signal gets smaller. A microphonic element in a ~12 mVrms path, mounted in the control cavity of an instrument that is struck for a living, is not an acceptable trade for removing a polarity constraint that is already resolved and clamped. Tantalum has no piezoelectric mechanism. **Do not re-propose ceramic here.** C0G is not available at this capacitance, and film is too large for the cavity.

**Voltage derating.** Working voltage is ~1.1 V. Tantalum reliability practice is heavy derating rather than the 2× that would be acceptable on a ceramic, so specify **16 V or 25 V**, not 6.3 V.

**EMI / anti-alias.** The ADC5140 is a sigma-delta with internal anti-alias; no external AA filter is needed. Provide an **optional shunt cap footprint (~100–330 pF, DNP)** from each INxP to AVSS for RF immunity, populated only if bench testing shows a need. No series resistor — it would shift the corner and add noise into a low-level path.

---

## 3. Nets

| Net | Description |
|---|---|
| `IN1_SIG`…`IN8_SIG` | Per-channel signal lines (from the pickup connectors): each preamp channel's amplified output → blocking cap → INxP. ≈320 mVpp, ohms-level source. Preamp boards are powered separately from the 3.3 V analog rail |
| `MICBIAS_A` / `MICBIAS_B` | ⚠ **Unused.** Previously the preamp supply; the preamp boards now take the 3.3 V analog rail through their pickup connectors (§1). Leave unconfigured |
| `BCLK_ADC` | `SAI4_SCK_B` bit clock (PA2), MCU → both codecs (shared) |
| `FSYNC_ADC` | `SAI4_FS_B` frame sync (PC0), MCU → both codecs (shared) |
| `SDOUT_ADC` | Shared TDM data bus, both codecs → `SAI4_SD_B` (PA0) (per-device slot assignment + unused-slot tri-state) |
| `I2C_SCL` / `I2C_SDA` | I2C1 control bus (shared with nothing else — DAC is strap-configured) |
| `CODEC_SHDNZ` | Active-low shutdown/reset, MCU PC6 → both codecs (shared) |
| `3V3_A` | Analog rail (AVDD) — from `power-supply-netlist.md` LDO |
| `3V45_D` | Digital rail (IOVDD) — see §7 IOVDD note ⚠ |
| `GND` | Single ground plane (AVSS + thermal pad direct to plane; no AGND/DGND split) |

---

## 4. Per-device connections (both codecs identical except ADDR strap + slot map)

The two devices are **ADC-A** and **ADC-B**. Pin numbers per the 24-WQFN pinout (SBAS892A pin table).

| Pin | Name | Net / connection |
|---|---|---|
| 1 | AVDD | `3V3_A` + 0.1 µF to GND at pin; 10 µF bulk shared on the 3V3_A pour near the device |
| 2 | AREG | on-chip 1.8 V analog reg output (AVDD = 3.3 V mode) → **1 µF to AVSS at pin**, no external supply ⚠ |
| 3 | VREF | **1 µF to AVSS at pin** (min per §8.3.4). Larger cap ⇒ raise `VREF_QCHG` |
| 4 | AVSS | `GND` (direct to plane) |
| 5 | MICBIAS | `MICBIAS_A`/`MICBIAS_B` — buffer supply rail. **1 µF to AVSS at pin** (sets the 1.6 µVRMS noise spec); routes to this device's 4 buffer rails via its pickup connector, **no series resistor**. `MBIAS_VAL = 001` → 3.014 V, powered on via `MICBIAS_PDZ` |
| 6 | IN1P_GPI1 | from buffer-1 signal line via a **4.7 µF tantalum** blocking cap, **+ toward this pin**, with a parallel silicon clamp diode, **cathode toward this pin** (GPI1 disabled — analog SE input); §2 |
| 7 | IN1M_GPO1 | **1 µF X7R to GND** (matching cap; single-ended AC-coupled per Fig. 37; 4.7 µF as drawn) |
| 8 | IN2P_GPI2 | from buffer-2 signal line via 4.7 µF tantalum, + and diode cathode toward this pin |
| 9 | IN2M_GPO2 | 1 µF X7R to GND (4.7 µF as drawn) |
| 10 | IN3P_GPI3 | from buffer-3 signal line via 4.7 µF tantalum, + and diode cathode toward this pin |
| 11 | IN3M_GPO3 | 1 µF X7R to GND (4.7 µF as drawn) |
| 12 | IN4P_GPI4 | from buffer-4 signal line via 4.7 µF tantalum, + and diode cathode toward this pin |
| 13 | IN4M_GPO4 | 1 µF X7R to GND (4.7 µF as drawn) — ⚠ **ADC-B IN4M cap missing in schematic** |
| 14 | SHDNZ | `CODEC_SHDNZ` (MCU PC6, shared); 10 kΩ pull-down to GND (on the MCU sheet) holds the part in reset until the MCU drives it |
| 15 | ADDR1_MISO | I²C address strap A1 — **device-distinct** (see §6) |
| 16 | ADDR0_SCLK | I²C address strap A0 — **device-distinct** (see §6) |
| 17 | SCL_MOSI | `I2C_SCL` (PB8); 2.2–4.7 kΩ pull-up to IOVDD (one pair for the bus) |
| 18 | SDA_SSZ | `I2C_SDA` (PB9); 2.2–4.7 kΩ pull-up to IOVDD |
| 19 | IOVDD | `3V45_D` (recommended, see §7 ⚠) + 0.1 µF to GND at pin |
| 20 | GPIO1 | **unused** — leave as configured Hi-Z / optional test point (interrupt option for spin 2) |
| 21 | SDOUT | `SAI4_SD_B` (PA0, shared bus; tri-state unused slots — §5) |
| 22 | BCLK | `SAI4_SCK_B` (PA2, shared, input/slave) |
| 23 | FSYNC | `SAI4_FS_B` (PC0, shared, input/slave) |
| 24 | DREG | 1.5 V digital core reg output → **1 µF to GND at pin**, no external supply |
| EPAD | Thermal Pad / exposed pad (VSS) | `GND` — direct to plane (device ground; labeled "EPAD"/EP on the KiCad symbol) |

---

## 5. Shared TDM bus (both codecs on one SDOUT)

Both codecs are ASI **slaves**: `BCLK`/`FSYNC` are inputs driven by the MCU SAI4_B master (`pin-allocation.md` §1). Both `SDOUT` pins tie to the single shared net `SAI4_SD_B` → PA0.

- **Slot map:** ADC-A drives slots **0–3**, ADC-B drives slots **4–7** (`CHx_SLOT`, P0_R11–R18). 8 slots × 32-bit × 32 kHz → **8.192 MHz BCLK** (= 256 × fs, TI's characterisation ratio).
- **Bus contention:** each device **tri-states the slots it does not own** — `ASI_OUT_CH_EN` per channel, plus `TX_FILL` (`ASI_CFG0` bit 0) = 1 for Hi-Z on unused cycles. Enable both on both devices so only the owning device drives each slot; the rest of the frame is high-Z.
- **Bus keeper is internal.** `TX_KEEPER` (`ASI_CFG1` bits 6:5) enables an on-chip keeper on SDOUT that holds the last driven value — settings 2/3 restrict it to the LSB window so the host latches the final bit cleanly without two devices contending at a slot boundary. `TX_LSB` and `TX_OFFSET` in the same register fine-tune the handoff. **No external bus-hold part is needed** (SBAA383C §3.1).
- **Optional:** a single **weak pull-down (~100 kΩ, DNP)** footprint on `SDOUT_ADC` as insurance for the power-up window before either device is configured. Given the internal keeper this is belt-and-suspenders — populate only if a logic-analyzer capture shows bus float. ⚠
- Keep `BCLK_ADC` / `FSYNC_ADC` short and away from the analog inputs (board plan Phase 3).

---

## 6. I²C addressing

Control bus = **I2C1** (PB8 SCL / PB9 SDA), the two codecs only (the PCM5102A DAC is strap-configured, not on I²C — `dac-selection.md`). One pair of pull-ups (2.2–4.7 kΩ) to IOVDD for the whole bus.

The 7-bit address is set by the **ADDR0 (pin 16)** and **ADDR1 (pin 15)** strap pins. The two devices must strap to **distinct addresses** — e.g. ADC-A and ADC-B differ in the ADDR0/ADDR1 tie (GND vs. IOVDD, and the further SDA/SCL-referenced options the part allows).

⚠ **Take the exact strap→address table from SBAS892A at entry** and confirm the two devices' straps (ADC-A: ADDR0+ADDR1→GND; ADC-B: ADDR0→IOVDD, ADDR1→GND) land on two non-conflicting addresses; verify no clash with any other I²C device. (Not transcribing specific hex here — memory is not trustworthy for the address map; this is a review-gate item.)

---

## 7. Power & decoupling (per device)

| Rail / pin | Source | Decoupling |
|---|---|---|
| AVDD (1) | `3V3_A` (clean analog LDO — critical for ADC performance) | 0.1 µF at pin + shared 10 µF bulk on 3V3_A near the pair |
| AREG (2) | internal 1.8 V reg (3.3 V AVDD mode) | 1 µF to AVSS at pin (no external feed) ⚠ |
| VREF (3) | internal reference | ≥ 1 µF to AVSS at pin |
| DREG (24) | internal 1.5 V core reg | 1 µF to GND at pin (no external feed) |
| IOVDD (19) | **`3V45_D`** (recommended ⚠) | 0.1 µF at pin |
| MICBIAS (5) | internal reg (VREF×1.096 = 3.014 V) | 1 µF to AVSS at pin; feeds 4 buffer rails via the pickup connector, no series resistor. **Budget: 4 buffers < 20 mA total/device** (30 mA OCP) ⚠ |

**IOVDD source — OPEN (§11).** IOVDD only powers the digital I/O (BCLK/FSYNC/SDOUT/I²C). Recommendation: feed it from **`3V45_D`** (the digital rail), not `3V3_A`, to keep SDOUT/BCLK switching current *out of* the low-noise analog LDO — the same reasoning that put the DAC's DVDD on the digital rail (`dac-selection.md` §6). 3.45 V is within IOVDD's 3.0–3.6 V window, and it matches the MCU's I/O rail exactly, so logic levels are clean in both directions. AVDD stays on `3V3_A`. ⚠ confirm at the gate. (Alternative: IOVDD on `3V3_A` — one rail into the island, simpler routing, at the cost of digital current on the analog LDO.)

**Output caps vs. supply decoupling.** Only **AVDD** and **IOVDD** are supply inputs (0.1 µF decoupling + shared 10 µF bulk on AVDD). **AREG, DREG, VREF, MICBIAS are internal regulator/reference *outputs*** — their caps are **mandatory** output/stability capacitors, not droppable bulk: VREF ≥ 1 µF is datasheet-required (also sets reference settling), AREG and DREG are the on-chip analog/digital-core LDO outputs (loop stability — 1 µF per the TI EVM/typical app; ⚠ confirm exact min if minimizing), and MICBIAS 1 µF sets its 1.6 µVRMS noise spec and reservoirs the preamp current. None can be removed for part-count.

**Grounding:** single GND net board-wide (AVSS pin 4 + thermal pad both direct to the plane, per datasheet). Zoning is by placement + the 3V3_A pour, not split ground nets — matches the DAC section and the board plan's solid-plane rule.

---

## 8. Register settings that are load-bearing on hardware values

**Full register configuration, SAI setup, and bring-up order live in
`adc-firmware-init.md`** — that document is the single owner. Listed here are
only the settings whose value is *chosen by a hardware decision in this
document*, so that changing one and not the other is visible.

- **Input impedance:** `CHx_IMP` = **20 kΩ (10)** — must match the §2 corner
  calculation. The 2.5 kΩ default moves the corner to ~13.5 Hz.
- **Coupling-cap charge:** raise `INCAP_QCHG` (P0_R5_D[5:4]) for the 4.7 µF
  blocking caps (the default window assumes ≤ 1 µF).
- **Input source / coupling:** `CHx_INSRC = 01` (single-ended), `CHx_DC = 0`
  (AC-coupled) — these are what make the §1 "single-ended AC-coupled" topology,
  including the INxM matching-cap requirement, correct.
- **MICBIAS:** `MBIAS_VAL = 001` → 3.014 V, the value assumed by §1, §7 and the
  buffer supply budget. Requires `ADC_FSCALE = 00`.
- **Full scale / VREF:** `ADC_FSCALE = 00` → VREF 2.75 V → 1 Vrms single-ended
  full scale; needs AVDD ≥ 3.0 V, met by `3V3_A`. If VREF's cap is ever raised
  above 1 µF, `VREF_QCHG` must follow (§4 pin 3).
- **Slot map and tri-state** per §5.

### Defaults that must be defeated ⚠

The ADC5140 is a far-field voice capture part. Three of its automatic features
default **on** and are wrong for this application — none of them announces
itself, so a board that works will simply be missing the low-frequency content
the design exists to capture:

- **Digital HPF — default ENABLED, −3 dB at 8 Hz at this design's sample rate.**
  See below; this is the one setting that must be got right, because it is the
  only low-frequency loss in the chain that no downstream correction can undo.
- **AGC — must be off.** Deterministic gain is required for feature extraction.
- **DRE — off initially.** Automatic gain shifting means level nondeterminism.

### The digital high-pass filter ⚠

**The corners scale with sample rate, and the datasheet tabulates them at 16 kHz
and 48 kHz.** This design runs 32 kHz (§5), so neither published column applies
directly. `HPF_SEL[1:0]` at `P0_R107` (SBAS892A §8.3.6.4, Table 16):

| `HPF_SEL[1:0]` | Setting | −3 dB at 32 kHz |
|---|---|---|
| `00` | programmable 1st-order IIR | as programmed; **flat by default** |
| `01` (default) | 0.00025 × fs | **8 Hz** |
| `10` | 0.002 × fs | 64 Hz |
| `11` | 0.008 × fs | 256 Hz |

> An earlier revision of this section gave the default as 12 Hz. That is the
> 48 kHz figure read from the datasheet's table without scaling. The conclusion
> is unchanged — 8 Hz still sits far above the 1.7 Hz corner §2 goes to trouble
> to achieve — but the number was wrong.

**Setting `HPF_SEL = 00` is a true bypass, not an approximation.** It hands the
filter to the programmable first-order IIR, whose *default* coefficients
(`N0 = 0x7FFFFFFF`, `N1 = 0`, `D1 = 0`) the datasheet states are flat at 0 dB —
all-pass. No coefficient arithmetic is required to defeat the filter.

**Specify a programmed corner at 0.5 Hz rather than a bypass.** Flat leaves the
converter's own residual DC offset in the stream, where the low-frequency
correction of `analog-front-end.md` §6.2 would amplify it. A 0.5 Hz corner sits
below the analysis band and below the processor's own DC removal, while still
bounding the offset before anything applies gain to it. Coefficients follow from
the transfer function `H(z) = (N0 + N1·z⁻¹) / (2³¹ − D1·z⁻¹)` with a pole at
`a = exp(−2π·fc/fs)`, giving `N0 = D1 = a·2³¹` and `N1 = −N0`:

| Corner at 32 kHz | `N0` = `D1` | `N1` |
|---|---|---|
| 0.2 Hz | `0x7FFEB696` | `0x8001496A` |
| **0.5 Hz (specify)** | **`0x7FFCC87E`** | **`0x80033782`** |
| 1.0 Hz | `0x7FF99110` | `0x80066EF0` |

The 32-bit coefficients resolve the corner to a few microhertz, so quantisation
is not a consideration at these frequencies. ⚠ Confirm the sign convention of
the denominator term against SBAS892A Equation 1 and TI's biquad application
report before writing — the coefficient registers are at `P4_R72–R83`.

**Three properties of this filter constrain the driver, not the board:**

- It is **global, not per-channel** — one setting covers all four channels of a
  device, which suits eight identical string channels but means it cannot be
  used to treat one differently.
- It must be programmed **per device**. Both codecs need it.
- With `HPF_SEL = 00` the coefficients must be written **before powering up any
  ADC channel for recording** (SBAS892A §8.3.6.4). This is a bring-up ordering
  constraint, not a runtime adjustment, and belongs in the driver's
  initialisation sequence.

### The programmable biquads are deliberately left flat

The device offers twelve programmable biquads, defaulting to all-pass. They are
**not** used for the low-frequency correction, because their output is the
single stream from which both the audio path and the analysis path derive, and
the correction belongs on the analysis branch alone (`analog-front-end.md`
§6.2). No register change is required to leave them flat.

**The allocation default needs no change either, but the reason is worth
recording** so it is not re-derived wrongly. `BIQUAD_CFG[1:0]` at `P0_R108`
defaults to `2'b10` — two biquads per channel, supporting up to six channels
(SBAS892A Table 18). That six is a count of *one device's* output channels, and
each device here drives four (§5). The eight channels of this design are four
per device across two devices, so the default accommodates them with a biquad to
spare. **The six-channel limit does not bite.** It would only apply if a single
device were asked to produce more than six output channels through its internal
mixer.

Final DC removal happens in the DSP at ~0.2–0.5 Hz, not in the converter
(`adc-firmware-init.md` §7).

---

## 9. Test points

See `test-points.md` (single source of truth; categorized by access type). Codec-side signals: `BCLK_ADC`/`FSYNC_ADC`/`SDOUT_ADC` (SAI4 bus) are Cat 2 probe pads; `I2C_SCL`/`I2C_SDA`, `CODEC_SHDNZ`, `MICBIAS_A`/`MICBIAS_B`, and the per-device input line are Cat 3 (touch at a passive).

---

## 10. BOM (codec section)

| Item | Value / Part | Package | LCSC | Notes |
|---|---|---|---|---|
| ADC codecs (×2) | TLV320ADC5140 | 24-WQFN 4×4 (RTW) | pick | ⚠ confirm LCSC stock at order (board plan risk register) |
| INxP blocking caps (×8) | 4.7 µF **tantalum**, **16 V or 25 V**, blocking (INxP) | pick | pick | **+ toward the converter** (§2 — converter side is higher by 375 mV on every channel); 4.7 µF sets ~1.7 Hz corner for near-DC finger-pressure sensing; heavy voltage derating is tantalum practice, do not fit 6.3 V |
| INxP clamp diodes (×8) | small-signal silicon switching diode | SOD-323 or smaller | pick | Parallel with each blocking cap, **cathode toward the converter**. Covers the power-sequencing window only (§2). Silicon not Schottky — leakage into a 20 kΩ low-level node matters, clamp voltage does not |
| INxM matching caps (×8) | 1 µF **X7R** preferred (4.7 µF as drawn OK), matching (INxM→GND) | 0402/0603 | basic | not signal-carrying; reconcile value doc↔schematic |
| AVDD decouplers (×2) | 0.1 µF X7R | 0402 | basic | AVDD at pin |
| IOVDD decouplers (×2) | 0.1 µF X7R | 0402 | basic | IOVDD at pin |
| AREG caps (×2) | 1 µF X7R | 0402/0603 | basic | AREG to AVSS |
| VREF caps (×2) | 1 µF X7R | 0402/0603 | basic | VREF to AVSS |
| DREG caps (×2) | 1 µF X7R | 0402/0603 | basic | DREG to GND |
| AVDD/3V3_A bulk (×1–2) | 10 µF X7R ≥10 V | 0805 | basic | shared AVDD/3V3_A bulk near the pair |
| MICBIAS caps (×2) | 1 µF X7R | 0402/0603 | basic | MICBIAS decoupling to AVSS (preamp supply — **populated**) |
| I²C pull-ups (SCL/SDA) | 2.2–4.7 kΩ | 0402 | basic | I²C pull-ups to IOVDD (one pair for the bus) |
| SHDNZ pull-down | 10 kΩ | 0402 | basic | SHDNZ pull-down (entered, shared, on MCU sheet) |
| ADDR straps (×?) | per address strap | 0402 | basic | ADDR0/ADDR1 straps — value/tie per §6 table ⚠ |
| RF shunt caps (×8) | 100–330 pF | 0402 | — | **DNP** optional RF shunt at each buffer signal line (external cable entry) |
| SDOUT bus pull-down | 100 kΩ | 0402 | — | **DNP** optional SDOUT bus pull-down |

Passives JLCPCB basic-class; LCSC codes at order time.

---

## 11. Netlist-gate verification checklist

Part and topology are settled (`adc-selection.md`); these are datasheet confirmations, value picks, and bench characterizations.

1. **Input impedance `CHx_IMP` — decided: 20 kΩ** (≈1.7 Hz corner at 4.7 µF), taken because it is free rather than because the corner has to be that low — see the note in §2 on what the corner is and is not for. (Source loading no longer enters this choice.) 10 kΩ (≈3.4 Hz) is the documented fallback if bench work ever shows the extra dynamic range is worth the higher corner. Firmware register setting must match (§8).
2. **Signal-cap tantalum polarity — RESOLVED, no open action.** The converter self-biases its AC-coupled inputs to VREF/2 ≈ 1.375 V; the preamp presents a divider-set 1.0 V. The converter side is higher by 375 mV on every channel, so **+ toward the converter** and the sign cannot invert. Full argument, including the bias-point selection rule, is in §2. ⚠ **The sequencing exposure is now wider, not narrower.** The preamp boards take the 3.3 V analog rail rather than MICBIAS, so they no longer come up strictly after the converter — the firmware ordering that previously closed this window does not apply. The parallel silicon clamp diode is what covers it and is required. **Bench items:** measure the DC on one input pin and confirm it sits near 1.375 V (the number comes from TI application material rather than the datasheet), and confirm the preamp side sits at 1.0 V on every channel (`preamp-board.md` §12 item 4).
3. **IOVDD source — decided: `3V45_D`** (keeps codec digital switching current off the analog LDO, and matches the MCU I/O rail so logic levels are clean both directions). Entered as such. ⚠ Remaining check is a datasheet one: confirm 3.45 V + rail tolerance sits inside IOVDD's recommended-operating window (3.0–3.6 V nominal) — see `layout-notes.md` §7 item 3.
4. **I²C addresses** — take the ADDR0/ADDR1 strap→address table from SBAS892A; confirm the drawn straps (ADC-A: GND/GND, ADC-B: IOVDD/GND) give distinct, non-conflicting addresses; check no bus clash. ⚠
5. **SDOUT bus discipline** — confirm both devices' unused-slot tri-state (`ASI_OUT_CH_EN`) and `TX_FILL` = Hi-Z are set, and pick a `TX_KEEPER` setting (2 or 3 = keeper during the LSB window only, per SBAA383C). The internal keeper covers steady-state contention, so the optional 100 kΩ SDOUT pull-down is a DNP footprint for the pre-configuration window only — decide whether to populate.
6. **AREG treatment** — confirm AREG decoupling / that it is *not* externally supplied in 3.3 V AVDD mode (AREG abs-max 2.0 V — never tie to 3V3_A). ⚠
7. **SHDNZ strap** — shared pull-down value and whether a per-codec reset split is wanted for bring-up (`pin-allocation.md` §4 PC7 spare). ⚠
8. **Coupling-cap charge (`INCAP_QCHG`)** — firmware must set it for 4.7 µF; note in the driver bring-up.
9. **Gain characterization — the level dispute is settled by measurement, no longer open.** The coil measures 40 mV peak-to-peak, which the preamp's gain of ~8 delivers as ≈320 mV peak-to-peak, roughly 17 dB below full scale (`analog-front-end.md` §1). Both earlier figures in the project record — the ≈12 mVrms sizing here and the hotter assumption from the preamp thread — were estimates against a unity front end that no longer exists. ⚠ **Remaining action:** set PGA and digital gain against the measured level and verify no clip at full scale. The requirement is far smaller than originally specified, and whether the Dynamic Range Enhancer still has a role should be reconsidered at the same time (`adc-firmware-init.md`).
10. **MICBIAS — no longer used, no budget to verify.** The preamp boards take the 3.3 V analog rail (§1, `analog-front-end.md` §4). MICBIAS may be left unconfigured. If it is ever brought back, note the load is now ~3.1 mA per board against the 20 mA per-device limit rather than the sub-milliamp figure that applied to followers.
11. **Cable protection** — the supply rail and the per-channel signal lines are external-cable entries; decide whether they need series ferrite / ESD clamp / the optional RF shunt cap. ⚠ Note the signal lines now carry ~320 mV peak-to-peak from an ohms-level source rather than tens of millivolts from kilohms, which materially reduces the ingress exposure this item was written against.
12. **Digital high-pass filter — decided: programmed corner at 0.5 Hz** via `HPF_SEL = 00` and the coefficients in §8. This is the only low-frequency loss in the chain that no downstream correction can undo, so it is the one firmware setting the analog low-frequency argument actually depends on. ⚠ **Remaining checks, all datasheet or bring-up rather than board:** confirm the denominator sign convention of SBAS892A Equation 1 before writing coefficients; confirm the driver writes them **before** powering up any record channel; confirm both devices are programmed. **Bench item:** verify the corner landed by sweeping a low-frequency tone into one channel and reading the captured level — a filter left at its 8 Hz default will pass a working board that is silently missing the content the design exists to capture.
13. **Biquad allocation — no action, recorded to prevent a wrong correction.** `BIQUAD_CFG[1:0]`'s default allocation supports six output channels *per device*, and each device drives four. The default stands. The biquads are left flat by design (§8).
14. **Auto-clock derivation at 32 kHz — RESOLVED (2026-07-28).** The scheme *is* table-based (SBAS892A §8.3.2, Table 6: supported FSYNC frequencies × BCLK-to-FSYNC ratios) and **32 kHz FSYNC at ratio 256 → 8.192 MHz BCLK is an explicitly listed, supported combination**. The auto-configuration block detects FSYNC frequency and BCLK ratio and sets every internal divider plus the PLL with no host programming; an unsupported combination raises an ASI clock-error interrupt and mutes the record channels (status in `ASI_STS`, P0_R21 — worth reading during bring-up as a clock-health check).

---

*Schematic-entry status.* Entered and verified: all 8 input channels (4.7 µF polarized blocking caps → INxP, incl. the ADC-B IN4M matching cap), AREG/VREF/DREG/MICBIAS 1 µF caps, distinct ADDR straps (ADC-A: ADDR0+ADDR1→GND; ADC-B: ADDR0→IOVDD, ADDR1→GND — resistor values unset), IOVDD on `3V45_D`, shared TDM bus, SHDNZ to PC6 with a 10 k pull-down. ⚠ **The entered schematic feeds the preamp boards from MICBIAS and must be rewired to the 3.3 V analog rail** (§1) — a one-net change per board, plus the connector's power pin. Each INxP blocking cap carries a **parallel silicon clamp diode** — a stated design element with its rationale in §2, not an entry-time addition. Single-polarity clamp is correct and intended. ⚠ Confirm orientation at review: **cathode toward the converter input**, which is the normally-higher-DC side (~1.375 V against the preamp's 1.0 V), so the diode sits reverse-biased by ~0.375 V in normal operation. The orientation is unchanged from entry; only the margin is smaller. **Not yet entered:** per-pin 0.1 µF AVDD/IOVDD decoupling + 10 µF bulk, I2C pull-up values (pull-ups present, values unset), ADDR strap resistor values. **To reconcile:** INxM matching caps drawn at 4.7 µF vs. 1 µF preferred in §2 (either fine — make doc and schematic agree); **part value entered as "XLV320ADC5140IRTWR" (both ADCs) — typo for TLV, will corrupt BOM lookup.**
