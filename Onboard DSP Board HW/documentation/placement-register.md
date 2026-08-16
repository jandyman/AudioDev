# Placement Register — Onboard DSP Board

**Generated file — do not hand-edit.** Produced by `tools/placement_register.py` from `Main Board.kicad_pcb`. Re-run after any placement change.

Parts are keyed by **value and function, not reference designator** — designators change on re-annotation. Passives are aggregated by value within each zone; distinct parts are listed individually.

## Board extents

| Metric | Value |
|---|---|
| Placed footprints | 108 |
| Board outline | 89.0 × 29.8 mm (x 94.2 … 183.2, y 72.5 … 102.2) |
| Long axis (x) span, origins | 77.9 mm (98.2 … 176.1) |
| Short axis (y) span, origins | 25.0 mm (74.5 … 99.5) |
| Back-side parts | none — single-sided |

## Zone — Analog front end

Spans x = 98.2 … 133.1 mm, 60 parts.

| Part | x (mm) | y (mm) | Package |
|---|---|---|---|
| BAS316 | 100.45 | 78.50 | D_SOD-323 |
| R | 101.75 | 87.00 | R_0402_1005Metric |
| R | 101.75 | 89.50 | R_0402_1005Metric |
| BAS316 | 104.95 | 78.50 | D_SOD-323 |
| XLV320ADC5140IRTWR | 105.75 | 87.00 | HVQFN-24-1EP_4x4mm_P0.5mm_EP2.1x2.1mm |
| BAS316 | 109.45 | 78.50 | D_SOD-323 |
| Neck Pickup | 112.55 | 74.50 | PinHeader_1x06_P2.54mm_Vertical |
| BAS316 | 113.95 | 78.50 | D_SOD-323 |
| TPS7A2033PDBVR | 115.75 | 83.25 | SOT-23-5 |
| PCM5102 | 116.50 | 95.00 | TSSOP-20_4.4x6.5mm_P0.65mm |
| BAS316 | 119.50 | 78.50 | D_SOD-323 |
| R | 120.25 | 87.78 | R_0402_1005Metric |
| R | 120.25 | 86.78 | R_0402_1005Metric |
| BAS316 | 124.00 | 78.50 | D_SOD-323 |
| XLV320ADC5140IRTWR | 124.75 | 87.03 | HVQFN-24-1EP_4x4mm_P0.5mm_EP2.1x2.1mm |
| BAS316 | 128.50 | 78.50 | D_SOD-323 |
| BAS316 | 133.00 | 78.50 | D_SOD-323 |
| Bridge Pickup | 133.12 | 74.50 | PinHeader_1x06_P2.54mm_Vertical |
| .1uF (×5) | 109.1 … 128.5 | — | passive |
| 1.2K (×1) | 115.8 | — | passive |
| 100nF (×1) | 119.5 | — | passive |
| 10K (×1) | 104.8 | — | passive |
| 10uF (×2) | 115.5 … 122.0 | — | passive |
| 1uF (×12) | 104.5 … 128.9 | — | passive |
| 2.2uF (×3) | 116.8 … 118.8 | — | passive |
| 4.7uF (×16) | 98.2 … 130.8 | — | passive |
| 62 (×1) | 116.2 | — | passive |

## Zone — MCU

Spans x = 139.5 … 157.9 mm, 33 parts.

| Part | x (mm) | y (mm) | Package |
|---|---|---|---|
| LED | 142.71 | 74.50 | LED_0603_1608Metric |
| R | 145.24 | 74.50 | R_0402_1005Metric |
| STM32H725RGVx | 145.75 | 86.75 | QFN-68-1EP_8x8mm_P0.4mm_EP6.4x6.4mm |
| R | 145.95 | 94.14 | R_0402_1005Metric |
| R | 147.95 | 94.14 | R_0402_1005Metric |
| Debug Connector | 151.56 | 98.36 | PinHeader_2x05_P1.27mm_Vertical |
| 24Mhz | 153.05 | 84.05 | Crystal_SMD_WE_IQXC-26-4Pin_1.6x1.2mm |
| .1uF (×1) | 144.4 | — | passive |
| 100nF (×12) | 139.6 … 153.4 | — | passive |
| 10K (×3) | 139.5 … 145.2 | — | passive |
| 15pF (×2) | 153.3 … 154.8 | — | passive |
| 1M (×3) | 144.4 … 157.9 | — | passive |
| 1uF (×1) | 150.0 | — | passive |
| 2.2uH (×1) | 152.7 | — | passive |
| 4.7uF (×2) | 154.7 … 155.7 | — | passive |
| 600 (×1) | 149.5 | — | passive |

