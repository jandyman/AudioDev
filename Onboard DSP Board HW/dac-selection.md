# DAC Selection & Output Stage — Multichannel Audio Board

**Status:** In discussion (rev 2, clean-slate survey) — **leaning PCM5102A**, with PCM5100A as the cost-down and WM8524 as the alternate. Supersedes the rev-1 discussion that leaned ES9023P; that lean rested on two datasheet errors (see §7). Resolves Phase 0 item 3 of `multichannel-audio-board-plan.md` once open items close.
**Scope:** the stereo playback DAC on **I2S1** (SPI1 in I2S master-TX mode) and its analog output stage down to the offboard jack.

---

## 1. Requirements

- Stereo I2S DAC, slave-clocked from **I2S1** (BCLK + LRCLK only; no MCLK is routed — and none is available without cost, since I2S1_MCK shares PC4 with `BATT_SENSE`), sample-rate-locked to the SAI4_B codec capture via the shared PLL3 kernel clock (`pin-allocation.md` §1).
- **Space-constrained** board → minimize external parts. No external buffer op-amp if avoidable.
- **Battery / single 3.3 V supply** — no 5 V or boost rail.
- Output goes **offboard through a 10 kΩ audio-taper pot with integrated on/off switch** to an instrument input. The pot sits at the DAC/output-stage output.
- **Max output level ≈ 0.1 Vrms** (passive bass-guitar level) — instrument level, not 2 V line level.
- Output impedance as low as reasonable; variable output Z from the pot is accepted.
- Power on/off thump suppression is **nice-to-have, not hard**: the switch is on the pot, so power toggles happen with the pot at minimum, which attenuates any transient.
- **JLCPCB (LCSC) stocked** — turnkey assembly; Extended parts fine.

---

## 2. What the architecture demands of the part

These three derived requirements do the actual part selection — they were implicit in rev 1 and are made explicit here:

**Buffer-free drive.** The chain is `DAC → fixed pad → pot → jack` with no op-amp anywhere. The 26 dB pad must be low-impedance so the pot sees a stiff source, which means the pad's total resistance loads the DAC at roughly **1–2 kΩ**. The DAC must therefore have an **integrated line driver rated for ~1 kΩ loads**. This single spec eliminates most cheap DACs (weak-swing outputs like PT8211/CS4344 would force the buffer back in) and eliminated the ES9023 (5 kΩ min load).

**Ground-referenced (symmetric-to-ground) output.** A charge-pump DAC whose output swings symmetrically about ground needs **no DC-blocking caps** anywhere in the chain — the pad and pot are DC-coupled, and residual DC across the pot is µV-level (no scratchy-pot aging). A VDD/2-biased output would need two large coupling caps sized against the ~1 kΩ pad (≥10 µF each) plus it reintroduces turn-on thump.

**Attenuate in analog, not in DSP.** Unchanged from rev 1: a digital ÷20 costs ~26 dB of SNR against the DAC's fixed analog noise floor; a passive pad attenuates signal and DAC noise together. Digital trim reserved for ≤1–2 dB of calibration.

So the target category is: **strap-configured stereo DAC with integrated charge pump, ground-referenced output, and ≥1 kΩ-capable line driver, single 3.3 V.** This is a small category — it contains the TI PCM510xA family, the WM8524, and the ES9023.

---

## 3. Candidates (checked 2026-07-13)

