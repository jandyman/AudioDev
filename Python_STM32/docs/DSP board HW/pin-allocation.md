# Pin Allocation — STM32H725ZGT6 (LQFP-144)

**Status:** Proposed (Phase 0 → Phase 2 input). Feeds the schematic symbol pin assignment and the netlist review gate.
**Target MCU:** STM32H725ZGT6, LQFP-144, per `power-supply.md` §4 (amended from H723ZGT6).
**Sibling:** H735ZGT6 (+crypto) is expected pin-identical (both SMPS variants) — verify before relying on it. **Note:** the H723/H733 (LDO-only) are **not** pin-compatible in LQFP-144 — see the banner.

> ⚠️ **MCU amended to STM32H725ZGT6 (2026-07-13, see `power-supply.md` §4).** The H723 and
> H725 are **NOT pin-compatible in LQFP-144** — verified pad-by-pad against the KiCad
> `STM32H723ZGTx` vs `STM32H725ZGTx` symbols (2026-07-13):
> - The **peripheral/AF allocation carries over by *name*** — every signal used in §2/§4
>   (PE4/5/6, PF6/7/8/9, PB8/9/13/14, PD8/9/10/14/15, PA8/11/12/13/14, PC4, PB3, PH0/1,
>   PE1/7/8) exists on both parts, so the logical plan is unchanged.
> - But **pin *numbers* shift on ~138 of 144 pads.** The H725 bonds out `VSSSMPS`/`VLXSMPS`/
>   `VDDSMPS`/`VFBSMPS` (pins 14–17) + three `VDDLDO` + `VDD50USB`, renumbering everything
>   after them (e.g. PC4 44→47, VBAT 6→8, VREF+ 32→35, PDR_ON 143→142).
> - **15 GPIOs do not exist on the H725:** PF0–PF5, PF12, PF13, PG0–PG5, PG15 (consumed by the
>   new power pins). None were allocated, but they're gone from the headroom (§5).
> - **Schematic impact:** swapping the symbol H723ZGTx→H725ZGTx preserves net *intent* but
>   moves every pin — reconnect the symbol, and add the new MCU power section (SMPS inductor,
>   VDDLDO ×3, VDD50USB, 3rd VCAP). Power map redone in §7 below.

**Source of truth for pin/AF mappings:** SAI block/AF names cross-checked against the CubeMX-derived `PeripheralPins.c` for the `H723Z(E-G)T` (LQFP-144) variant in STM32duino for I2C / USART / ADC / USB (AF names are identical on the H725), and the STM32H72x datasheets (DS13313 for H723, **DS13311 for H725**). **The power-pin map (§7) and all pin *numbers* are taken from the KiCad `MCU_ST_STM32H7:STM32H725ZGTx` symbol** — do not use the H723 numbers, the parts are not pin-compatible (banner).

> ⚠️ Package / part notes:
> - **Port I is not bonded out on LQFP-144** — ignore any Port-I "default" pins from generic H7 references.
> - **The H723 has no SAI2/SAI3.** Its full serial-audio blocks are **SAI1** and **SAI4** (plus SPI-based I2S1/2/3). Both audio streams here use the two sub-blocks of **SAI1** (A = codec RX, B = DAC TX).

---

## 1. Audio topology (matches Phase 0 clocking scheme)

Two sub-blocks of **one SAI (SAI1)**, both **masters**, both fed from the **same SAI1 kernel clock (PLL3)**, each dividing down to its own bit clock — so both frame-syncs are locked to 48 kHz off a common source:

| Bus | SAI | Role | Bit clock | Notes |
|---|---|---|---|---|
| Codec capture | **SAI1_A** | Master, TDM **receiver** | ~12.288 MHz (8 slots × 32 bit × 48 kHz) | Generates BCLK + FSYNC to both ADC5140s; single shared serial-data input (both codecs on one DOUT bus, per-device slot assignment). No MCLK distributed — codecs derive internal clocks from BCLK via their on-chip PLL. |
| DAC playback | **SAI1_B** | Master, I2S **transmitter** | ~3.072 MHz (2 ch × 32 bit × 48 kHz) | Generates BCLK + LRCLK to the PCM5102A. **No MCLK** — DAC's internal PLL runs from BCLK (SCK pin strapped low); PF7 stays DNP. |

