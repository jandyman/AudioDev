# Codec (ADC) Section — Netlist + BOM

**Status:** Draft for schematic entry (started 2026-07-14). Implements the codec section of Phase 2 in `multichannel-audio-board-plan.md`; consumes the SAI/I2C/GPIO allocation from `pin-allocation.md` §1–§4 and the `3V3_A` / `3V45_D` rails from `power-supply-netlist.md`. Connections are given **by pin name** — take pin *numbers* from the KiCad symbol / datasheet at entry, don't trust memory. Items marked ⚠ go on the netlist-review-gate checklist. Datasheet: TI **SBAS892A** (TLV320ADC5140), 24-pin WQFN.

**Scope:** two TLV320ADC5140 codecs, each configured as **4× single-ended, AC-coupled** analog inputs → 8 channels on one shared TDM bus into `SAI4_B` (RX). Analog input conditioning, coupling/blocking caps, shared clock/data bus, distinct I²C addresses, per-device power + decoupling. The stereo DAC (`I2S1` TX) is a separate section — see `dac-selection.md`.

---

## 1. Design inputs (confirmed with user 2026-07-14)

- **Source per channel:** low-impedance magnetic pickups, each **buffered at the pickup by a JFET source-follower**. Buffer output impedance is known and low, **~1 kΩ**. Signal level is **< 0.1 V peak-to-peak** (≈ 35 mVpp ≈ 12 mVrms) — roughly **30–40 dB below** the ADC's single-ended full scale.
- **Gain:** the required gain is not yet known and is deliberately handled **inside the ADC5140** (analog channel PGA + digital channel volume, optionally DRE up to 24 dB). Flexible in-device gain was a **primary reason for choosing this part**. The analog board path stays **unity** — no external gain stage; all level-setting is a register choice, characterized once the buffer output level is measured.
- **Preamp powering:** each pickup preamp is powered from the codec's **MICBIAS** output used as a **supply rail**. The four JFET source-follower buffers are designed to run directly off a rail, so MICBIAS feeds their Vdd **directly — no series load resistor**. Wiring is **multi-conductor** (one MICBIAS power line + one signal line per channel + ground) through a per-device connector (`J1` for ADC-A, `J2` for ADC-B): MICBIAS on one conductor powers all four buffers, and each buffer's audio returns on its own signal conductor, AC-coupled into `INxP`. **MICBIAS = 3.014 V** (VREF×1.096, `MBIAS_VAL = 001`), regulated, 1.6 µVRMS noise, up to **20 mA per device** (30 mA over-current trip) — the four buffers' combined supply current must stay inside that budget (§11). Each device's MICBIAS powers **its own 4 buffers only** — the two MICBIAS outputs are **never tied together** (separate regulators).
- **Coupling:** **AC-coupled** to reject each buffer's DC output bias while passing near-DC audio. **Signal blocking cap (INxP) = 4.7 µF tantalum** — sized to push the high-pass corner as low as practical (~1.7 Hz at 20 kΩ input impedance) so the **onset transient of finger pressure** on the string is captured; see §2. It taps the buffer's signal line into INxP. **Matching cap (INxM) = 1 µF X7R preferred** (the 4.7 µF currently drawn is also fine — it carries no signal; see §2).
- **Channels:** all 8 identical single-ended AC-coupled, MICBIAS-powered, unless a per-channel exception is called out later.

### Why single-ended AC-coupled here (datasheet basis, SBAS892A §8.3.3)

Each ADC5140 has four `INxP`/`INxM` analog pin pairs. In single-ended mode (`CHx_INSRC = 01`) the signal enters **INxP through the blocking cap**, and **INxM is grounded through a matching cap** — *not* directly to ground (Fig. 37). The INxM cap is required because the front end is internally differential and biased to an internal common-mode; a hard ground on INxM would fight that bias. Four pairs → **4 single-ended channels per device**, ×2 devices = **8 channels**, matching the board plan.

---

## 2. Input stage — coupling caps, impedance, corner

