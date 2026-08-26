# Codec (ADC) — Firmware Initialization & Bring-Up

**Status:** Specification for the driver to be written. Not yet implemented.

**Scope:** the register configuration, SAI setup, and bring-up order for the two
TLV320ADC5140 capture converters. This document owns all register-level content;
`adc-netlist.md` §8 carries only the handful of settings that are load-bearing
on hardware values, and points here.

**Architecture assumed** (from `multichannel-audio-board-plan.md` and
`pin-allocation.md`): discrete STM32H725RGV6, bare-metal in-house ecosystem
(libDaisy already replaced). **SAI4_B is the TDM master receiver** — it is the
only sub-block with clock pins on the VFQFPN68 package. System sample rate
**32 kHz**, 8 slots × 32 bit → **BCLK 8.192 MHz** (256 × fs), kernel-clocked
from PLL3_P at 24.576 MHz. Both converters are ASI slaves deriving internal
clocks from BCLK via their on-chip PLLs; **no MCLK is distributed**.

**Datasheet:** TI SBAS892A. Register references use the Py_Rz_D[k] notation.

**Analog goal that drives several settings below:** preserve sub-audio string
deflection — the DSP should see the player pulling on the string *before*
release, not just the vibration after. The low-frequency corner is set in
hardware at roughly 1.7 Hz (`adc-netlist.md` §2); the job here is to avoid
undoing it in registers. Bass low E is 41.2 Hz, so everything of interest to
the feature extractor sits below the note fundamental.

---

## 1. Reference material worth mining

| Document | Relevance |
|---|---|
| SBAA383 — multiple devices, shared TDM and I²C | The authority for the two-device bus; carries worked I²C configuration scripts |
| SBAA381 — sample rates and processing blocks | Confirms the 32 kHz / 256× combination and the processing-block choice |
| SBAA378 — biquads | If any in-device filtering is ever wanted |
| SBAC290 — C register headers | Saves transcribing the register map |
| Linux ASoC driver `tlv320adcx140.c` | Independent working implementation — good for reset/power-up sequencing and bit-field interpretation where the datasheet is terse |

Full links and sourcing are in `adc-selection.md` §7.

Note SBAA382 covers operating the device *as bus master* — the opposite of this
design. Useful only as background on the ASI clocking model.

---

## 2. I²C control

Bus is I2C1 (`pin-allocation.md` §4), the two converters only — the playback DAC
is strap-configured and not on the bus.

- Device A (neck pickup) and device B (bridge pickup) differ only in their
  address straps and slot maps. One driver, one configuration table, called
  twice.
- ⚠ **Take the ADDR1/ADDR0 strap-to-address table from SBAS892A's Programming
  section at implementation time.** The family-standard values are widely
  assumed and are what the Linux driver uses, but this has not been verified
  against the datasheet for this part, and the schematic straps must be
  confirmed to land on two non-conflicting addresses (`adc-netlist.md` §11
  item 4).
- Registers are **paged**: write the page-select register (P0_R0) first, then
  the register within the page.
- **I²C broadcast write is available** for simultaneous configuration or
  triggering of both devices (SBAA383) — the clean way to get a synchronized
  channel start.
- Start the bus at 100 kHz for bring-up and raise it later; the parts support
  fast-mode and fast-mode plus.

---

## 3. Register configuration

Both devices unless noted.

### 3.1 Analog input — the settings the analog design depends on

⚠ **Items 1–4 all invert under the open hardware proposal in `adc-netlist.md`
§2.1** (DC-coupled differential input on one added cable conductor): source
becomes `CHx_INSRC = 00`, coupling `CHx_DC = 1`, impedance `CHx_IMP = 01`
(10 kΩ — 2.5 kΩ is not supported for DC-coupled inputs), and the quick-charge
item disappears. Do not write the driver against the proposal until it is
adopted, but do keep these four values together in one table in the source so
that flipping them is one edit rather than four.

1. **Input source: single-ended.** `CHx_INSRC = 01` → P0_R60/65/70/75 D[6:5],
   all four channels each device.