> **Note (STM32H723):** this part has **no SAI2** — its full serial-audio blocks are **SAI1** and **SAI4** (plus SPI-based I2S1/2/3). The DAC uses **SAI1 block B**, the second sub-block of the same peripheral that runs the codec capture on block A — not a separate SAI. The two sub-blocks are independent masters sharing one SAI1 kernel clock (PLL3): block A ÷ to 12.288 MHz, block B ÷ to 3.072 MHz, both frame-syncs at exactly 48 kHz from the common source, so the capture and playback sample rates are **frequency-locked by construction** (no drift, nothing to coordinate across clock trees). This is the standard full-duplex SAI configuration (block A in, block B out), stays in the D2 domain on DMA1/2, and reuses one driver for both directions. SAI4 (PD11/12/13/PE0, D3 domain, BDMA+SRAM4) and I2S2/SPI2 (PB12/13) were the alternatives — rejected as higher-risk for the clock-sync requirement.

---

## 2. Primary peripheral allocation

| Function | Signal | Pin | AF | Direction | Connects to |
|---|---|---|---|---|---|
| **SAI1 (codec TDM RX)** | SAI1_FS_A | **PE4** | AF6 | out | ADC5140 ×2 — FSYNC |
| | SAI1_SCK_A | **PE5** | AF6 | out | ADC5140 ×2 — BCLK |
| | SAI1_SD_A | **PE6** | AF6 | in | ADC5140 ×2 — shared DOUT bus |
| | SAI1_MCLK_A *(reserve)* | PE2 | AF6 | out | test point / DNP — no MCLK in baseline scheme |
| **SAI1_B (DAC I2S TX)** | SAI1_SCK_B | **PF8** | AF6 | out | PCM5102A — BCK |
| | SAI1_FS_B | **PF9** | AF6 | out | PCM5102A — LRCK |
| | SAI1_SD_B | **PF6** | AF6 | out | PCM5102A — DIN |
| | SAI1_MCLK_B | PF7 | AF6 | out | **DNP / test point** — PCM5102A needs no MCLK (SCK strapped to DGND) |
| **I2C1 (control)** | I2C1_SCL | **PB8** | AF4 | OD | ADC5140 ×2 — 2.2–4.7 kΩ pull-ups to 3V3 (DAC not on I2C: PCM5102A is strap-configured — see `dac-selection.md`) |
| | I2C1_SDA | **PB9** | AF4 | OD | " |
| **USART3 (BT — reserved)** | USART3_TX | **PD8** | AF7 | out | BT module RX |
| | USART3_RX | **PD9** | AF7 | in | BT module TX |
| | USART3_RTS | **PB14** | AF7 | out | BT module CTS (HW flow control) |
| | USART3_CTS | **PB13** | AF7 | in | BT module RTS |
| **USB_OTG_FS (reserve)** | OTG_FS_DM | **PA11** | AF10 | bidir | USB-C D− (data reserved; charge-only baseline) |
| | OTG_FS_DP | **PA12** | AF10 | bidir | USB-C D+ |
| **Battery sense** | ADC1_INP4 | **PC4** | analog | in | battery voltage divider (`BATT_SENSE` net) |
| **Control pot 1** | ADC1_INP11 | **PC1** | analog | in | net `Pot2` — RV1 wiper (pot: `3V3_A` ↔ GND) |
| **Control pot 2** | ADC1_INP8 | **PC5** | analog | in | net `Pot3` — RV2 wiper (pot: `3V3_A` ↔ GND) |
| *(spare pot input)* | ADC1_INP10 | **PC0** | analog | in | reserved — net `Pot1` label present on the MCU sheet, nothing attached (was "control pot 1" before the 2026-07-15 two-pot amendment, §6 item 6) |
| **Clock verify** | MCO1 | **PA8** | AF0 | out | test point (HSE/PLL health) |

