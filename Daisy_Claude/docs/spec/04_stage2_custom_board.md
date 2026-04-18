# Spec 04 — Stage 2: Custom Board Planning

**Status:** planning — decisions recorded below are agreed but work not yet started.

Stage 1 (wire program on Daisy Seed Rev 4 + Pod) is complete and confirmed working.
Stage 2 is designing and fabbing a custom board that will serve as the permanent DSP
platform for this project.

---

## 1. Chip target — locked: STM32H743VIT6

| Property | Value |
|---|---|
| Package | LQFP-100 (14×14 mm, 0.5 mm pitch) |
| Flash | 2 MB internal |
| SRAM | 1 MB internal (DTCM + AXI + D2 + D3) |
| Core | Cortex-M7 @ 480 MHz |
| Audio | SAI1 (same peripheral as H750 on Daisy Seed) |

Rationale over the H750 (current Daisy Seed chip):
- H750 internal flash is only 128 KB — the Daisy Seed works around this by booting from
  external QSPI flash, which we explicitly do not want.
- H743 has 2 MB internal flash: enough for this project without external memory.
- Both chips are LQFP-100 variants, so the pin layout and peripheral set are the same.
  Firmware should port with a new linker script + new board.h only.

Rationale over LQFP-144 (H743ZIT6):
- LQFP-100 is a smaller, simpler board. No peripherals we need require the extra pins.

---

## 2. Reference materials

### WeActStudio MiniSTM32H7xx
- GitHub: https://github.com/WeActStudio/MiniSTM32H7xx
- A commercially produced minimum-system board using the STM32H743VIT6 (and H750VBT6).
- Hardware files are in **Altium format** (.SchDoc / .PcbDoc). KiCAD 7+ can import Altium
  files directly — use File → Import → Altium Designer.
- Board documentation is in Chinese. Claude can translate: paste text into Claude Code,
  or upload PDF/image to the Claude app (claude.ai) for image-based translation.
- This board includes a lot we don't need (TFT header, QSPI flash, SD card, DVP camera
  port). Use the Altium import as a starting-point schematic cross-check and layout
  reference for the CPU island, then strip it down.
- **Before building on the import:** verify whether the board uses the internal LDO
  (VCAP scheme, two external caps) or bypasses the LDO by feeding VCAP from an external
  1.1 V rail. The two approaches have different layout implications. AN4938 covers both.

### ST Application Note AN4938 (Rev 7, October 2024)
- "Getting started with STM32H74xI/G and STM32H75xI/G MCU hardware development"
- URL: https://www.st.com/resource/en/application_note/an4938-getting-started-with-stm32h74xig-and-stm32h75xig-mcu-hardware-development-stmicroelectronics.pdf
- **This is the layout rulebook.** Covers LQFP-100 explicitly.
- Key sections to read before laying out the CPU:
  - Power supply schemes (internal LDO vs. bypass)
  - VCAP pin requirements (see §3 below — this is the most common first-spin mistake)
  - Per-pin decoupling cap placement diagram for LQFP-100
  - VDDA / VREF+ filtering for ADC
  - PCB stack-up recommendation (4-layer minimum)

---

## 3. Critical layout notes (CPU island)

### VCAP — the H743-specific gotcha
The H743 has an internal LDO that regulates the core supply. VCAP1 and VCAP2 are the
LDO output pins. Each needs a ~2.2 µF ceramic capacitor placed as close as possible to
the pin. This is **not** present on most simpler STM32 families and is the most common
H7 first-spin mistake. AN4938 §power-supply covers this in detail.

If the LDO is bypassed (VCAP connected to an external 1.1 V rail), the caps change
and you need the extra rail. Check what WeAct does before deciding.

### Per-pin VDD decoupling
Each VDD/VSS pin pair gets a 100 nF ceramic cap. The whole package also needs one
4.7 µF bulk ceramic. AN4938 has a placement diagram showing which cap goes where
relative to the LQFP-100 pin numbering.

### VDDA / VREF+
Separate analog supply pins. If ADC performance matters, add a ferrite bead + caps
filter between VDD and VDDA. AN4938 shows the recommended filter circuit.

### Stack-up
ST recommends 4-layer minimum: signal / GND / VDD / signal. Solid ground plane under
the chip is what makes decoupling caps effective. Do not attempt this on 2-layer.

---

## 4. Firmware portability

Stage 1 firmware was written with Stage 2 portability as an explicit constraint:
- No external memory accesses
- All buffers fit in internal SRAM
- No libDaisy, no HAL — only CMSIS register headers
- SAI1 peripheral is identical on H743 vs H750

Expected porting work:
- New linker script (`custom_h743/linker/stm32h743_flash.ld`) — update FLASH origin/size
  (flash at 0x08000000, 2 MB), update SRAM regions to match H743 layout
- New `board.h` — reassign pin names to match custom board schematic
- New CubeIDE project subfolder (`custom_h743/`) alongside `seed_h750/`
- Clock config may need a tweak if HSE crystal value changes
- No driver rewrites expected

---

## 5. KiCAD workflow (when ready to start)

1. Import WeAct Altium files into KiCAD (File → Import → Altium Designer)
2. Audit the CPU schematic section against AN4938 (power supply scheme, decoupling values)
3. Strip out unused subsystems (TFT, QSPI, SD, DVP)
4. Add project-specific peripherals (audio codec, debug header, power input)
5. Layout: start with CPU island using AN4938 cap placement diagram, then route outward
6. DRC + AN4938 checklist before sending to fab

KiCAD symbol and footprint for STM32H743VIT6 are in the standard KiCAD library
(`MCU_ST_STM32H7`) — no need to import from SnapMagic/Ultra Librarian.
