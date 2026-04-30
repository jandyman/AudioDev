# Spec 05 — Stage 2 target chip revision: LQFP-100 → LQFP-144

**Status:** supersedes §1 of spec 04 and revises §2 (reference materials).
The remainder of spec 04 (§3 layout notes, §4 firmware portability, §5 KiCAD
workflow) still applies essentially unchanged.

---

## 1. What changed

| | Old (spec 04 §1) | New |
|---|---|---|
| Chip | STM32H743VIT6 | **STM32H743ZIT6** |
| Pin count | 100 | **144** |
| Package | LQFP-100, 14×14 mm | **LQFP-144, 20×20 mm**, 0.5 mm pitch |
| Flash | 2 MB | 2 MB (unchanged) |
| SRAM | 1 MB | 1 MB (unchanged) |
| Core | M7 @ 480 MHz | unchanged |
| SAI1 peripheral | identical | unchanged |
| GPIOs | ~82 usable | ~114 usable |

---

## 2. Why the change

When spec 04 was drafted, the working assumption was that **WeActStudio
MiniSTM32H7xx** would serve as the reference design — its hardware files were
believed to be Altium source, importable into KiCAD 7+. Investigation found
the WeAct GitHub repo only ships:

- A schematic **PDF** (read-only)
- A board-outline **PDF**
- A 3D **STEP** file
- An Altium **IntLib** (parts library only — no schematic, no PCB layout)

There is **no `.SchDoc` or `.PcbDoc` source** in the WeAct repo. The "import
Altium into KiCAD" workflow does not apply.

A wider search for open-source LQFP-100 H743 reference designs with importable
source files came up empty:

- **OpenMV Cam H7 / H7 Plus** — confirmed by the OpenMV team as not open
  source for hardware. PDF only, design contracted out, OrCAD source not
  released.