The high-pass corner is set by the blocking cap and the **programmable input impedance** `CHx_IMP` (2.5 k default / 10 k / 20 k, I²C-selectable per channel, SBAS892A Table 9), not by an external resistor:

```
fc(-3dB) = 1 / (2π · R_imp · C_in)
```

With **C_in = 4.7 µF** fixed, the impedance setting directly picks the corner and also sets how hard the 1 kΩ buffer is loaded:

| `CHx_IMP` | Corner @ 4.7 µF | Buffer loading (1 kΩ src) | Noise / DR |
|---|---|---|---|
| 2.5 kΩ | ~13.5 Hz | ÷ = 0.71 → **−3.0 dB** | lowest noise |
| 10 kΩ | ~3.4 Hz | ÷ = 0.91 → −0.83 dB | slightly higher |
| **20 kΩ (recommended)** | **~1.7 Hz** | ÷ = 0.95 → −0.4 dB | slightly higher still |

> **Rail-powered note.** Because the buffers are powered from a **dedicated MICBIAS rail** (no per-channel load resistor), each input is driven only by the buffer's ~1 kΩ output impedance — there is no `RL` shunt loading the signal. The corner is set by `C_in` and `R_imp` alone; the ~1 kΩ source merely adds ~1 kΩ in series (negligible against a 20 kΩ `R_imp`), so passband level and corner are essentially the ideal RC values in the table above.

**Recommendation: 20 kΩ.** The design goal is **near-DC response to capture the onset transient of finger pressure**, so the lowest available corner wins: 20 kΩ × 4.7 µF ≈ **1.7 Hz**, the nearest-DC option for the chosen cap, and it loads the JFET buffer the lightest. The "slightly higher noise" of the 20 kΩ setting is immaterial against a buffered source that is gained up in-device, and the ADC's own converter noise dominates. Note the front end is inherently AC-coupled, so a *sustained* (true-DC) press is blocked regardless — what passes is the pressure **transient/attack**, whose spectral content sits well above 1.7 Hz, so the low corner captures the onset, which is the sensing target. **10 kΩ** (~3.4 Hz) is only a fallback if a touch more dynamic range is ever wanted. ⚠ **user-confirm** — §11 item 1.

**Blocking-cap charge time.** 4.7 µF exceeds the device's default coupling-cap quick-charge window (default sized for **≤ 1 µF**). No hardware cost — firmware raises `INCAP_QCHG` (P0_R5_D[5:4]) so the caps charge to the common-mode at power-up without a long settle (SBAS892A §8.3.3). Captured in §8.