## Zone — Power / charger

Spans x = 158.1 … 169.0 mm, 13 parts.

| Part | x (mm) | y (mm) | Package |
|---|---|---|---|
| TPS63020DSJR | 161.40 | 83.80 | VSON-14-1EP_3x4.45mm_P0.65mm_EP1.6x4.2mm |
| TP4054 | 165.00 | 93.00 | SOT-23-5 |
| Battery | 165.95 | 75.60 | JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal |
| Output Jack | 169.04 | 97.75 | PinHeader_1x03_P2.54mm_Vertical |
| .1uF (×1) | 158.1 | — | passive |
| 1.5uH (×1) | 166.7 | — | passive |
| 100K (×1) | 167.6 | — | passive |
| 10uF (×1) | 159.3 | — | passive |
| 30k (×1) | 162.8 | — | passive |
| 4.7uF (×2) | 167.2 … 167.8 | — | passive |
| 47uF (×1) | 163.1 | — | passive |
| 590K (×1) | 166.6 | — | passive |

## Zone — Radio / controls

Spans x = 174.6 … 176.1 mm, 2 parts.

| Part | x (mm) | y (mm) | Package |
|---|---|---|---|
| ~ | 174.60 | 98.00 | Potentiometer_Chinese_Single_Horizontal_Switch |
| E104-BT5032A | 176.10 | 82.15 | WIRELM-SMD_E104-BT5010A |

## Key distances

Centre-to-centre unless a pin is named. These are the separations the layout rationale depends on.

| From | To | Distance |
|---|---|---|
| MCU | nearer ADC codec | 21.00 mm |
| MCU | core SMPS inductor | 7.14 mm |
| MCU | buck-boost | 15.93 mm |
| MCU | charger | 20.24 mm |
| Buck-boost | nearer ADC codec | 36.79 mm |
| Buck-boost inductor | nearer ADC codec | 42.02 mm |
| Analog LDO | nearer ADC codec | 9.76 mm |
| Analog LDO | DAC | 11.77 mm |
| HSE crystal | MCU | 7.78 mm |
| HSE crystal | core SMPS inductor | 4.36 mm |
| HSE crystal | its load caps | 1.92 mm |
| HSE crystal | NRST cap | 2.38 mm |
| BLE module | MCU | 30.70 mm |
| BLE module | buck-boost inductor | 9.59 mm |

## Clearances — courtyard edge to courtyard edge

Centre-to-centre is meaningless for the large parts. These are the gaps that decide whether the corner assembles and whether metal sits in a radiating near field.

| From | To | Gap |
|---|---|---|
| BLE module | buck-boost inductor | 1.45 mm |
| BLE module | volume pot | 0.52 mm |
| BLE module | battery connector | 2.55 mm |
| Buck-boost inductor | volume pot | 4.63 mm |

## Keep-out region — BLE antenna end

The pad-free end of the module carries the ceramic chip antenna. Copper is cleared beneath it on all layers and the end faces the board edge, so no return path detours around the gap. Gaps below are to the nearest metal; vendor external-metal guidance is 10-30 mm for best range and degrades gracefully rather than cliff-edge.

Extent: x = 170.35 … 181.85 mm, y = 72.93 … 77.07 mm (11.50 × 4.14 mm).

| Part | Gap to region |
|---|---|
| Buck-boost inductor | 4.66 mm |
| Volume pot | 12.38 mm |
| Battery connector | 2.55 mm |
| Buck-boost converter | 7.94 mm |

## Pin geometry — MCU east face — core SMPS and HSE share an edge

ST placed the core-SMPS hot loop (pads 4–7) and the HSE crystal pair (pads 10–11) on the same package edge, two pads apart. The HSE oscillator therefore sits within a few mm of the buck switch node no matter how it is placed — this is a pinout constraint, not a layout choice.

| Pin | Function | x (mm) | y (mm) |
|---|---|---|---|
| 4 | VSSSMPS | 149.64 | 88.75 |
| 5 | VLXSMPS — switch node | 149.64 | 88.35 |
| 6 | VDDSMPS | 149.64 | 87.95 |
| 7 | VFBSMPS | 149.64 | 87.55 |
| 10 | PH0 / HSE_IN | 149.64 | 86.35 |
| 11 | PH1 / HSE_OUT | 149.64 | 85.95 |

| From | To | Distance |
|---|---|---|
| VLXSMPS (switch node) → HSE_IN | | 2.00 mm |
| VFBSMPS → HSE_IN | | 1.20 mm |
| HSE pair pitch | | 0.40 mm |