- **Phil's Lab (pms67)** — public GitHub repos use STM32F4, not H7. The H7
  audio SoM (Phil's Lab #45) is part of his paid Altium course.
- **Waveshare OpenH743I-C** — uses LQFP-176/BGA, wrong package.
- **Random hobby repos** — quality unknown, not vendor-grade.

Meanwhile, **ST publishes the full Altium source files** for the
Nucleo-H743ZI / Nucleo-H743ZI2 (board MB1364) as part of their Board
Manufacturing Specification (`mb1364_bdp.zip`):

- `.PrjPcb` (Altium project)
- `.SchDoc` (schematic source)
- `.PcbDoc` (PCB layout source — the layer artwork in editable form)
- Gerbers, BOM, assembly drawings, 3D STEP

KiCAD 7+ imports Altium projects via *File → Import → Altium Designer*.
Confirmed working in the ST community thread "Issue Importing Nucleo-144
Development Board into KiCad" (status: Solved). One Linux-only gotcha
(case-sensitive filename references) does not apply on macOS.

The MB1364 layout was drawn by ST themselves — the chip vendor — on a 4-layer
stackup that matches AN4938's recommendation. As reference designs go this is
as authoritative as exists outside ST internal materials.

The package change from LQFP-100 to LQFP-144 is the price of switching the
reference. The CPU island layout — VCAP placement, per-pin decoupling, VDDA
filtering, crystal placement — transfers **pin-for-pin**, not just
philosophically.

---

## 3. Costs of the package change

Worth noting but all small:

- **Chip price:** H743ZIT6 ≈ H743VIT6 within a few dollars at unit qty.
- **Board area:** +6 mm in each dimension (20×20 mm chip vs 14×14 mm).
  Negligible for our enclosure budget.
- **Decoupling caps:** ~10 VDD/VSS pairs vs ~5 → roughly twice as many 100 nF
  caps. Sub-dollar.
- **Routing:** more pins to break out, but only the ones we use need to leave
  the CPU island. Unused pins still get their decoupling cap and stop there.
- **Firmware port from Stage 1:** unchanged in scope — new linker script + new
  `board.h`. SAI1 peripheral, clock tree, DMA controller all identical between
  H743 and H750.
- **KiCAD library:** STM32H743ZIT6 is in the standard `MCU_ST_STM32H7`
  symbol/footprint library. No SnapEDA/Ultra Librarian import needed.

What we gain (besides the layer artwork):

- Pin-for-pin reference layout from the chip vendor.
- ~32 more usable GPIOs — breathing room for future expansion (extra UART,
  expansion header, more controls) without redesigning.
- Ability to buy a $30 Nucleo-H743ZI2 for bench cross-reference while drawing.

---

## 4. Revised reference materials

Replaces spec 04 §2.

### Primary layout reference — Nucleo MB1364
- Product page: https://www.st.com/en/evaluation-tools/nucleo-h743zi.html
- Board design package (Altium source + Gerbers + BOM + STEP):
  `https://www.st.com/resource/en/board_manufacturing_specification/mb1364_bdp.zip`
- Schematic-only PDF (quick reference):
  `https://www.st.com/resource/en/schematic_pack/mb1364-h743zi-c01_schematic.pdf`
- User manual UM2407 (Nucleo-144 boards including MB1364):
  `https://www.st.com/resource/en/user_manual/um2407-stm32h7-nucleo144-boards-mb1364-stmicroelectronics.pdf`

### Rulebook — AN4938 (unchanged from spec 04 §2)
- "Getting started with STM32H74xI/G and STM32H75xI/G MCU hardware development"
- `https://www.st.com/resource/en/application_note/an4938-getting-started-with-stm32h74xig-and-stm32h75xig-mcu-hardware-development-stmicroelectronics.pdf`
- AN4938 covers LQFP-100, LQFP-176, and BGA — does **not** explicitly
  illustrate LQFP-144, but the per-pin decoupling principles transfer
  directly. The MB1364 layout is the canonical LQFP-144 application of these
  rules.

### Secondary cross-check — WeAct MiniSTM32H7xx (demoted)
- Repo at `hardware/weact_h7_ref/` (already cloned).
- Useful as a sanity check that a known-working LQFP STM32H743 production
  board agrees with our layout decisions on power, reset, crystal, and
  decoupling values. Not used as a layout starting point.

---

## 5. Revised workflow

Replaces spec 04 §5.

1. **Download** (st.com blocks automated curl — manual browser download):
   - `mb1364_bdp.zip` → unzip into `hardware/nucleo_h743zi_ref/`
   - `AN4938.pdf` → save into `hardware/st_appnotes/`
2. **Smoke-test the import**: open KiCAD 7+, *File → Import → Altium Designer*,
   point at the `.PrjPcb`. Verify the schematic and PCB views render.
   If something fails, stop and figure out why — do not work around it.
3. **Audit the imported CPU section** against AN4938:
   - VCAP1 / VCAP2 cap values and placement
   - Per-pin VDD decoupling values and placement
   - VDDA / VREF+ filter (ferrite + caps)
   - Crystal load capacitor values vs HSE crystal spec
4. **Strip out unused subsystems**: ST-Link debugger, Ethernet PHY, Arduino
   shield headers, USB host. Keep CPU island, power supply, reset circuit,
   crystals, debug header.
5. **Add project peripherals**: AK4556 codec (or replacement), audio jacks,
   power input, any user controls.
6. **Layout**: place project peripherals around the preserved CPU island.
   Do not move the CPU island components — that's the part we're inheriting.
7. **DRC + AN4938 checklist + 4-layer stackup confirmation** before fab.

---

## 6. Open questions to revisit when work starts

- **Internal LDO vs bypass mode** for VCAP. Whichever MB1364 uses is what we
  inherit unless there's a specific reason to override.
- **HSE crystal frequency** — MB1364 uses an 8 MHz crystal feeding the
  ST-Link MCO (which then drives H743 HSE via ST-Link's MCO output, not a
  local crystal on the H743). For our standalone board we drop the ST-Link
  MCO chain and need a local HSE crystal. Frequency choice (8 vs 16 vs 25 MHz)
  affects PLL config — Stage 1 used 16 MHz to match Daisy Seed. Decide
  before drawing the clock section.
- **Power input** — MB1364 takes 5 V from the ST-Link USB. Our board takes
  power from where? (Audio rack 9 V via 5 V LDO? USB-C? Both?) Decide before
  drawing the power section.
