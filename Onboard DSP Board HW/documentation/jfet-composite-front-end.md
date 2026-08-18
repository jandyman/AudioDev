# JFET / Operational-Amplifier Composite Front End — Parked Investigation

**Status:** Investigated, simulated, **not adopted**. The per-string front end
remains the single low-noise operational amplifier with gain specified in
`preamp-board.md`. This document exists so the work does not have to be redone
if the conditions in §7 are ever met.

**Scope:** the composite input stage recorded as an evaluated-and-rejected
alternative in `analog-front-end.md` §8 — what the circuit is, what simulation
established, the device-selection rule it turns on, and the conditions under
which it returns. The reasoning that governs the *adopted* design is in
`analog-front-end.md` and is not repeated here.

**Simulation.** LTspice schematic, netlist, loop-gain bench and device models
are in `../simulation/jfet-composite-ltspice.zip`. Results quoted below come
from that model; the amplifier macromodel reproduces both published noise
figures — 30 nV/√Hz at 1 kHz and 4.7 µVpp over 0.1–10 Hz — and the model of the
adopted design reproduces the 10.5 nV/√Hz hand budget of `analog-front-end.md`
§2.1 to within 0.15 nV, so the comparison is like for like.

---

## 1. The circuit

**A matched dual N-channel JFET differential pair replaces the amplifier's own
input stage.** One gate takes the coil, the other takes the feedback network,
the sources join at a tail resistor to ground, both drains are resistor-loaded
to the analog rail, and the two drains cross into the amplifier's inputs. The
amplifier supplies open-loop gain, DC accuracy and output drive only.

**The common-source inversion and the drain crossover cancel**, so the composite
behaves as an ordinary non-inverting amplifier whose input pins are the two JFET
gates. Everything downstream is therefore unchanged from `preamp-board.md` §8 —
same gain network, same shelf, same 1.0 V bias reference, same input filter,
same coil-as-bias-path arrangement.

**The drain-to-input assignment is load-bearing, not cosmetic.** Reversed, the
loop is positive: the feedback half turns off, the input half takes the entire
tail current, and the output sits on the negative rail. The channel is dead
rather than inverted. This makes the cheapest possible bring-up check also a
complete one — **if the output rests at the bias reference, the polarity is
right** — measurable with a meter and no signal.

## 2. What simulation established

Three things this was previously recorded as unknown or unfavourable on:

| | Previously assumed | Simulated |
|---|---|---|
| Input-referred noise | 8 nV/√Hz, three decibels quieter | 8.7 nV/√Hz, **1.8 dB**; 7.7 nV/√Hz (2.8 dB) with the gain network scaled down |
| Supply current per channel | 220 µA, a third of the adopted part | 384 µA, **half** |
| JFET stage gain required | six, below which the composite is worse | ten is available with margin |
| Low-frequency noise | not considered | **better**, not worse — see below |

**The low-frequency result is the surprising one.** A 4.7 µVpp amplifier lands
quieter than a 0.8 µVpp one: 0.62 µVpp against 0.82 µVpp input-referred over
0.1–10 Hz. The JFET stage divides the amplifier's 1/f contribution by the stage
gain, and the pair's own corner sits near 100 Hz. Whatever else is true of this
topology, it is not vulnerable in the analysis band.

## 3. The bias-point objection does not survive

The loop forces the two drain voltages equal, hence the two drain currents
equal, hence the two gate voltages equal. **The output therefore rests on the
bias reference, offset only by the pair's own gate-source mismatch, one for
one** — and does not move across the Idss spread at all:

| Grade corner | Source node | Drains | Output |
|---|---|---|---|
| Low Idss | 1.26 V | 2.56 V | bias reference |
| Typical | 1.43 V | 2.46 V | bias reference |
| High Idss | 1.75 V | 2.27 V | bias reference |

This is exactly the property the source follower could not have, and it is the
strongest thing the topology has going for it. The five-to-one Idss distribution
stops being a calibration problem and becomes invisible.

## 4. The stability objection does not survive either

The extra stage multiplies loop gain, and with it the crossover frequency, by
the stage gain — 903 kHz at 40° of phase margin, which rings.

**Treatment: a series resistor and capacitor across the two drains.** It is
differential only, so the common-mode path and its supply rejection are
untouched, and it removes a bounded 10.6 dB between a pole at 26 kHz and a zero
at 87 kHz rather than rolling off indefinitely. A plain capacitor would add a
second 90° of lag at crossover and trade ringing for oscillation; the zero
flattens the response before the loop gets there, so only the amplifier's
dominant pole contributes phase at crossover. Result: **345 kHz at 66°.**

Values follow from the loop, and — writing them in terms of the marked component
values, the factors of two from the differential connection having cancelled:

| | |
|---|---|
| Gain removed | 1 + 2·(drain load) / (compensation resistor) |
| Pole | 1 / (2π · compensation capacitor · (2·(drain load) + compensation resistor)) |
| Zero | 1 / (2π · compensation resistor · compensation capacitor) |