2. **Coupling: AC-coupled** (default). `CHx_DC = 0` → same registers, D4.
3. **Input impedance: 20 kΩ — not the 2.5 kΩ default.** `CHx_IMP = 10` →
   same registers, D[3:2]. **This setting is load-bearing for the entire analog
   plan.** The default would move the corner to roughly 13.5 Hz
   (`adc-netlist.md` §2). Source loading is no longer a factor.
4. **Input-cap quick charge** sized for the 4.7 µF blocking caps — the default
   assumes ≤ 1 µF. `INCAP_QCHG` → P0_R5 D[5:4]. Undersized, the baseline drifts
   for hundreds of milliseconds after channel power-up.
5. **Full scale / VREF:** default `ADC_FSCALE = 00` → P0_R59 D[1:0] → VREF
   2.75 V → 1 Vrms single-ended full scale. Requires AVDD ≥ 3.0 V, satisfied by
   the analog rail. **VREF quick-charge** default is 3.5 ms assuming a 1 µF VREF
   cap; if the hardware uses more, set `VREF_QCHG` → P0_R2 D[4:3] (3.5 / 10 /
   50 / 100 ms).

### 3.2 Automation that must be switched off

This is a far-field voice capture device being used as an instrumentation front
end. Its convenience features actively fight the design goal, and **all of them
default to a state that is wrong here.**

6. **Digital HPF: default is ENABLED**, first-order IIR, −3 dB at 12 Hz.
   **Disable it**, or reprogram its coefficients for a corner well below 1 Hz.
   Left alone it silently removes the pre-pluck string-deflection energy the
   whole low-frequency design exists to capture — and it does so without any
   error indication.
7. **AGC: off.** Deterministic gain is required for feature extraction.
8. **DRE: off** initially — automatic gain shifting means level
   nondeterminism. Revisit only after characterizing its effect on transients.
   With DRE off the device still gives roughly 108 dB dynamic range, which is
   ample.

### 3.3 Gain and calibration

9. **Channel PGA:** 0–42 dB range in 1 dB steps, plus digital channel volume
   (−100 to +27 dB in 0.5 dB steps) if more is needed.
   **Starting value: roughly 17 dB of deficit, not the 30–40 dB this document
   originally assumed.** The coil measures 40 mVpp and the front end amplifies
   it to ≈320 mVpp (`analog-front-end.md` §1). The earlier ~23 dB dispute in the
   project record is closed — both figures were estimates against a unity front
   end that no longer exists. Set gain against the measured level at the
   converter input and verify no clipping at full scale. **Reconsider whether
   DRE has a role at all** at this input level.
10. **Gain calibration:** 0.1 dB per-channel trim, to match channels after
    measurement. **The requirement is much smaller than previously stated.**
    Front-end gain is a resistor ratio matched to component tolerance, so what
    remains is coil-to-coil variation — real, but a trim rather than the
    semiconductor-spread correction this step was written for
    (`preamp-board.md` §1).
11. **Phase calibration:** available at 163 ns resolution per channel. File
    under later — this is for aligning neck against bridge channels for
    cross-pickup feature extraction (pluck position, string velocity). Apply
    only if bench measurement shows it is needed.

Neck and bridge levels will differ, and may differ per string.

### 3.4 MICBIAS

12. **MICBIAS is not used.** The preamp boards take the 3.3 V analog rail
    (`adc-netlist.md` §1, `analog-front-end.md` §4). Leave `MICBIAS_PDZ`
    de-asserted. The settings are recorded in case it is ever brought back:
    `MBIAS_VAL = 001` → P0_R59 D[6:4] → 3.014 V (VREF × 1.096, which requires
    `ADC_FSCALE = 00`), enabled via `MICBIAS_PDZ` → P0_R117 D7.
13. ⚠ **The firmware sequencing protection that used to exist here is gone, and
    the hardware clamp is now the only cover.** The blocking caps at the
    converter inputs are polarised tantalums, oriented positive toward the
    converter because the converter's input common-mode (~1.375 V) sits above
    the preamp's 1.0 V bias point in every steady state.

    Previously the preamps drew their supply from MICBIAS, so firmware could
    guarantee the converter's common-mode was established first simply by
    enabling the channels before MICBIAS. **The preamps now take the 3.3 V
    analog rail, so they may be live before the converter is configured at all**
    — a wider transient window than the one this ordering closed, and one
    firmware cannot close. The parallel clamp diode across each blocking cap is
    what covers it, and it is therefore required rather than insurance
    (`adc-netlist.md` §2, §11 item 2).

    **Power the input channels early in the bring-up sequence regardless.** It
    shortens the window even though it no longer eliminates it.
    Everything else about MICBIAS is configured in the bulk write as normal.
    `INCAP_QCHG` is already set by then, so the caps charge to the common-mode
    on channel power-up as intended.

    MICBIAS can also be gated directly from a GPIO without I²C if that turns out
    to be useful for power management — the same ordering constraint applies to
    that path.