---

## 3. Fixed-function pins (no mux choice — reserve on symbol)

| Function | Pin(s) | Notes |
|---|---|---|
| SWD debug | **PA13** (SWDIO), **PA14** (SWCLK) | 10-pin Cortex header for J-Link |
| SWO (optional trace) | **PB3** | Reserve as test point; RTT is the baseline, SWO is a bonus |
| HSE crystal | **PH0** (OSC_IN), **PH1** (OSC_OUT) | Keep loop tight; source of PLL3 SAI clock |
| Boot | **BOOT0** (dedicated pin) | 10 kΩ pull-down strap; SWD-only programming |
| Reset | **NRST** | 100 nF + optional header |
| Core supply | **VCAP ×3** + **V*SMPS** + **VDDLDO ×3** (see §7) | H725 SMPS-direct: cap/strap treatment per AN5419 / **Nucleo-H725** (not H723ZG — supply mode differs) |
| Analog ref | **VREF+** (pin 35 on H725) | **no VREF− pin** — bonded internally to VSSA. Tie VREF+ per Nucleo crib (to VDDA or a reference) |
| Power | see §7 power-pin map | full decoupling per Nucleo crib |

---

## 4. Control / housekeeping GPIO (reserve; final port pick at schematic)

| Function | Suggested pin | Notes |
|---|---|---|
| Codec SHDNZ / reset (shared) — net `CODEC_SHDNZ` | **PD10** | drives both ADC5140 SHDNZ (net `CODEC_SHDNZ`, per schematic + `adc-netlist.md`); add per-codec split only if bring-up needs it |
| Codec spare reset / 2nd line | **PD14** | keep free for independent codec control |
| DAC soft-mute (PCM5102A **XSMT**) | **PD15** | hold **low** through power-up until rails + BCLK stable, drive high to un-mute (ramped) — see `dac-selection.md` §6 |
| BT module reset / enable | **PE7** | matches chosen module's control pin |
| BT status / wake | **PE8** | LP/host-wake if module provides it |
| Status LED | **PE1** | debug heartbeat |

ADC5140 I2C addresses are set by hardware **ADDR** strap resistors (not GPIO) — the two codecs must strap to distinct addresses; verify at the netlist review gate.

---

## 5. Utilization

~28 of **~99** available GPIO used (H725 LQFP-144 — the H725 has ~15 fewer GPIO than the H723; see below). Still generous headroom for spin-2 additions. Freed by the SAI1_B move: **PD11/PD12/PD13/PE0** (the former mis-labeled SAI2 pins) are available, as is SAI4 entirely.

> ⚠️ **Headroom reduced by the H725 swap.** The H725 does **not** bond out **PF0–PF5, PF12, PF13, PG0–PG5, PG15** (15 GPIO consumed by the SMPS/VDDLDO pins). None are allocated, but the earlier "most of ports F and G remain free" no longer holds. Surviving Port F = PF6–PF11, PF14, PF15; surviving Port G = PG6–PG14. Confirm any spin-2 pin pick exists on the H725 (§7 / the `STM32H725ZGTx` symbol), not the H723.

---

## 6. Open items to resolve before finalizing the symbol