| Part | Output / drive | Clock | Supply | Pkg | ~LCSC | Stock | Verdict |
|---|---|---|---|---|---|---|---|
| **PCM5102A** (TI) | 2.1 Vrms ground-centered, charge pump, **1 kΩ min load**, XSMT soft-mute | **No MCLK** (internal PLL off BCK, SCK tied low) | single 3.3 V | TSSOP-20 | ~$0.9–1.1 (C107671) | Good | **Leaning choice** |
| **PCM5100A** (TI) | Same family, pin-identical, 100 dB SNR (vs 112) | No MCLK | single 3.3 V | TSSOP-20 | ~$0.86 (C131154) | Good | Cost-down drop-in on same footprint |
| **WM8524** (Cirrus) | 2.1 Vrms ground-referenced, DC servo, **1 kΩ min load**, ≤1 mV DC offset, 800-sample soft-mute, pop-suppressed up/down sequencer | **Needs MCLK** (128–1152·fs, auto-detected, synchronous) | single 3.3 V | TSSOP-16 (5.0×4.4) | ~$0.98 (C146242) | **Thin (~80 pcs)** | Alternate — technically excellent, stock too thin for turnkey |
| **ES9023P** (ESS) | 2 Vrms ground-referenced, charge pump, but **5 kΩ min load** → pad output Z floor ~250–330 Ω | **Needs MCLK** (>192·fs async; power-up counter runs on MCLK) | single 3.3 V | SOP-16 | ~$1.2 (C2760388) | Good | Rejected: loses on both min load and clocking; R8 level-set can't reach 0.1 V (collapses below ~1.3 Vrms, bench-verified on diyAudio) |
| **CS4344** (Cirrus) | VDD/2-biased → coupling caps, weak drive, thump-prone | Needs MCLK | 3.3–5 V | TSSOP-10 | ~$0.4 | Good | Rejected: fails §2 on drive and DC coupling |
| **PT8211/TM8211** | ~0.5 Vrms, high-Z output, 16-bit, LSB-justified (not I2S) | No MCLK | 3.3–5 V | SOP-8 | ~$0.1 | Good | Rejected: needs a buffer — package savings lost immediately |
| I2C codecs w/ analog volume (ES8156, TLV320DAC3100, …) | Settable analog level, HP drivers | varies | varies | larger | $1–3 | varies | Rejected: I2C init is cheap (bus + driver already exist for the ADC5140s) but the analog-volume register would only replace four 0402 resistors while adding caps, pins, and config code. The pot is still required regardless (user volume + power switch). |

---

## 4. Why PCM5102A