**Matching cap (INxM) = 1 µF X7R preferred; 4.7 µF as currently drawn is also acceptable.** INxM carries no signal (it's only the AC-ground reference for the internally-differential front end), so its value does not enter the signal transfer — the passband and the ~1.7 Hz corner are set entirely by the INxP cap. At **4.7 µF** it simply matches the signal cap and gives the best low-frequency common-mode reference (its own AC-ground corner also ~1.7 Hz). At **1 µF** that node's AC-ground corner rises to ~8 Hz (at 20 k `R_imp`), slightly reducing common-mode rejection below ~8 Hz — subsonic, negligible common-mode content from instrument pickups, so **inaudible** — in exchange for a smaller/cheaper part. X7R is fine either way (low swing). **The schematic currently uses 4.7 µF (C15/C16/C17/C9 on ADC-A, and the ADC-B set);** pick one value and make doc + schematic agree.

**Signal blocking-cap dielectric = 4.7 µF tantalum (decided).** Distortion is not a concern — the AC swing across the cap is tiny (< 0.1 Vpp), so tantalum's voltage-coefficient / dielectric-absorption artifacts are negligible (same reasoning as the X7R M-cap). **The one real caveat is polarity / reverse voltage** (⚠ §11): the tantalum sees the DC difference between the **buffer's output bias** (signal-line side) and INxP's internal common-mode, and a tantalum can fail *short* if reverse-biased even momentarily — e.g. at power-up or with MICBIAS off, one side can sit at 0 V while the other is positive. Confirm which side is higher and that it never reverses across all power states (power-up/down, MICBIAS gated off); orient the tantalum accordingly, or substitute a non-polar part if the sign can't be guaranteed.

**EMI / anti-alias.** The ADC5140 is a sigma-delta with internal anti-alias; no external AA filter is needed. Provide an **optional shunt cap footprint (~100–330 pF, DNP)** from each INxP to AVSS for RF immunity, populated only if bench testing shows a need. No series resistor — it would shift the corner and add noise into a low-level path.

---

## 3. Nets

| Net | Description |
|---|---|
| `IN1_SIG`…`IN8_SIG` | Per-channel buffer signal lines (from the `J1`/`J2` connectors): each JFET buffer's audio output → blocking cap → INxP. Buffers are powered separately from the MICBIAS rail |
| `MICBIAS_A` / `MICBIAS_B` | Per-device buffer supply rail (3.014 V) — feeds that device's 4 buffers directly through connector `J1`/`J2`, no series resistor; **not** interconnected |
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

Refs: **U3 = ADC-A**, **U4 = ADC-B**. Pin numbers per the 24-WQFN pinout (SBAS892A pin table).

| Pin | Name | Net / connection |
|---|---|---|
| 1 | AVDD | `3V3_A` + 0.1 µF to GND at pin; 10 µF bulk shared on the 3V3_A pour near the device |
| 2 | AREG | on-chip 1.8 V analog reg output (AVDD = 3.3 V mode) → **1 µF to AVSS at pin**, no external supply ⚠ |
| 3 | VREF | **1 µF to AVSS at pin** (min per §8.3.4). Larger cap ⇒ raise `VREF_QCHG` |
| 4 | AVSS | `GND` (direct to plane) |
| 5 | MICBIAS | `MICBIAS_A`/`MICBIAS_B` — buffer supply rail. **1 µF to AVSS at pin** (sets the 1.6 µVRMS noise spec); routes to this device's 4 buffer rails via connector `J1`/`J2`, **no series resistor**. `MBIAS_VAL = 001` → 3.014 V, powered on via `MICBIAS_PDZ` |
| 6 | IN1P_GPI1 | from buffer-1 signal line via **C_in 4.7 µF tantalum** blocking cap (GPI1 disabled — analog SE input) ⚠ polarity |
| 7 | IN1M_GPO1 | **1 µF X7R to GND** (matching cap; single-ended AC-coupled per Fig. 37; 4.7 µF as drawn) |
| 8 | IN2P_GPI2 | from buffer-2 signal line via 4.7 µF tantalum |
| 9 | IN2M_GPO2 | 1 µF X7R to GND (4.7 µF as drawn) |
| 10 | IN3P_GPI3 | from buffer-3 signal line via 4.7 µF tantalum |
| 11 | IN3M_GPO3 | 1 µF X7R to GND (4.7 µF as drawn) |
| 12 | IN4P_GPI4 | from buffer-4 signal line via 4.7 µF tantalum |
| 13 | IN4M_GPO4 | 1 µF X7R to GND (4.7 µF as drawn) — ⚠ **U4 (ADC-B) IN4M cap missing in schematic** |
| 14 | SHDNZ | `CODEC_SHDNZ` (MCU PC6, shared); 10 kΩ pull-down to GND (R18, on the MCU sheet) holds the part in reset until the MCU drives it |
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

- **Slot map:** ADC-A drives slots **0–3**, ADC-B drives slots **4–7** (`CHx_SLOT`, P0_R11–R18). 8 slots × 32-bit × 48 kHz → ~12.288 MHz BCLK.
- **Bus contention:** each device **tri-states the slots it does not own** (SBAS892A: "tri-state feature for the unused audio data slots"). Enable tri-state on both so only the owning device drives each slot; the rest of the frame is high-Z. No hard external bus keeper is required.
- **Optional:** a single **weak pull-down (~100 kΩ, DNP)** on `SDOUT_ADC` to define the bus during the brief windows both devices are high-Z (power-up / between slots). Populate only if a logic-analyzer capture shows bus float. ⚠
- Keep `BCLK_ADC` / `FSYNC_ADC` short and away from the analog inputs (board plan Phase 3).

---

## 6. I²C addressing

Control bus = **I2C1** (PB8 SCL / PB9 SDA), the two codecs only (the PCM5102A DAC is strap-configured, not on I²C — `dac-selection.md`). One pair of pull-ups (2.2–4.7 kΩ) to IOVDD for the whole bus.

The 7-bit address is set by the **ADDR0 (pin 16)** and **ADDR1 (pin 15)** strap pins. The two devices must strap to **distinct addresses** — e.g. ADC-A and ADC-B differ in the ADDR0/ADDR1 tie (GND vs. IOVDD, and the further SDA/SCL-referenced options the part allows).

⚠ **Take the exact strap→address table from SBAS892A at entry** and confirm U3/U4's straps (U3: ADDR0+ADDR1→GND; U4: ADDR0→IOVDD, ADDR1→GND) land on two non-conflicting addresses; verify no clash with any other I²C device. (Not transcribing specific hex here — memory is not trustworthy for the address map; this is a review-gate item.)

---

## 7. Power & decoupling (per device)

| Rail / pin | Source | Decoupling |
|---|---|---|
| AVDD (1) | `3V3_A` (clean analog LDO — critical for ADC performance) | 0.1 µF at pin + shared 10 µF bulk on 3V3_A near the pair |
| AREG (2) | internal 1.8 V reg (3.3 V AVDD mode) | 1 µF to AVSS at pin (no external feed) ⚠ |
| VREF (3) | internal reference | ≥ 1 µF to AVSS at pin |
| DREG (24) | internal 1.5 V core reg | 1 µF to GND at pin (no external feed) |
| IOVDD (19) | **`3V45_D`** (recommended ⚠) | 0.1 µF at pin |
| MICBIAS (5) | internal reg (VREF×1.096 = 3.014 V) | 1 µF to AVSS at pin; feeds 4 buffer rails via `J1`/`J2`, no series resistor. **Budget: 4 buffers < 20 mA total/device** (30 mA OCP) ⚠ |

**IOVDD source — OPEN (§11).** IOVDD only powers the digital I/O (BCLK/FSYNC/SDOUT/I²C). Recommendation: feed it from **`3V45_D`** (the digital rail), not `3V3_A`, to keep SDOUT/BCLK switching current *out of* the low-noise analog LDO — the same reasoning that put the DAC's DVDD on the digital rail (`dac-selection.md` §6). 3.45 V is within IOVDD's 3.0–3.6 V window, and it matches the MCU's I/O rail exactly, so logic levels are clean in both directions. AVDD stays on `3V3_A`. ⚠ confirm at the gate. (Alternative: IOVDD on `3V3_A` — one rail into the island, simpler routing, at the cost of digital current on the analog LDO.)

**Output caps vs. supply decoupling.** Only **AVDD** and **IOVDD** are supply inputs (0.1 µF decoupling + shared 10 µF bulk on AVDD). **AREG, DREG, VREF, MICBIAS are internal regulator/reference *outputs*** — their caps are **mandatory** output/stability capacitors, not droppable bulk: VREF ≥ 1 µF is datasheet-required (also sets reference settling), AREG and DREG are the on-chip analog/digital-core LDO outputs (loop stability — 1 µF per the TI EVM/typical app; ⚠ confirm exact min if minimizing), and MICBIAS 1 µF sets its 1.6 µVRMS noise spec and reservoirs the preamp current. None can be removed for part-count.

**Grounding:** single GND net board-wide (AVSS pin 4 + thermal pad both direct to the plane, per datasheet). Zoning is by placement + the 3V3_A pour, not split ground nets — matches the DAC section and the board plan's solid-plane rule.

---

## 8. Register-configuration notes (firmware, not netlist — recorded so the two stay in sync)

- **Input source:** `CHx_INSRC = 01` (single-ended) for all 4 channels each device (P0_R60/65/70/75 D[6:5]).
- **Coupling:** AC-coupled (leave `CHx_DC = 0`).
- **Input impedance:** `CHx_IMP` = **20 kΩ (10) recommended** — must match the §2 hardware decision.
- **Coupling-cap charge:** raise `INCAP_QCHG` (P0_R5_D[5:4]) for the 4.7 µF caps (> 1 µF default window).
- **Full scale / VREF:** default `ADC_FSCALE = 00` → VREF 2.75 V → **1 Vrms single-ended FS** (needs AVDD ≥ 3.0 V — met by 3V3_A).
- **Gain:** channel PGA + digital volume (+ optional DRE ≤ 24 dB) to lift the sub-0.1 Vpp source; value TBD from measured buffer level.
- **ASI:** TDM mode (`ASI_FORMAT = 00`), 32-bit slots (`ASI_WLEN = 11`), slot map per §5, **unused-slot tri-state enabled** on both devices.
- **MICBIAS:** `MBIAS_VAL = 001` → 3.014 V (VREF×1.096, requires `ADC_FSCALE = 00`); power on via `MICBIAS_PDZ` (P0_R117_D7). Can also be gated on/off directly from GPIO1/GPIx without I²C. Sequence: power MICBIAS up before/with enabling the input channels so the preamps bias and the 4.7 µF blocking caps charge (works alongside `INCAP_QCHG`).

---

## 9. Test points

See `test-points.md` (single source of truth; categorized by access type). Codec-side signals: `BCLK_ADC`/`FSYNC_ADC`/`SDOUT_ADC` (SAI4 bus) are Cat 2 probe pads; `I2C_SCL`/`I2C_SDA`, `CODEC_SHDNZ`, `MICBIAS_A`/`MICBIAS_B`, and the per-device input line are Cat 3 (touch at a passive).

---

## 10. BOM (codec section)

| Ref | Value / Part | Package | LCSC | Notes |
|---|---|---|---|---|
| U3, U4 | TLV320ADC5140 | 24-WQFN 4×4 (RTW) | pick | ⚠ confirm LCSC stock at order (board plan risk register) |
| C_in ×8 | 4.7 µF **tantalum**, blocking (INxP) | pick | pick | ⚠ **polarity/reverse-voltage** (§2/§11); low-swing → distortion non-issue; 4.7 µF sets ~1.7 Hz corner for near-DC finger-pressure sensing |
| C_inm ×8 | 1 µF **X7R** preferred (4.7 µF as drawn OK), matching (INxM→GND) | 0402/0603 | basic | not signal-carrying; reconcile value doc↔schematic |
| C_avdd ×2 | 0.1 µF X7R | 0402 | basic | AVDD at pin |
| C_iovdd ×2 | 0.1 µF X7R | 0402 | basic | IOVDD at pin |
| C_areg ×2 | 1 µF X7R | 0402/0603 | basic | AREG to AVSS |
| C_vref ×2 | 1 µF X7R | 0402/0603 | basic | VREF to AVSS |
| C_dreg ×2 | 1 µF X7R | 0402/0603 | basic | DREG to GND |
| C_bulk ×1–2 | 10 µF X7R ≥10 V | 0805 | basic | shared AVDD/3V3_A bulk near the pair |
| C_micbias ×2 | 1 µF X7R | 0402/0603 | basic | MICBIAS decoupling to AVSS (preamp supply — **populated**) |
| R_scl, R_sda | 2.2–4.7 kΩ | 0402 | basic | I²C pull-ups to IOVDD (one pair for the bus) |
| R_shdnz | 10 kΩ | 0402 | basic | SHDNZ pull-down R18 (entered, shared, on MCU sheet) |
| R_addr ×? | per address strap | 0402 | basic | ADDR0/ADDR1 straps — value/tie per §6 table ⚠ |
| C_emi ×8 | 100–330 pF | 0402 | — | **DNP** optional RF shunt at each buffer signal line (external cable entry) |
| R_sdout | 100 kΩ | 0402 | — | **DNP** optional SDOUT bus pull-down |

Passives JLCPCB basic-class; C-numbers at order time.

---

## 11. Open items / netlist-gate checklist additions

1. **Input impedance `CHx_IMP`** — **20 kΩ (≈1.7 Hz corner) recommended** to meet the near-DC finger-pressure goal; 10 kΩ (≈3.4 Hz) only if more dynamic range is wanted. ⚠ user-confirm; must match the register setting.
2. **Signal-cap tantalum polarity** (dielectric decided: 4.7 µF tantalum on INxP, 1 µF/4.7 µF X7R on INxM) — confirm the DC across each INxP tantalum (**buffer output bias** vs. internal common-mode) and that it **never reverses** across power-up/down and MICBIAS-off; orient `+` to the higher side, or use a non-polar part if the sign can't be guaranteed. Needs the ADC5140 input common-mode voltage (datasheet/EVM) + the buffer output bias. ⚠
3. **IOVDD source** — `3V45_D` (recommended, keeps digital current off analog LDO) vs. `3V3_A`. ⚠ confirm at gate.
4. **I²C addresses** — take the ADDR0/ADDR1 strap→address table from SBAS892A; confirm the drawn straps (U3: GND/GND, U4: IOVDD/GND) give distinct, non-conflicting addresses; check no bus clash. ⚠
5. **SDOUT bus discipline** — confirm both devices' unused-slot tri-state is enabled; decide whether to populate the optional 100 kΩ SDOUT pull-down. ⚠
6. **AREG treatment** — confirm AREG decoupling / that it is *not* externally supplied in 3.3 V AVDD mode (AREG abs-max 2.0 V — never tie to 3V3_A). ⚠
7. **SHDNZ strap** — shared pull-down value and whether a per-codec reset split is wanted for bring-up (`pin-allocation.md` §4 PC7 spare). ⚠
8. **Coupling-cap charge (`INCAP_QCHG`)** — firmware must set it for 4.7 µF; note in the driver bring-up.
9. **Gain characterization** — measure JFET-buffer output level, then set PGA/digital/DRE gain; verify no clip at 1 Vrms FS.
10. **MICBIAS supply-current budget** — the JFET buffers now run directly off the MICBIAS rail (no `RL`, they are designed to run off a rail); confirm the 4 buffers' combined supply current stays **< 20 mA/device** (30 mA OCP). ⚠
11. **Cable protection** — the MICBIAS rail and the per-channel signal lines are external-cable entries; decide whether they need series ferrite / ESD clamp / the optional RF shunt cap. ⚠

---

*Schematic-entry status.* Entered and verified: all 8 input channels (4.7 µF polarized blocking caps → INxP, incl. U4 IN4M matching cap), AREG/VREF/DREG/MICBIAS 1 µF caps, distinct ADDR straps (U3: ADDR0+ADDR1→GND; U4: ADDR0→IOVDD, ADDR1→GND — resistor values unset), IOVDD on `3V45_D`, shared TDM bus, SHDNZ to PC6 with R18 10 k pull-down. MICBIAS rails are the auto-named connector nets `Net-(J1-Pin_1)`/`Net-(J2-Pin_1)` feeding the buffers directly through J1/J2 (no series RL — the JFET buffers are designed to run off a rail; confirmed U3 pin 5 → C35 1 µF + J1, U4 pin 5 → C36 1 µF + J2). **Not yet entered:** per-pin 0.1 µF AVDD/IOVDD decoupling + 10 µF bulk, I2C pull-up values (R1/R2 present, values unset), ADDR strap resistor values. **To reconcile:** INxM matching caps drawn at 4.7 µF vs. 1 µF preferred in §2 (either fine — make doc and schematic agree); **part value entered as "XLV320ADC5140IRTWR" (both U3/U4) — typo for TLV, will corrupt BOM lookup.**