1. ~~**DAC MCLK.**~~ **Resolved 2026-07-13:** DAC decided = **PCM5102A** (`dac-selection.md` rev 2). PF7 = DNP/test point; DAC not on I2C. DAC-side straps for the schematic: **SCK→DGND** (enables internal PLL / no-MCLK mode), **FMT→GND** (I2S), **DEMP→GND**, **FLT→GND** (normal latency), **XSMT→PD15**.
2. **BT module.** UART3 + RTS/CTS is reserved; confirm the chosen module actually uses HW flow control and whether it needs the reset/wake GPIOs above (Phase 0 item 5).
3. **USB.** Baseline is charge-only, so PA11/PA12 are reserved but need not route to the connector's data pair on spin 1. Decide whether to route them anyway (near-zero cost, keeps the door open).
4. **Battery-sense pin vs. layout.** PC4/ADC1_INP4 chosen arbitrarily among free ADC1 inputs — pick the one nearest the power section at placement to keep the divider trace short.
5. **Cross-check at netlist review gate:** SAI pin-mux validity (done here), I2C address straps, codec DOUT bus-hold/pull, BCLK/FSYNC test points, decoupling counts.
6. **Control pots (amended 2026-07-15, later the same day: three → two).** **Two** MCU-read panel pots (RV1 → net `Pot2` → PC1, RV2 → net `Pot3` → PC5), each wiped between `3V3_A` and GND — `3V3_A` because VREF+ ties to VDDA_MCU = `3V3_A` (through FB1), making the reading ratiometric; fed from *before* the ferrite so wiper current/noise stays off the reference net. Suggested: 10 kΩ linear (~330 µA each), wiper → ~1 kΩ series → 100 nF to GND at the MCU pin (LPF + S/H charge reservoir; use a long ADC sampling time) — **RC not yet entered in the schematic**. The **third pot is not an MCU input**: it is the volume pot (RV3, chassis) on the DAC output path, and it carries the integrated on/off switch — now a **hard battery-line switch** (`bat+` → switch → `VBAT`), not an EN signal; see `power-supply-netlist.md` §2. PC0 = ADC1_INP10 is a free spare (a `Pot1` label sits unattached on the MCU sheet). Channel numbers **verified 2026-07-15** against the CubeMX-derived `PeripheralPins.c` for the `H725Z(E-G)T` variant: PC0 = ADC1_INP10, PC1 = ADC1_INP11, PC5 = ADC1_INP8. **PC2 was rejected** — on the H72x it exists only as PC2_C = ADC3_INP0 (no ADC1/2 path; the ADC123_INP12 mapping is an H74x-ism), and ADC3 lives in the D3 domain.

---

## 7. Power / ground pin map (verified from the KiCad `STM32H725ZGTx` symbol)

**Redone for the H725 (2026-07-13).** Pin numbers below are the H725 pinout and **differ from the H723** — see the banner at the top. Verified pad-by-pad from the KiCad `MCU_ST_STM32H7:STM32H725ZGTx` symbol; ⚠ still cross-check the SMPS / VDDLDO / VCAP treatment against **DS13311 + AN5419 + the Nucleo-H725 reference** before the netlist gate — the correct wiring is supply-mode-dependent (SMPS-direct here).

| Net | Pins | Count | Notes |
|---|---|---|---|
| VDD (3V3 digital) | 7, 13, 19, 32, 42, 56, 71, 79, 92, 106, 119, 129, 144 | 13 | decouple each (0.1 µF/pin + bulk) |
| VDDLDO | 70, 105, 143 | 3 | **new on H725** — core-LDO input; in SMPS-direct mode tie per AN5419 (typically to VDD) ⚠ |
| VDDSMPS | 16 | 1 | **new** — core-SMPS input, from `3V45_D` + local decoupling |
| VLXSMPS | 15 | 1 | **new** — SMPS inductor node → 2.2 µH → VFBSMPS (keep loop tight) |
| VFBSMPS | 17 | 1 | **new** — SMPS output/feedback; 4.7 µF to GND at pin ⚠ |
| VSSSMPS | 14 | 1 | **new** — SMPS ground |
| VCAP | 68, 103, 140 | 3 | **3 on H725 (was 2)** — cap value/treatment per AN5419 for SMPS-direct ⚠ |
| VDD33USB | 91 | 1 | USB FS 3.3 V (reserve; charge-only baseline) |
| VDD50USB | 90 | 1 | **new** — USB transceiver supply; tie per Nucleo-H725 even on charge-only ⚠ |
| VDDA | 36 | 1 | `VDDA_MCU` (3V3_A via ferrite) |
| VREF+ | 35 | 1 | see §3 |
| VBAT (MCU backup domain) | 8 | 1 | **not** the `BATT` cell net — see note below |
| VSS | 6, 12, 18, 33, 41, 55, 69, 80, 89, 104, 118, 128, 141 | 13 | single GND plane |
| VSSA | 34 | 1 | analog ground |
| PDR_ON | 142 | 1 | tie to VDD (internal power-down reset OK) |

