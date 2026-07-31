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

Capture and playback are **frequency-locked by construction**: both peripherals' kernel-clock muxes select **PLL3_P** (RCC `D3CCIPR.SAI4BSEL`, `D2CCIP1R.SPI123SEL` — both offer pll3_p).

**System sample rate is 32 kHz.** Bass content is negligible above ~10 kHz, so a 15 kHz Nyquist leaves real margin; the reduction cuts YIN's cost by ~56 % (its difference function scales as fs², since both window length and lag range track fs), which is a larger saving than the 27 % clock cut the 400 MHz ceiling imposes. 32 kHz is a standard rate — the PCM5102A groups it with 44.1 and 48 kHz as "single rate", and the ADC5140's programmable range is 7.35–768 kHz — so no codec runs off-book. The board's output is analog, so nothing external constrains the choice.

**HSE = 24.000 MHz**, a stock frequency, chosen for sourcing rather than for arithmetic. It regenerates the audio family exactly:

```
HSE 24.000  /M=5   → 4.800 MHz PLL3 reference
            ×N=128 → 614.4 MHz VCO      (wide range 192–836 MHz)
            /P=25  → PLL3_P = 24.576 MHz
```

The same VCO is reachable from 8, 12 or 16 MHz with M = 5 and N = 384/256/192, so the crystal frequency stays a free sourcing variable. 48 kHz remains available on the same tree (SAI ÷2, I2S ÷8) if it is ever wanted back.

| Bus | Peripheral | Role | Bit clock | Notes |
|---|---|---|---|---|
| Codec capture | **SAI4_B** | Master, TDM **receiver** | 8.192 MHz (8 slots × 32 bit × 32 kHz; PLL3_P ÷ 3) | Generates BCLK + FSYNC to both ADC5140s; single shared serial-data input (both codecs on one bus, per-device slot assignment). No MCLK distributed — codecs derive internal clocks from BCLK via their on-chip PLL. BCLK = 256 × fs, TI's own characterisation ratio. |
| DAC playback | **I2S1** (SPI1, I2S master TX) | Master, I2S **transmitter** | 2.048 MHz (2 ch × 32 bit × 32 kHz; PLL3_P ÷ 12) | Generates BCK + LRCK to the PCM5102A. **No MCLK** — DAC's internal PLL runs from BCK (SCK pin strapped low). Rate detection carries ±4 % tolerance, so the exact chain above spends none of that margin. |

