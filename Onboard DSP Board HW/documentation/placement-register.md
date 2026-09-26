# Placement Register — Onboard DSP Board

**Generated file — do not hand-edit.** Produced by `tools/placement_register.py` from `Main Board.kicad_pcb`. Re-run after any placement change.

Parts are keyed by **value and function, not reference designator** — designators change on re-annotation. Passives are aggregated by value within each zone; distinct parts are listed individually.

## Board extents

| Metric | Value |
|---|---|
| Placed footprints | 92 |
| Board outline | 89.0 × 29.8 mm (x 94.2 … 183.2, y 72.5 … 102.2) |
| Long axis (x) span, origins | 79.4 mm (96.7 … 176.1) |
| Short axis (y) span, origins | 25.0 mm (74.5 … 99.5) |
| Back-side parts | none — single-sided |

## Zone — Analog front end

Spans x = 96.7 … 133.1 mm, 40 parts.

| Part | x (mm) | y (mm) | Package |
|---|---|---|---|
| Bridge Pickup | 96.65 | 81.35 | PinHeader_1x07_P2.00mm_Horizontal |
| ~ | 98.00 | 86.50 | TestPoint_Plated_Hole_ID7_OD1.2mm |
| TLV320ADC5140IRTWR | 105.75 | 87.00 | RTW24_4P15X4P15_TEX |
| TPS7A2033PDBVR | 114.50 | 82.85 | SOT-23-5 |
| TLV9001IDCK | 114.90 | 75.61 | SOT-353_SC-70-5 |
| PCM5102 | 116.50 | 95.00 | TSSOP-20_4.4x6.5mm_P0.65mm |
| Bridge Pickup | 121.75 | 81.40 | PinHeader_1x07_P2.00mm_Horizontal |
| TLV320ADC5140IRTWR | 124.75 | 87.03 | RTW24_4P15X4P15_TEX |
| ~ | 133.10 | 87.12 | TestPoint_Plated_Hole_ID7_OD1.2mm |
| .1uF (×5) | 109.1 … 128.5 | — | passive |
| 1.2K (×1) | 115.8 | — | passive |
| 100K (×1) | 114.0 | — | passive |
| 100nF (×1) | 118.2 | — | passive |
| 10K (×5) | 101.8 … 120.2 | — | passive |
| 10uF (×3) | 115.0 … 122.0 | — | passive |
| 1uF (×10) | 104.5 … 128.9 | — | passive |
| 2.2uF (×3) | 116.8 … 118.8 | — | passive |
| 62 (×1) | 116.2 | — | passive |
| 68K (×1) | 116.3 | — | passive |

## Zone — MCU

Spans x = 139.5 … 157.9 mm, 35 parts.

| Part | x (mm) | y (mm) | Package |
|---|---|---|---|
| MC01 | 139.77 | 88.10 | TestPoint_Plated_Hole_ID4_OD7.0mm |
| LED | 142.71 | 74.50 | LED_0603_1608Metric |
| STM32H725RGVx | 145.75 | 86.75 | QFN-68-1EP_8x8mm_P0.4mm_EP6.4x6.4mm |
| Debug Connector | 151.56 | 98.36 | PinHeader_2x05_P1.27mm_Vertical |
| 24Mhz | 153.05 | 84.05 | Crystal_SMD_WE_IQXC-26-4Pin_1.6x1.2mm |
| .1uF (×1) | 144.4 | — | passive |
| 100nF (×12) | 139.6 … 153.4 | — | passive |
| 10K (×3) | 139.5 … 145.2 | — | passive |
| 10uF (×2) | 155.1 … 156.7 | — | passive |
| 1K (×1) | 145.2 | — | passive |
| 1M (×3) | 144.4 … 157.9 | — | passive |
| 1uF (×1) | 150.0 | — | passive |
| 2.2uH (×1) | 152.7 | — | passive |
| 4.7K (×2) | 145.9 … 147.9 | — | passive |
| 4.7uF (×1) | 155.7 | — | passive |
| 6.8pF (×2) | 153.3 … 154.8 | — | passive |
| 600 (×1) | 149.5 | — | passive |

## Zone — Power / charger

Spans x = 158.1 … 169.0 mm, 14 parts.

| Part | x (mm) | y (mm) | Package |
|---|---|---|---|
| TPS63020DSJR | 161.40 | 83.50 | DSJ14_2P85X1P58 |
| TP4054 | 165.00 | 93.00 | SOT-23-5 |
| Battery | 165.95 | 75.60 | JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal |
| Output Jack | 169.04 | 97.75 | PinHeader_1x03_P2.54mm_Vertical |
| .1uF (×1) | 158.1 | — | passive |
| 1.3M (×1) | 166.6 | — | passive |
| 1.5uH (×1) | 166.2 | — | passive |
| 10uF (×1) | 159.3 | — | passive |
| 220K (×1) | 167.6 | — | passive |
| 22uF (×2) | 163.1 … 163.1 | — | passive |
| 3.3K (×1) | 162.8 | — | passive |
| 4.7uF (×2) | 167.2 … 167.8 | — | passive |

## Zone — Radio / controls

Spans x = 171.2 … 176.1 mm, 3 parts.

| Part | x (mm) | y (mm) | Package |
|---|---|---|---|
| ~ | 171.25 | 92.00 | TestPoint_Plated_Hole_ID7_OD1.2mm |
| E104-BT5032A | 176.10 | 82.15 | WIRELM-SMD_E104-BT5010A |
| 10K (×1) | 174.6 | — | passive |

## Key distances

Centre-to-centre unless a pin is named. These are the separations the layout rationale depends on.

| From | To | Distance |
|---|---|---|
| MCU | nearer ADC codec | *not placed* |
| MCU | core SMPS inductor | 7.14 mm |
| MCU | buck-boost | 15.98 mm |
| MCU | charger | 20.24 mm |
| Buck-boost | nearer ADC codec | *not placed* |
| Buck-boost inductor | nearer ADC codec | *not placed* |
| Analog LDO | nearer ADC codec | *not placed* |
| Analog LDO | DAC | 12.31 mm |
| HSE crystal | MCU | 7.78 mm |
| HSE crystal | core SMPS inductor | 4.36 mm |
| HSE crystal | its load caps | *not placed* |
| HSE crystal | NRST cap | 2.38 mm |
| BLE module | MCU | 30.70 mm |
| BLE module | buck-boost inductor | 10.03 mm |

## Clearances — courtyard edge to courtyard edge

Centre-to-centre is meaningless for the large parts. These are the gaps that decide whether the corner assembles and whether metal sits in a radiating near field.

| From | To | Gap |
|---|---|---|
| BLE module | buck-boost inductor | 1.95 mm |
| BLE module | volume pot | *not placed* |
| BLE module | battery connector | 2.55 mm |
| Buck-boost inductor | volume pot | *not placed* |

## Keep-out region — BLE antenna end

The pad-free end of the module carries the ceramic chip antenna. Copper is cleared beneath it on all layers and the end faces the board edge, so no return path detours around the gap. Gaps below are to the nearest metal; vendor external-metal guidance is 10-30 mm for best range and degrades gracefully rather than cliff-edge.

Extent: x = 170.35 … 181.85 mm, y = 72.93 … 77.07 mm (11.50 × 4.14 mm).

| Part | Gap to region |
|---|---|
| Buck-boost inductor | 4.48 mm |
| Volume pot | *not placed* |
| Battery connector | 2.55 mm |
| Buck-boost converter | 8.06 mm |

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