Put crossover about a decade under the amplifier's second pole, the zero about a
quarter of crossover, and the pole above the audio band. The in-band cost is
high-frequency loop gain, which is free here: the differential voltage across
the pair is a few hundred microvolts at 20 kHz against a linear range of
±160 mV, so there is no distortion to correct.

**The layout dependence recorded as un-finalisable on paper is swallowed by the
network.** The deliberate capacitance is 780 pF differential, so drain stray
moves phase margin by four degrees for 20 pF at each drain. It can be finalised
on paper after all.

## 5. What replaces those objections: a device selection rule

The pair's sources sit at the bias reference plus the gate-source voltage, and
the drains at the rail less the drain drop. Write the saturation condition and
the operating-point gate-source voltage cancels, leaving a rule on the pinch-off
voltage alone:

> **|Vgs(off)| ≤ (analog rail) − (bias reference) − (drain current × drain
> load).**

With the values simulated that is **1.46 V**, and every volt of drain drop
bought for stage gain comes straight out of that budget:

| Drain drop | Max \|Vgs(off)\| | Stage gain |
|---|---|---|
| 0.84 V | 1.46 V | 10.2 |
| 0.49 V | 1.80 V | 6.0 |
| 0.33 V | 1.97 V | 4.0 |

**This is the low-pinch-off constraint of the superseded follower reappearing at
the pair's tail**, and it eliminates the premium dual-JFET catalogue before
noise or price is considered — the low-noise audio duals run to −2 V and beyond
and will not bias on this rail. Only the low-Idss grades of a dual audio JFET
fit, and the grade the fab stocks is the wrong one: two of its three corners
leave saturation, and retuning the resistors to bias it forces the stage gain
down until the composite is **noisier than the single-amplifier design it would
replace**.

**Package and pinout do not carry across candidates.** A five-pin dual has
commoned one terminal and it must be the sources; six-pin duals bring both out.
There is no registered pinout. Lay out a six-pad land pattern — a five-lead part
drops into it with one pad unused — and treat a substitution as a re-route
rather than a footprint change.

**An escape exists if only a high-pinch-off grade is available.** Break the
unity DC gain with a resistor from the feedback node to ground and halve the
bias reference: the output still lands at 1.0 V, but the pair's common mode
drops with the reference and the whole grade fits with the full noise figure
recovered. It doubles the offset at the output, puts DC across a signal-path
resistor in violation of `preamp-board.md` §9, and adds a part per channel.
Recorded as available, not specified.

## 6. Scaling the gain network — a finding that outlives this circuit

The adopted design's noise budget is dominated by its amplifier, which is why
`analog-front-end.md` §8 argues only about the cost of *raising* the feedback
resistors. Once the amplifier terms fall, the two passives become the largest
contributors and the arithmetic reverses.

| Term | Adopted design | Composite |
|---|---|---|
| Amplifier | 7.50 nV/√Hz | ~3.5 (pair) + ~2.2 (amplifier ÷ stage gain) |
| Feedback network | 5.60 | 5.60 |
| Input series resistor | 4.07 | 4.07 |
| Coil | 2.30 | 2.30 |
| **Total** | **10.65** | **8.73** |

**Scaling the feedback network down by 2.2× buys 1.06 dB** and leaves the
feedback ratio, and therefore the compensation, untouched. Hold the gain leg
return capacitor at its present value rather than growing it — the shelf pole
moves from 3.3 Hz to 7.2 Hz, the shelf *depth* is unchanged because depth is the
gain ratio, and §6 of `analog-front-end.md` already establishes that corner as
recoverable on the analysis branch. This sidesteps the piezoelectric objection
entirely.

**Do not scale the input series resistor.** Its 4.07 nV is tempting and it is
load-bearing twice over. Holding the RF corner while lowering it drags the coil
resonance from 62 kHz down to 28.6 kHz, which puts **+3.3 dB of lift at 16 kHz**
— Nyquist at the converter's sample rate — and the provisioned damping network
does not fix it, because that lift is the resonance's skirt rather than its
peak. Keeping the shunt capacitor instead gives away the series element that is
the only part of the filter still doing anything at 2.4 GHz.

## 7. Conditions under which this returns

Sharp enough to check rather than judge:

1. **RF rectification at the CMOS input proves to be a real problem**
   (`analog-front-end.md` §9 item 2). The RF treatment in `preamp-board.md` §7
   was reasoned about a JFET gate junction and this circuit returns to that
   structure. **A gate junction is not established to be quieter under RF** — a
   junction conducts where an insulated gate does not, and CMOS inputs are
   generally the better of the two on interference rejection. The argument is
   only that this is the structure the analysis was done for, and that having
   both boards gives a controlled comparison on one instrument.
2. **A low-pinch-off matched dual becomes a stocked, low-cost part.** §5 is the
   whole test; nothing else needs revisiting.
3. **The front end becomes the dominant load.** That is a different product —
   most plausibly a multi-coil commercial pickup rather than one coil per
   string, or a version of this system whose processor and radio do not dominate
   the supply budget. Single-string coils serving this DSP system are not it.

Cost is not on this list. At the fab's prices the composite lands near $0.70 a
channel against $2.15, which is a couple of dollars an instrument and should not
be used to carry the argument either way.