No VREF− pin (internally VSSA). The H725 **does** break out the core SMPS (`V*SMPS`) and `VDDLDO` — that is the whole reason for the H723→H725 amendment (`power-supply.md` §4). Take the SMPS / VCAP / VDDLDO strap-and-cap treatment verbatim from AN5419 / Nucleo-H725; it is supply-mode-dependent.

> ⚠️ **VBAT pin (8 on H725) ≠ the `BATT` cell net.** The MCU VBAT pin is the RTC/backup-domain supply (≤3.6 V op). Do **not** connect it to the 3.0–4.2 V `BATT` cell net — that would exceed its rating. With no coin-cell backup in use, tie it to **VDD / `3V45_D`** per the Nucleo crib. The board's battery is the `BATT` net (sensed via `BATT_SENSE` → PC4); the two share no copper. Renamed from `VBAT`→`BATT` on 2026-07-13 specifically to remove this name collision. Flag at the netlist gate.

---

*Updated 2026-07-15 (later): control pots reduced **three → two** (RV1 = `Pot2` → PC1/INP11, RV2 = `Pot3` → PC5/INP8; PC0/INP10 spare). The third panel pot is the volume pot RV3 on the DAC output — chassis part, no MCU pin — and its integrated switch is now a hard battery-line switch (`bat+` → `VBAT`), not `EN_3V45`; see `power-supply-netlist.md` §2/§3a. Schematic-entry status: sheets connected via global labels (2026-07-15 conversion pass); pot wiper RCs not yet entered.*

*Updated 2026-07-15: added three control pots on PC0/PC1/PC5 (ADC1_INP10/11/8) — same ADC1 as `BATT_SENSE` (4-channel scan) and adjacent to the VREF+/VDDA corner. Pots wipe `3V3_A` ↔ GND (ratiometric vs VREF+); pot 1's integrated switch is SW1 (`EN_3V45`). Initial pick of PC2 corrected: on the H72x PC2 is PC2_C = ADC3_INP0 only (user caught via the KiCad symbol; confirmed against the `H725Z(E-G)T` PeripheralPins.c). See §6 item 6.*

*Updated 2026-07-13: DAC finalized to PCM5102A per `dac-selection.md` rev 2 — PF7 MCLK → DNP, PD15 → XSMT, strap notes added.*

*Updated 2026-07-13: cell/system net renamed `VBAT`→`BATT` (sense midpoint `VBAT_SENSE`→`BATT_SENSE`) across power docs to match the schematic and remove the collision with the MCU's backup-domain VBAT pin. The MCU VBAT pin keeps its name and ties to VDD/`3V45_D`.*

*Updated 2026-07-13: **H725 pinout correction.** Verified pad-by-pad against the KiCad `STM32H725ZGTx` vs `STM32H723ZGTx` symbols that the two are **not pin-compatible** in LQFP-144 (~138/144 pads differ; 15 GPIO — PF0–5, PF12/13, PG0–5, PG15 — dropped for the SMPS/VDDLDO pins). Corrected the amendment banner, §3 (VREF+ 32→35, VCAP/SMPS/VDDLDO), §5 (headroom), and rewrote §7's power map from the H725 symbol. All §2/§4 signal allocations were already H725-safe (no used pin lost). Numbers still to be cross-checked vs DS13311/AN5419/Nucleo-H725 at the netlist gate.*

*SAI/I2C/UART/ADC/USB pin+AF verified 2026-07-12 against the CubeMX-derived `PeripheralPins.c` (LQFP-144 variant) and the STM32H723ZG datasheet; SAI block/AF names and the power-pin map verified directly against the KiCad `MCU_ST_STM32H7:STM32H723ZGTx` symbol. Correction log: the DAC was originally mis-assigned to "SAI2" (H743 carryover) — the H723 has no SAI2; moved to SAI1 block B.*