### 3.5 Serial audio interface

14. **Format:** TDM (`ASI_FORMAT = 00`, default), word length 32-bit
    (`ASI_WLEN = 11`, default) → P0_R7. Leave FSYNC and BCLK polarity at
    defaults unless bring-up shows otherwise (§4).
15. **Slot assignment:** device A channels 1–4 → slots 0–3, device B channels
    1–4 → slots 4–7. `CHx_SLOT` → P0_R11–R18. **The slot map doubles as the
    string map** — slots 0–3 are neck E/A/D/G, slots 4–7 bridge E/A/D/G.
16. **Tri-state unused slots** on both devices (`ASI_OUT_CH_EN`), plus
    `TX_FILL` = Hi-Z on unused cycles. Each device drives only its own four
    slots on the shared data line.
17. **Bus keeper** (`TX_KEEPER`, `ASI_CFG1` bits 6:5) — settings 2 or 3 restrict
    it to the LSB window so the host latches the final bit cleanly without two
    devices contending at a slot boundary. This replaces any external bus-hold
    part; the optional pull-down on the data net is a DNP footprint covering
    only the pre-configuration window (`adc-netlist.md` §5).
18. **`TX_OFFSET`** (P0_R8 D[4:0]): default 0. TI recommends a non-zero offset
    at higher bit-clock rates; at 8.192 MHz the default should be fine, but this
    is the first knob to reach for if MSB corruption appears (§4).
19. **Channel enable and ADC power-up last**, after clocks are running and
    verified.

---

## 4. SAI4_B driver configuration

**Master receiver.** SAI4_B generates BCLK and FSYNC and receives data on the
shared data line from both converters.

- **Domain note:** SAI4 is in the D3 domain, so capture DMA is via **BDMA** with
  buffers in **SRAM4** (`pin-allocation.md` §1). At 8 channels × 32 samples ×
  4 bytes double-buffered this is a few KB against SRAM4's 16 KB — comfortable.
  D-cache coherency for that region is handled in the platform layer; either
  place the buffer in an MPU non-cacheable region or invalidate explicitly on
  the RX half before reading.
- **Frame:** 8 slots × 32 bits = 256 BCLK per frame, FSYNC at 32 kHz →
  BCLK 8.192 MHz. This ratio is explicitly in the converter's supported
  auto-detect table.
- **Kernel clock:** PLL3_P at 24.576 MHz, divided by 3 in the SAI
  (`pin-allocation.md` §1). Capture and playback are frequency-locked by
  construction because both peripherals' kernel muxes select PLL3_P.
- **Slots:** all eight enabled, 32-bit slots, data size 32 (or 24-in-32 —
  decide alignment once and document it).
- **Frame geometry.** The converter transmits slot-0 MSB aligned to the FSYNC
  rising edge with `TX_OFFSET = 0`, and data transitions on the BCLK rising
  edge, so the SAI should sample on the falling edge. Configure FS as a pulse —
  one BCLK wide is supported, multiples also work — with the frame-offset and
  polarity settings placing the FS rising edge at the start of slot 0.
- **The classic bring-up bug is a one-bit or one-slot rotation.** Fix it from
  the SAI frame-offset and slot configuration *first*, and from the converter's
  `TX_OFFSET` only second. **Do not adjust both ends at once** — that turns a
  one-variable problem into a two-variable one.
- **Data format:** samples are MSB-first two's complement, arriving interleaved
  as one frame of eight channels per sample period.

⚠ Verify SAI4_B master-receiver TDM configuration and BDMA request routing
against RM0468 at bring-up (`pin-allocation.md` §1).

---

## 5. Bring-up sequence