- **Only category member with no MCLK at all**: SCK tied low → internal PLL runs from BCK. Three wires from I2S1, no MCLK trace near the analog section — and on this MCU an MCLK-requiring part would cost the battery-sense pin (I2S1_MCK = PC4).
- **1 kΩ min load** → the L-pad can sit at Rs = 1.2 k / Rsh = 62 Ω → **~59 Ω source feeding the pot** (rev 1's ES9023 could not do better than ~250–330 Ω within its load spec).
- Ground-centered charge-pump output → fully DC-coupled chain, no caps, no thump mechanism; **XSMT** soft-mute pin for controlled ramp (GPIO PC9, net `DAC_XSMT`, or RC delay).
- Strap-configured, deep TI documentation, RPi-ecosystem-proven no-MCLK operation.
- Good LCSC stock at ~$1; **PCM5100A is pin-identical on the same footprint** — 100 dB SNR is still ~30 dB more than a bass rig can use at 0.1 V, so the footprint carries a built-in cost-down (and 5101A/5102A upgrade) option with zero layout risk.

**Why not WM8524:** on paper it's arguably nicer (TSSOP-16, DC servo, sequenced pop-free up/down) but it needs MCLK and LCSC stock is ~80 pcs — not turnkey-safe. Revisit only if TI supply becomes a problem.

---

## 5. Output level & attenuation stage

Chain: `PCM5102A (2.1 Vrms) → fixed L-pad → 10 kΩ audio pot (w/ switch) → jack`, fully DC-coupled.

L-pad: **Rs = 1.2 kΩ, Rsh = 62 Ω** (per channel):

- Division with the 10 k pot in parallel with Rsh: 2.1 V × 61.6 / 1261.6 ≈ **0.103 Vrms max** at the pot — full pot rotation spans 0 → ~0.1 V.
- Pad output Z ≈ Rs ∥ Rsh ≈ **58 Ω**.
- DAC load = Rs + Rsh∥10k ≈ **1.26 kΩ** ✓ (≥1 kΩ spec), ~1.7 mA per channel at full scale — negligible battery cost.
- Jack sees the pot wiper: variable, worst case ~2.5 kΩ at mid-rotation. Into a ≥1 MΩ instrument input that is a 0.25 % level error; with ~500 pF of cable the pole is ~127 kHz. A passive bass itself presents 5–20 kΩ+, so this is cleaner than the source it emulates. **Accepted** (a constant-Z output would need a buffer *after* the pot, which is offboard — topologically impractical, not just a space trade).
- Noise: pad attenuates DAC noise with the signal; delivered SNR ≈ DAC's (~110 dB re 0.1 V incl. ~58 Ω Johnson noise). PCM5100A variant: ~98 dB — still far beyond the application.
- DC: ±1 mV-class DAC offset ÷20 → ~50 µV across the pot — no wiper-noise concern.
- **External loads:** ≥1 MΩ (instrument) is transparent; 10 kΩ (mixer line in) costs ~0.05 dB at full rotation, ~2 dB at mid-rotation — fine for a volume knob. Note 0.1 V is ~10 dB under −10 dBV consumer line nominal; mixer gain trim covers it.
- **Short-circuit safe:** a shorted jack grounds the wiper; worst case (pot at max) the short lands across Rsh, so the DAC sees Rs alone = 1.2 kΩ — still ≥ the 1 kΩ min load (~1.75 mA). The series Rs guarantees the DAC can never see <1.2 kΩ regardless of what's downstream.

Four 0402 resistors total (2/channel). TI's recommended RC output filter (470 Ω + 2.2 nF) is subsumed by the pad: add 2.2–3.3 nF across Rsh if wideband content downstream matters.

---

## 6. Board / pin integration

- **I2S:** I2S1 — BCLK=PA5 (`I2S1_CK`), LRCLK/WS=PA4 (`I2S1_WS`), DIN=PA7 (`I2S1_SDO`), all AF5. **No MCLK routed.** PCM5102A SCK pin strapped to DGND.
- **XSMT (soft-mute):** drive from GPIO **PC9** (net `DAC_XSMT`) — hold low until rails/clocks stable, release to un-mute. The pot-switch topology already covers worst-case thump (power toggles at pot minimum), so this is belt-and-suspenders.
- **Straps:** FLT, DEMP, FMT per datasheet defaults (normal latency, no de-emphasis, I2S).
- **Not on I2C** — I2C1 remains the two ADC5140s only.
- **Analog supply:** AVCC/CPVDD from the shared low-noise analog LDO (same rail family as ADC5140 AVDD); charge-pump caps local to the DAC.

No new MCU pins beyond what `pin-allocation.md` already allocates.

### PCM5102A pin-by-pin (TSSOP-20, per datasheet SLAS859C pin table + Fig. 33)

| Pin | Name | Connection |
|---|---|---|
| 1 | CPVDD | 3V3A (analog LDO rail) — 0.1 µF to GND tight at pin (pump input reservoir, *noisy return*); bulk 10 µF shared on the 3V3A pour nearby |
| 2 | CAPP | 2.2 µF flying cap to pin 4 (CAPM) |
| 3 | CPGND | GND (*noisy return — own via, don't share with quiet pads*) |
| 4 | CAPM | other end of flying cap |
| 5 | VNEG | 2.2 µF to GND at pin (−3.3 V rail decouple, *noisy return*) |
| 6 | OUTL | → Rs 1.2 k → pad node L (Rsh 62 Ω to GND) → pot L |
| 7 | OUTR | → Rs 1.2 k → pad node R (Rsh 62 Ω to GND) → pot R |
| 8 | AVDD | 3V3A — 0.1 µF to GND tight at pin (quiet-side termination); bulk shared with pin 1's 10 µF |
| 9 | AGND | GND (*quiet return — Rsh grounds group here*) |
| 10 | DEMP | GND (de-emphasis off) |
| 11 | FLT | GND (normal-latency filter) |
| 12 | SCK | GND (selects BCK-PLL / no-MCLK mode) |
| 13 | BCK | MCU PA5 (`I2S1_CK`) |
| 14 | DIN | MCU PA7 (`I2S1_SDO`) |
| 15 | LRCK | MCU PA4 (`I2S1_WS`) |
| 16 | FMT | GND (I2S) |
| 17 | XSMT | MCU PC9, net `DAC_XSMT` (low = soft-mute; would tie to AVDD if unused) |
| 18 | LDOO | 0.1 µF to GND — internal 1.8 V LDO output, **no supply connection** (external 1.8 V only if bypassing the LDO; not done here) |
| 19 | DGND | GND |
| 20 | DVDD | 3.3 V **digital** rail — 0.1 µF to GND at pin; bulk folds into the digital rail's existing 10 µF nearby (internal LDO derives the 1.8 V core from DVDD; keeps digital current off the analog LDO) |

Notes: **single GND net board-wide** — no AGND/DGND nets in the schematic (TI: one common ground plane, no split; same for the ADC5140s, whose AVSS and thermal pad both go "directly to the board ground plane"). Zoning is by placement and the 3V3A net, not by ground nets. Assumes the 6-layer stackup (solid GND on L2): every cap and ground pin takes its own via(s) tight to its pads; the plane closes all loops underneath. Decoupling-cap ordering on CPVDD/AVDD: pin → cap tap → via to 3V3A, so the cap junctions the trace and the rail via hangs beyond it (trace inductance to the rail is free filtering). Cap set: 4× 0.1 µF at pins (CPVDD, AVDD, DVDD, LDOO), 2× 2.2 µF charge pump (flying + VNEG) on L1 at the chip, 1× shared 10 µF on the 3V3A pour near the DAC (CPVDD side); DVDD bulk shared with the digital rail. Charge-pump caps (2, 4, 5) closest to the device. Free bonus from the auto power modes: BCK+LRCK held low >1 s → full power-down (~0.2 mA), and restart is automatic when the I2S clocks resume — firmware gets DAC power management just by stopping/starting I2S1.

---

## 7. Corrections vs rev 1 (why the ES9023 lean was wrong)

1. ES9023 **requires MCLK** (>192·fs async mode; the pop-suppression power-up counter runs on MCLK cycles). "No MCLK to route" was never true — it's true of the PCM510xA.
2. ES9023 **min load is 5 kΩ**; every pad row in the rev-1 table (500 Ω–2 kΩ loads) violated it.
3. ES9023's R8 output-level resistor cannot reach 0.1 V — output collapses below ~1.15–1.35 Vrms (diyAudio bench measurement). No pad-free path existed.

---

## 8. Open items before finalizing

1. **PCM5102A power-down behavior** — confirm no transient when 3.3 V collapses with XSMT high (mitigated by pot-at-min, but check the TI app notes / bench).
2. **Final pad values & pot taper** — confirm Rs=1.2k/Rsh=62 against the real full-scale (2.1 Vrms typ, ±10 % over supply) and pick audio-taper pot part.
3. **JLCPCB assembly check** — confirm C107671 (PCM5102APWR) loadable as Extended part at order time; note C131154 (PCM5100APWR) as BOM alternate.
4. **Optional RC across Rsh** — decide if the 2.2–3.3 nF ultrasonic filter cap is wanted.

---

## Sources

- PCM510xA family datasheet (TI) — https://www.ti.com/product/PCM5102A — 2.1 Vrms ground-centered, 1 kΩ min load, no-MCLK PLL mode, XSMT
- PCM5100APWR — LCSC C131154 — https://www.lcsc.com/product-detail/Digital-To-Analog-Converters-DACs_Texas-Instruments-PCM5100APWR_C131154.html (~$0.86, in stock)
- PCM5102APWR — LCSC C107671 — https://www.lcsc.com/product-detail/C107671.html
- WM8524 datasheet v4.1 (Wolfson/Cirrus) — https://d3uzseaevmutz1.cloudfront.net/pubs/proDatasheet/WM8524_v4.1.pdf — 1 kΩ min load, MCLK 128–1152·fs, DC servo
- WM8524CGEDT/R — LCSC C146242 — https://www.lcsc.com/product-detail/Digital-To-Analog-Converters-DACs_Cirrus-Logic-WM8524CGEDT-R_C146242.html (~$0.98, **~80 pcs**)
- ES9023 datasheet v0.72 (ESS) — https://www.esstech.com/wp-content/uploads/2022/09/ES9023-Datasheet-v0.72.pdf — MCLK modes p.4, RL min 5 kΩ p.10
- diyAudio: "ES9023: Lowest possible output using R8?" — https://www.diyaudio.com/community/threads/es9023-lowest-possible-output-using-r8.389217/ — bench-measured collapse below ~1.15–1.35 Vrms

*Decision not yet locked — see §8.*
