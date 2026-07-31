# Placement Register — Onboard DSP Board

**Generated file — do not hand-edit.** Produced by `tools/placement_register.py` from `Main Board.kicad_pcb`. Re-run after any placement change.

Parts are keyed by **value and function, not reference designator** — designators change on re-annotation. Passives are aggregated by value within each zone; distinct parts are listed individually.

## Board extents

| Metric | Value |
|---|---|
| Placed footprints | 106 |
| Long axis (x) span | 76.4 mm (98.2 … 174.6) |
| Short axis (y) span | 25.0 mm (74.5 … 99.5) |
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

Spans x = 139.5 … 155.7 mm, 31 parts.

| Part | x (mm) | y (mm) | Package |
|---|---|---|---|
| R | 145.24 | 74.50 | R_0402_1005Metric |
| STM32H725RGVx | 145.75 | 86.75 | QFN-68-1EP_8x8mm_P0.4mm_EP6.4x6.4mm |
| R | 145.95 | 94.14 | R_0402_1005Metric |
| R | 147.95 | 94.14 | R_0402_1005Metric |
| Debug Connector | 151.56 | 98.36 | PinHeader_2x05_P1.27mm_Vertical |
| 24Mhz | 153.25 | 83.85 | Crystal_SMD_2016-4Pin_2.0x1.6mm |
| .1uF (×1) | 144.4 | — | passive |
| 100nF (×12) | 139.6 … 153.4 | — | passive |
| 10K (×3) | 139.5 … 145.2 | — | passive |
| 15pF (×2) | 153.3 … 155.2 | — | passive |
| 1M (×2) | 144.4 … 145.9 | — | passive |
| 1uF (×1) | 150.0 | — | passive |
| 2.2uH (×1) | 152.7 | — | passive |
| 4.7uF (×2) | 154.7 … 155.7 | — | passive |
| 600 (×1) | 149.5 | — | passive |

## Zone — Power / charger

Spans x = 159.8 … 174.6 mm, 15 parts.

| Part | x (mm) | y (mm) | Package |
|---|---|---|---|
| TPS63020DSJR | 163.30 | 83.80 | VSON-14-1EP_3x4.45mm_P0.65mm_EP1.6x4.2mm |
| TP4054 | 165.00 | 93.00 | SOT-23-5 |
| Battery | 167.95 | 75.75 | JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal |
| Output Jack | 169.04 | 97.75 | PinHeader_1x03_P2.54mm_Vertical |
| ~ | 174.60 | 98.00 | Potentiometer_Chinese_Single_Horizontal_Switch |
| .1uF (×1) | 160.0 | — | passive |
| 1.5uH (×1) | 168.6 | — | passive |
| 100K (×1) | 169.5 | — | passive |
| 10uF (×1) | 161.2 | — | passive |
| 1M (×1) | 159.8 | — | passive |
| 30k (×1) | 162.8 | — | passive |
| 4.7uF (×2) | 167.2 … 167.8 | — | passive |
| 47uF (×1) | 164.9 | — | passive |
| 590K (×1) | 168.5 | — | passive |

## Key distances

Centre-to-centre unless a pin is named. These are the separations the layout rationale depends on.

| From | To | Distance |
|---|---|---|
| MCU | nearer ADC codec | 21.00 mm |
| MCU | core SMPS inductor | 7.14 mm |
| MCU | buck-boost | 17.80 mm |
| MCU | charger | 20.24 mm |
| Buck-boost | nearer ADC codec | 38.68 mm |
| Buck-boost inductor | nearer ADC codec | 43.92 mm |
| Analog LDO | nearer ADC codec | 9.76 mm |
| Analog LDO | DAC | 11.77 mm |
| HSE crystal | MCU | 8.04 mm |
| HSE crystal | core SMPS inductor | 4.58 mm |
| HSE crystal | its load caps | 2.10 mm |
| HSE crystal | NRST cap | 2.61 mm |

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