1. Hold the shutdown line low — the hardware pull-down does this at power-on.
   Bring the rails up.
2. Release shutdown via GPIO and wait per the datasheet (order of milliseconds).
3. **I²C only.** Probe both device addresses; both must acknowledge. Nothing
   else is worth attempting until this passes.
4. Write the full configuration (§3) to both devices. Clocks may be stopped
   during configuration — the auto-clock detector runs when clocks appear.
5. Start the SAI4_B master clocks.
6. **Read `ASI_STS` (P0_R21) on both devices.** This confirms the auto-detected
   FSYNC frequency and BCLK-to-FSYNC ratio were accepted. An unsupported
   combination raises a clock-error interrupt and mutes the channels. **This
   read is what cleanly separates "converter misconfigured" from "SAI
   misconfigured" — both otherwise present as silence**, and it is the single
   highest-value diagnostic in the sequence.
7. Enable channels and power up the converters — broadcast write if simultaneous
   start matters. The input common-mode comes up here and the blocking caps
   quick-charge to it.
8. **Then, and only then, assert `MICBIAS_PDZ`** to bring up the buffer rails.
   ⚠ Reversing steps 7 and 8 reverse-biases the input blocking caps for the
   duration of the gap — see §3.4 item 13.
9. **Prove slot steering with one device before enabling the second**
   (`multichannel-audio-board-plan.md` risk register). Then inject a known
   signal into one neck and one bridge channel and confirm, in order: slot
   positions, channel order, polarity.

---

## 6. Bench verification

- **Measure the actual low-frequency corner per channel.** The internal 20 kΩ
  input impedance has loose tolerance, so 1.7 Hz is nominal only.
- **Confirm quick-charge settings** by watching the baseline settle after
  channel enable with the 4.7 µF blocking caps fitted.
- **Noise floor per channel at operating gain, radio on versus off.** This is
  what validates the preamp boards' input RC filters (`preamp-board.md` §7),
  and it is the identified risk to the front-end design.
- **Check inter-device sample alignment** using the same physical event on the
  neck and bridge coils of one string. Apply phase calibration only if a
  measurable offset exists.

---

## 7. DSP-side notes

Downstream of the driver, but recorded here because they are the other half of
the low-frequency decision:

- **Do DC removal in the digital domain**, first-order high-pass at roughly
  0.2–0.5 Hz — **not** in the converter's HPF. Keeping the converter path wide
  open means the feature extractor can see the raw signal if it wants it, and
  the final trim happens where it can be changed without touching hardware
  configuration.
- **Per-channel DC offsets are now small.** The front end's offset is tens of
  microvolts rather than a five-to-one semiconductor spread, and the coupling
  caps block it regardless. Any residual offset is the converter's own. Treat as
  per-channel calibration constants, estimable at idle, but do not expect the
  magnitudes this step was originally sized for. ⚠ Under `adc-netlist.md` §2.1
  the coupling caps are gone and the front end's offset does reach the converter
  — still tens of microvolts, so the conclusion is unchanged, but the DC removal
  above stops being optional.
- ⚠ **No low-frequency correction is required for the preamp, and none should be
  written.** An earlier revision of `analog-front-end.md` specified a 17.9 dB
  shelf inversion on the analysis branch to undo a gain-network shelf. **That
  shelf no longer exists** — the front end is DC-coupled and flat to DC
  (`analog-front-end.md` §6). Writing the correction anyway would boost 18 dB of
  nothing, and the converter's residual offset with it.

---

## 8. Where the rest lives

| Topic | Document |
|---|---|
| Why this converter, and its documentation links | `adc-selection.md` |
| Input stage, coupling caps, corner, per-pin connections, BOM | `adc-netlist.md` |
| ⚠ The open DC-coupled differential proposal and its register table | `adc-netlist.md` §2.1 |
| Preamp reference architecture and distribution | `../OPA376 String Preamp/reference-architecture.md` |
| The per-string preamp boards feeding it | `preamp-board.md` |
| Why that front end amplifies rather than buffers | `analog-front-end.md` |
| SAI/I²C/GPIO assignment and the PLL3 clock tree | `pin-allocation.md` |
| Firmware effort estimate and risk register | `multichannel-audio-board-plan.md` |
| Probe points on the capture bus | `test-points.md` |
