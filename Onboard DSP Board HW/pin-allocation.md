# Pin Allocation — STM32H725RGV6 (VFQFPN68)

**Status:** As-built (schematic entered; netlist review gate items marked ⚠).
**Target MCU:** STM32H725RGV6 — VFQFPN68, 8×8 mm, 0.4 mm pitch, exposed pad = VSS. 46 GPIO. JLCPCB [C5271073](https://jlcpcb.com/partdetail/STMicroelectronics-STM32H725RGV6/C5271073) (~$10–12; low stock — 10 pcs secured; DigiKey/ST eStore fallback). **Sibling:** H735RGV6 (+crypto) if ever needed.

**Package consequences (drive the whole allocation):**

- Bonded GPIO: **all of Port A, Port B minus PB11, Port C = PC0/1/4/5/6/7/9/10/11/12/14/15, PD2, PH0/PH1.** Ports D (except PD2), E, F, G do not exist.
- **SAI1 has no pins on this package** — CubeMX lists only **SAI4** as an available SAI, and SAI4 block A has no SCK/FS pins here, so **SAI4_B is the only peripheral that can master the 8-slot TDM bus**. The DAC therefore rides an SPI-I2S peripheral (I2S1). See §1.
- **SMPS-direct is the only core supply mode** (VDDLDO bonded internally; ST-confirmed) → **400 MHz hard ceiling**, no board-level recovery to 550 MHz. Plan of record was already 400 MHz for power (`power-supply.md` §4); the ceiling makes the DSP-headroom analysis and YIN burst rework load-bearing. Exit if they fail: respin to LQFP-144 H725ZGT6 with SMPS→LDO cascade.
- **No VREF+ pin** (internal to VDDA → `MCU_VDDA` is the ADC reference), no PDR_ON, no VDD33USB/VDD50USB. Simplifies the power section (§7).

**Sources of truth:** pad-by-pad pinout cross-checked between the KiCad `MCU_ST_STM32H7:STM32H725RGVx` symbol and the CubeMX `STM32H725RGVx.xml` (ST open pin data — identical); AFs from the CubeMX-derived stm32duino `H725R(E-G)V_H735RGV` `PeripheralPins.c` and Zephyr `stm32h725rgvx-pinctrl.dtsi` (two independent derivations, agreeing). ⚠ spot-check the six audio-pin AFs against DS13311 Table 8 at the netlist gate.

---

## 1. Audio topology (clocking scheme — resolved)

Capture and playback are **frequency-locked by construction**: both peripherals' kernel-clock muxes select **PLL3_P** (RCC `D3CCIPR.SAI4BSEL`, `D2CCIP1R.SPI123SEL` — both offer pll3_p). HSE = **24.576 MHz** (Y1) → PLL3 integer-N (e.g. VCO 393.216 MHz, PLL3_P = 49.152 MHz).

| Bus | Peripheral | Role | Bit clock | Notes |
|---|---|---|---|---|
| Codec capture | **SAI4_B** | Master, TDM **receiver** | 12.288 MHz (8 slots × 32 bit × 48 kHz) | Generates BCLK + FSYNC to both ADC5140s; single shared serial-data input (both codecs on one bus, per-device slot assignment). No MCLK distributed — codecs derive internal clocks from BCLK via their on-chip PLL. |
| DAC playback | **I2S1** (SPI1, I2S master TX) | Master, I2S **transmitter** | 3.072 MHz (2 ch × 32 bit × 48 kHz; I2SDIV = 16 from 49.152 MHz) | Generates BCK + LRCK to the PCM5102A. **No MCLK** — DAC's internal PLL runs from BCK (SCK pin strapped low). |

**Why two different peripherals:** SAI4_B is the only sub-block with clock pins on this package, and one sub-block provides one master bit clock — the two streams need different rates (12.288 vs 3.072 MHz), so the DAC uses I2S1. SAI4 block A (SD_A on **PB2**, AF8) remains available as an internal-synchronous slave sharing block B's 12.288 MHz TDM clock — a future TDM-playback option, no clock pins needed.

**Firmware note — SAI4 is D3-domain:** capture DMA via **BDMA**, buffers in **SRAM4** (16 KB; 8 ch × 48 samples × 4 B double-buffered ≈ 3 KB/ms-block — comfortable). D-cache coherency for that region handled in the platform layer. The DAC side (I2S1, D2 domain) uses regular DMA. ⚠ verify SAI4_B master-receiver TDM config + BDMA request routing against RM0468 at firmware bring-up.

---

## 2. Primary peripheral allocation

| Function | Signal / net | Pin | Pad | AF | Direction | Connects to |
|---|---|---|---|---|---|---|
| **SAI4_B (codec TDM RX)** | `SAI4_FS_B` | **PC0** | 13 | AF8 | out | ADC5140 ×2 — FSYNC |
| | `SAI4_SCK_B` | **PA2** | 19 | AF8 | out | ADC5140 ×2 — BCLK |
| | `SAI4_SD_B` | **PA0** | 17 | AF10 | in | ADC5140 ×2 — shared SDOUT bus |
| | SAI4_MCLK_B *(reserve)* | PA1 | 18 | AF10 | out | test point / DNP — no MCLK in the clocking scheme |
| **I2S1 (DAC TX)** | `I2S1_CK` | **PA5** | 24 | AF5 | out | PCM5102A — BCK |
| | `I2S1_WS` | **PA4** | 23 | AF5 | out | PCM5102A — LRCK |
| | `I2S1_SDO` | **PA7** | 26 | AF5 | out | PCM5102A — DIN |
| | *(no MCLK reserve)* | — | — | — | — | I2S1_MCK = PC4 collides with `BATT_SENSE`; DAC needs none |
| **I2C1 (control)** | `I2C1_SCL` | **PB8** | 64 | AF4 | OD | ADC5140 ×2 — R2 pull-up to `3V45_D` ⚠ value unset (2.2–4.7 kΩ). DAC not on I2C (strap-configured, `dac-selection.md`) |
| | `I2C1_SDA` | **PB9** | 65 | AF4 | OD | " (R1 pull-up) |
| **USART3 (BT — reserved)** | `USART3_TX` | **PC10** | 54 | AF7 | out | BT module RX |
| | `USART3_RX` | **PC11** | 55 | AF7 | in | BT module TX |
| | `USART3_RTS` | **PB14** | 38 | AF7 | out | BT module CTS (HW flow control) |
| | `USART3_CTS` | **PB13** | 37 | AF7 | in | BT module RTS |
| **USB (reserve)** | `OTG_FS_DM` | **PA11** | 46 | — | bidir | USB data reserved; charge is via jack ring, no USB connector on spin 1 (this part's OTG_HS in FS-PHY mode) |
| | `OTG_FS_DP` | **PA12** | 47 | — | bidir | " |
| **Battery sense** | `BATT_SENSE` = ADC1_INP4 | **PC4** | 27 | analog | in | battery voltage divider |
| **Control pot 1** | `Pot2` = ADC1_INP11 | **PC1** | 14 | analog | in | RV1 wiper (pot: `3V3_A` ↔ GND, ratiometric vs VDDA) |
| **Control pot 2** | `Pot3` = ADC1_INP8 | **PC5** | 28 | analog | in | RV2 wiper |
| **Clock verify** | MCO1 | **PA8** | 43 | AF0 | out | test point (HSE/PLL health) |

Pots are **PCB-mounted** (they mechanically support the board; knobs go right-angle through the panel), so wiper runs are short traces. Wiper RC filters judged unnecessary — firmware uses a long ADC sampling time (10 k pot ≈ 2.5 kΩ worst-case source) plus normal control-value smoothing; an optional 100 nF at each wiper is the only candidate if bench noise ever suggests it. The third panel pot is **RV3, the volume pot** (chassis-style but PCB-mounted, integrated switch = hard battery-line switch `bat+`→`VBAT`) — not an MCU input.

---

## 3. Fixed-function pins

| Function | Pin(s) | Pad | As-built |
|---|---|---|---|
| SWD debug | **PA13** (`SWDIO`), **PA14** (`SWCLK`) | 48, 52 | **J5**: 2×5 1.27 mm ARM Cortex Debug header — 1 VTref=`3V45_D`, 2 SWDIO, 4 SWCLK, 6 SWO, 10 NRST, 3/5/9 GND, 7 KEY, 8 NC |
| SWO | **PB3** (`SWO`) | 58 | wired to J5 pin 6; RTT is the logging baseline, SWO a bonus |
| HSE crystal | **PH0/PH1** | 10, 11 | **Y1 = 24.576 MHz** + C93/C94 load caps (15 pF placeholder — ⚠ set to 2×(CL−C_stray) for the chosen part; if a 3225 4-pad crystal, pads 2/4 = GND in the footprint) |
| Boot | **BOOT0** | 63 | R14 10 kΩ pull-down; SWD-only programming |
| Reset | **NRST** | 12 | C2 100 nF to GND + J5 pin 10 (⚠ MCU-sheet net needs its global `NRST` label restored to reach J5) |
| Analog ref | VDDA | 16 | `MCU_VDDA` = `3V3_A` via FB1; **VREF+ is internal to VDDA on this package** — no pin, no strap |
| Power | see §7 | | |

---

## 4. Control / housekeeping GPIO (as-built)

| Function | Pin | Pad | As-built |
|---|---|---|---|
| Codec SHDNZ (shared) — `CODEC_SHDNZ` | **PC6** | 40 | drives both ADC5140 SHDNZ; R18 10 kΩ pull-down holds reset until MCU drives |
| Codec spare reset / 2nd line | **PC7** | 41 | reserved (unwired) — split only if bring-up needs it |
| DAC soft-mute — `DAC_XSMT` | **PC9** | 42 | PCM5102A XSMT: hold **low** through power-up until rails + BCK stable (`dac-selection.md` §6) |
| BT module reset/enable — `BT1` | **PB12** | 36 | reserved (label only, spin 2) |
| BT status/wake — `BT2` | **PB15** | 39 | reserved (label only, spin 2) |
| Status LED — `LED` | **PD2** | 57 | PD2 → D1 anode, cathode → R15 → GND (active-high, off during reset by Hi-Z default) ⚠ R15 value unset — 1 kΩ ≈ 1.5 mA |

ADC5140 I2C addresses are set by hardware ADDR straps: U3 = GND/GND, U4 = IOVDD/GND. ⚠ confirm against the SBAS892A strap→address table at the gate (`adc-netlist.md` §6).

---

## 5. Utilization

**29 of 46 GPIO used.** Free: PA1 (MCLK reserve/TP), PA3, PA6, PA9, PA10, PA15, PB0, PB1, PB2 (SAI4_SD_A option), PB4, PB5, PB6, PB7, PB10, PC12, PC14/PC15 (LSE pair — usable as GPIO, no 32 kHz crystal planned). Headroom is real but thin vs the LQFP — check any spin-2 pin pick against this list and the package pinout (ports D/E/F/G largely don't exist).

---

## 6. Open items (netlist-gate checklist)

1. ⚠ **Crystal load caps** — C93/C94 = 15 pF placeholder; finalize against the chosen 24.576 MHz part's CL (2×(CL−C_stray)); footprint choice for 2-pad vs 4-pad crystal.
2. ⚠ **DS13311 AF spot-check** for the six audio pins (machine-derived AFs above; two sources agree).
3. ⚠ **I2C pull-up values** (R1/R2) and **ADDR strap values** — parts placed, values unset.
4. ⚠ **R15 (LED) value** — suggest 1 kΩ.
5. ~~**NRST label**~~ **Resolved** — verified from the netlist 2026-07-24: `NRST` = U7 pin 12 + C2 + J5 pin 10, one net.
6. **USB routing** — PA11/PA12 reserved; decide whether to route to any pads on spin 1 (near-zero cost; no connector planned). If USB data is ever activated, ⚠ verify how the transceiver is supplied on VFQFPN68 (no VDD33USB/VDD50USB pins — DS13311).
7. **BT module** — confirm the chosen module uses HW flow control and matches the PB12/PB15 control lines (Phase 0 item 5).
8. **SDOUT bus pull-down** — 100 kΩ DNP on `SAI4_SD_B` (populate only if bench shows float; `adc-netlist.md` §5).
9. **Test points** — see `test-points.md` (single source of truth; categorized by access type). Reserve pad on PA1 (`SAI4_MCLK_B`) noted there as Cat 3 / DNP.

---

## 7. Power / ground pin map (as-built)

| Net | Pads | Count | As-built |
|---|---|---|---|
| `3V45_D` (VDD digital) | 9, 22, 35, 51, 68 | 5 | decoupling section: C96–C99 100 nF (one per pin at layout) + C101 4.7 µF bulk |
| VBAT (backup domain) | 1 | 1 | tied to `3V45_D` (no coin cell) — **not** the battery `VBAT` net; shares name only |
| VDDSMPS | 6 | 1 | `3V45_D` — **coverage rule, not per-pin caps** (2026-07-24, see `layout-notes.md` §5.1): pin vias into the island; ≥1 100 nF island↔GND cap within ~2 mm of the pin-6 via (on the near side of the VDD cluster — this is the noisy consumer), 4.7 µF within ~5 mm |
| VLXSMPS → VFBSMPS | 5 → 7 | | **L2 2.2 µH** between them; **C95 4.7 µF** at VFBSMPS (AN5419 direct-SMPS) — keep this hot loop tight; VSSSMPS (pad 4) is two pads away |
| VCAP | 33, 49, 66 | 3 | **100 nF each** (C90/C91/C92) — LDO permanently disabled on this package (ST-confirmed) |
| VDDA / VSSA | 16 / 15 | 1/1 | `MCU_VDDA` (FB1 from `3V3_A`) + C38 100 nF / C37 1 µF *(schematic refs)* |
| VSS | 8, 21, 34, 50, 67 + **exposed pad (69)** | 6 | single ground plane; pad soldered, thermal-via stitch at layout |
| NRST / BOOT0 | 12 / 63 | | C2 100 nF / R14 10 kΩ pull-down |

Pins that exist on other H725 packages but **not here** (nothing to wire): VDDLDO ×3 (internal — SMPS-only supply mode), VREF+ (internal to VDDA), PDR_ON (internal), VDD33USB/VDD50USB.

---

*Pinout verified pad-by-pad: KiCad `STM32H725RGVx` symbol ↔ CubeMX `STM32H725RGVx.xml` (identical). AF numbers from stm32duino `H725R(E-G)V_H735RGV` `PeripheralPins.c` + Zephyr `stm32h725rgvx-pinctrl.dtsi`. SMPS/VCAP/VDDLDO treatment per AN5419 + ST community confirmation (VFQFPN68 = SMPS-only, VCAP 100 nF). Kernel-clock muxes (`SAI4BSEL`, `SPI123SEL` → pll3_p) confirmed against RM0468-derived ChibiOS/Zephyr clock definitions. ADC channel numbers (PC0=INP10 spare, PC1=INP11, PC5=INP8, PC4=INP4) from the same pin data.*