**Why two different peripherals:** SAI4_B is the only sub-block with clock pins on this package, and one sub-block provides one master bit clock — the two streams need different rates (8.192 vs 2.048 MHz), so the DAC uses I2S1. SAI4 block A (SD_A on **PB2**, AF8) remains available as an internal-synchronous slave sharing block B's 8.192 MHz TDM clock — a future TDM-playback option, no clock pins needed.

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
| **I2C1 (control)** | `I2C1_SCL` | **PB8** | 64 | AF4 | OD | ADC5140 ×2 — pull-up to `3V45_D` ⚠ value unset (2.2–4.7 kΩ). DAC not on I2C (strap-configured, `dac-selection.md`) |
| | `I2C1_SDA` | **PB9** | 65 | AF4 | OD | " (pull-up) |
| **USB (reserve)** | `OTG_FS_DM` | **PA11** | 46 | — | bidir | USB data reserved; charge is via jack ring, no USB connector on spin 1 (this part's OTG_HS in FS-PHY mode) |
| | `OTG_FS_DP` | **PA12** | 47 | — | bidir | " |
| **Battery sense** | `BATT_SENSE` = ADC1_INP4 | **PC4** | 27 | analog | in | battery voltage divider |
| **Control pot 1** | `Pot2` = ADC1_INP11 | **PC1** | 14 | analog | in | wiper (pot: `3V3_A` ↔ GND, ratiometric vs VDDA) |
| **Control pot 2** | `Pot3` = ADC1_INP8 | **PC5** | 28 | analog | in | wiper |
| **Clock verify** | MCO1 | **PA8** | 43 | AF0 | out | test point (HSE/PLL health) |

Pots are **PCB-mounted** (they mechanically support the board; knobs go right-angle through the panel), so wiper runs are short traces. Wiper RC filters judged unnecessary — firmware uses a long ADC sampling time (10 k pot ≈ 2.5 kΩ worst-case source) plus normal control-value smoothing; an optional 100 nF at each wiper is the only candidate if bench noise ever suggests it. The third panel pot is **the volume pot** (chassis-style but PCB-mounted, integrated switch = hard battery-line switch `bat+`→`VBAT`) — not an MCU input.

---

## 3. Fixed-function pins

| Function | Pin(s) | Pad | As-built |
|---|---|---|---|
| SWD debug | **PA13** (`SWDIO`), **PA14** (`SWCLK`) | 48, 52 | debug header: 2×5 1.27 mm ARM Cortex Debug — 1 VTref=`3V45_D`, 2 SWDIO, 4 SWCLK, 6 SWO, 10 NRST, 3/5/9 GND, 7 KEY, 8 NC |
| SWO | **PB3** (`SWO`) | 58 | wired to the debug header SWO pin; RTT is the logging baseline, SWO a bonus |
| HSE crystal | **PH0/PH1** | 10, 11 | **24.000 MHz crystal, CL 8 pF, SMD1612-4P** — NDK NX1612SA family (4-pad; pads 2/4 = GND, tied to the can). Load caps ≈ **6.8 pF** (2×(CL−C_stray) = 7.0 pF at 4.5 pF stray; 6–10 pF covers 3–5 pF stray — ⚠ at CL 8 pF the answer is far more sensitive to C_stray than it was at CL 12 pF, so settle C_stray against the final routing before committing). The 1612 body is 1.92 mm² against the 2016's 3.2 mm² and the 3225's 8.0 mm², which is what makes the corner tractable — see `layout-notes.md` §5.1.1. |
| Boot | **BOOT0** | 63 | 10 kΩ pull-down; SWD-only programming |
| Reset | **NRST** | 12 | 100 nF to GND + the debug header NRST pin (⚠ MCU-sheet net needs its global `NRST` label restored to reach the header) |
| Analog ref | VDDA | 16 | `MCU_VDDA` = `3V3_A` via the VDDA ferrite; **VREF+ is internal to VDDA on this package** — no pin, no strap |
| Power | see §7 | | |

---

## 4. Control / housekeeping GPIO (as-built)

| Function | Pin | Pad | As-built |
|---|---|---|---|
| Codec SHDNZ (shared) — `CODEC_SHDNZ` | **PC6** | 40 | drives both ADC5140 SHDNZ; 10 kΩ pull-down holds reset until MCU drives |
| Codec spare reset / 2nd line | **PC7** | 41 | reserved (unwired) — split only if bring-up needs it |
| DAC soft-mute — `DAC_XSMT` | **PC9** | 42 | PCM5102A XSMT: hold **low** through power-up until rails + BCK stable (`dac-selection.md` §6) |
| Status LED — `LED` | **PD2** | 57 | PD2 → status-LED anode, cathode → series resistor → GND (active-high, off during reset by Hi-Z default). **Red 0603**, Vf 1.8–2.4 V, 300 mcd at 20 mA. Series resistor **1 kΩ ≈ 1.5 mA** (≈22 mcd, plainly visible); 2.2 kΩ ≈ 0.7 mA if battery life is favoured over brightness. **Red, not green** — a green Vf of ~3.0 V would leave only ~0.35 V across the resistor on this rail, so part-to-part Vf spread would swing the current several-fold; red's ~1.9 V leaves ~1.45 V and a well-defined current. |

ADC5140 I2C addresses are set by hardware ADDR straps: ADC-A = GND/GND, ADC-B = IOVDD/GND. ⚠ confirm against the SBAS892A strap→address table at the gate (`adc-netlist.md` §6).

---

## 5. Utilization

**23 of 46 GPIO used.** Free: PA1 (MCLK reserve/TP), PA3, PA6, PA9, PA10, PA15, PB0, PB1, PB2 (SAI4_SD_A option), PB4, PB5, PB6, PB7, PB10, PB12, PB13, PB14, PB15, PC10, PC11, PC12, PC14/PC15 (LSE pair — usable as GPIO, no 32 kHz crystal planned). PC10/PC11 plus PB13/PB14 remain a complete USART3 set (AF7, with hardware flow control) if a serial link is ever wanted. Headroom is real but thin vs the LQFP — check any spin-2 pin pick against this list and the package pinout (ports D/E/F/G largely don't exist).

---

## 6. Verification items (netlist-gate checklist)

Pin assignment is settled; these are confirmations and value picks to close at the gate.

1. ⚠ **Crystal load caps** — 6.8 pF suits the chosen 24 MHz / CL 8 pF part at ~4.5 pF stray; confirm C_stray against the final routing (6–10 pF covers 3–5 pF). At CL 8 pF, C_stray is a first-order term rather than a correction, so settle it against the routed layout, not before.
2. ⚠ **Crystal drive level** — the 1612's max drive is 100 µW, well under a 3225's. Check it against the H725 HSE drive setting, and leave a series damping-resistor position (0 Ω default) at the oscillator.
3. ⚠ **Load the 1612 footprint into the project** — `Main Board/AudioDev.pretty` holds `Crystal_SMD_NDK_NX1612SA-4Pin_1.6x1.2mm` (drawn to NDK's recommended land: pads 0.75 × 0.65 mm on 1.05 × 0.75 mm centres) but is **not yet in `fp-lib-table`**. Add it from Preferences → Manage Footprint Libraries (project tab), or with the project closed append to `Main Board/fp-lib-table`:
   `(lib (name "AudioDev")(type "KiCad")(uri "${KIPRJMOD}/AudioDev.pretty")(options "")(descr "Project-local footprints"))`
   Then swap the HSE crystal from `Crystal:Crystal_SMD_2016-4Pin_2.0x1.6mm` and re-run `tools/placement_register.py`. Note the inner gap between the two pad rows is 0.10 mm — right at JLC's minimum solder-mask dam, so expect a hairline dam or none; worth an eye on the fab drawing. KiCad's stock `Crystal:Crystal_SMD_WE_IQXC-26-4Pin_1.6x1.2mm` is a drop-in alternative if the local library is ever unavailable.
4. ⚠ **`DIVP3` odd value 25** — PLL1's DIVP is restricted to even values; PLL2/PLL3 are documented 1–128. The 24 MHz → 24.576 MHz chain in §1 depends on 25 being accepted. Verify in RM0468.
5. ⚠ **DS13311 AF spot-check** for the six audio pins (machine-derived AFs above; two sources agree).
6. ⚠ **I2C pull-up values** and **ADDR strap values** — parts placed, values unset.
7. ~~**LED series-resistor value**~~ **Resolved** — 1 kΩ; see `power-supply-netlist.md` for the LED part and the current-setting rationale.
8. ~~**NRST label**~~ **Resolved** — verified from the netlist 2026-07-24: `NRST` = MCU pin 12 + the 100 nF cap + the debug header NRST pin, one net.
9. **USB routing** — PA11/PA12 reserved; decide whether to route to any pads on spin 1 (near-zero cost; no connector planned). If USB data is ever activated, ⚠ verify how the transceiver is supplied on VFQFPN68 (no VDD33USB/VDD50USB pins — DS13311).
10. **SDOUT bus pull-down** — 100 kΩ DNP on `SAI4_SD_B` (populate only if bench shows float; `adc-netlist.md` §5).
11. **Test points** — see `test-points.md` (single source of truth; categorized by access type). Reserve pad on PA1 (`SAI4_MCLK_B`) noted there as Cat 3 / DNP.

---

## 7. Power / ground pin map (as-built)

| Net | Pads | Count | As-built |
|---|---|---|---|
| `3V45_D` (VDD digital) | 9, 22, 35, 51, 68 | 5 | decoupling section: 100 nF one per pin (at layout) + 4.7 µF bulk |
| VBAT (backup domain) | 1 | 1 | tied to `3V45_D` (no coin cell) — **not** the battery `VBAT` net; shares name only |
| VDDSMPS | 6 | 1 | `3V45_D` — **coverage rule, not per-pin caps** (2026-07-24, see `layout-notes.md` §5.1): pin vias into the island; ≥1 100 nF island↔GND cap within ~2 mm of the pin-6 via (on the near side of the VDD cluster — this is the noisy consumer), 4.7 µF within ~5 mm |
| VLXSMPS → VFBSMPS | 5 → 7 | | **2.2 µH inductor** between them; **4.7 µF** at VFBSMPS (AN5419 direct-SMPS) — keep this hot loop tight; VSSSMPS (pad 4) is two pads away |
| VCAP | 33, 49, 66 | 3 | **100 nF each** — LDO permanently disabled on this package (ST-confirmed) |
| VDDA / VSSA | 16 / 15 | 1/1 | `MCU_VDDA` (VDDA ferrite from `3V3_A`) + 100 nF / 1 µF |
| VSS | 8, 21, 34, 50, 67 + **exposed pad (69)** | 6 | single ground plane; pad soldered, thermal-via stitch at layout |
| NRST / BOOT0 | 12 / 63 | | 100 nF / 10 kΩ pull-down |

Pins that exist on other H725 packages but **not here** (nothing to wire): VDDLDO ×3 (internal — SMPS-only supply mode), VREF+ (internal to VDDA), PDR_ON (internal), VDD33USB/VDD50USB.

---

*Pinout verified pad-by-pad: KiCad `STM32H725RGVx` symbol ↔ CubeMX `STM32H725RGVx.xml` (identical). AF numbers from stm32duino `H725R(E-G)V_H735RGV` `PeripheralPins.c` + Zephyr `stm32h725rgvx-pinctrl.dtsi`. SMPS/VCAP/VDDLDO treatment per AN5419 + ST community confirmation (VFQFPN68 = SMPS-only, VCAP 100 nF). Kernel-clock muxes (`SAI4BSEL`, `SPI123SEL` → pll3_p) confirmed against RM0468-derived ChibiOS/Zephyr clock definitions. ADC channel numbers (PC0=INP10 spare, PC1=INP11, PC5=INP8, PC4=INP4) from the same pin data.*
