# Analog Front End — Design Basis

**Status:** Committed. The per-string front end is a low-noise operational
amplifier with gain, sited at the pickup. The circuit is `preamp-board.md`.

**Scope:** the reasoning that spans the pickup boards, the converter and the
control-cavity electronics — why the front end amplifies rather than buffers,
what that decision requires of the supply and the coupling network, and what was
evaluated and rejected. The circuits themselves live in `preamp-board.md`
(per-string front end) and `cavity-preamp-board.md` (control-cavity analog
board). This document exists so that neither of those has to argue for itself.

**Why it is separate.** The front end was originally specified as a JFET source
follower — impedance conversion only, no gain. That design is complete and
preserved at `superseded/preamp-board-jfet.md`. The decision to replace it turns
on measurements and on a converter specification, not on anything visible in
either circuit, so the argument belongs in one place rather than distributed
through both as annotations.

---

## 1. Measured inputs

Everything below rests on three bench measurements of the pickup and one
datasheet figure. Where a number here is an assumption rather than a
measurement, it is marked.

| Quantity | Value | Note |
|---|---|---|
| Coil output, nominal playing | **40 mV peak-to-peak** | controlled comparison against a commercial pickup on the same instrument |
| Commercial pickup, same comparison | **400 mV peak-to-peak** | the reference the downstream world expects |
| Coil DC resistance | **320 Ω** | two coils in series |
| Coil inductance | **66 mH** | two coils in series |
| Converter input-referred noise at high channel gain | **1–2 µV** | ⚠ read from the axis range of Figure 14 (single-ended) in SBAS892A, not from the trace — **confirm before relying on it** |

**The pickup is 20 dB below a conventional one.** That single fact drives the
whole design. It is not a defect to be wound out: signal scales with turns while
resistance scales with turns times turn length, so for a fixed winding window
finer wire buys output and thermal noise in exactly equal measure. Going from
41 to 43 AWG would yield about 55% more turns for +4 dB of output and 2.5× the
DC resistance, leaving the coil's own signal-to-noise ratio unchanged. Gauge is
a trim, not a lever. **The 20 dB has to come from an amplifier.**

**Signal convention used throughout.** Peak-to-peak measurements are converted to
the equivalent RMS of a sine at that peak — 40 mV peak-to-peak becomes 14.1 mV.
Signal-to-noise figures are therefore peak-referenced, i.e. dynamic range, which
is the same convention the converter's own specifications use. Noise is
integrated over 20 kHz and A-weighted.

**The coil is nearly noiseless.** 320 Ω contributes 2.30 nV/√Hz, well below any
practical front end. There is no coil-imposed floor to design against; the
active device sets the noise.

---

## 2. The requirement: gain at the pickup

Three independent arguments converge on the same conclusion. Any one of them
would be suggestive; together they are decisive.

### 2.1 A buffer cannot deliver its own noise figure

This is the strongest argument and the least obvious. Consider what each
candidate front end achieves in isolation, and what actually arrives at the
converter:

| Front end | Its own ceiling | Delivered to the converter |
|---|---|---|
| JFET source follower | 85 dB | **74 dB** |
| Operational amplifier with gain | 82 dB | **81 dB** |

The follower is the quieter device — 7.11 nV/√Hz against 10.5, referred to the
coil. It is also the one that throws away eleven decibels, because without gain
the signal reaches the converter at 23 mV peak-to-peak, where the converter's own
1–2 µV input-referred noise becomes the system limit. Every front end that
provides gain lands within a decibel of its own ceiling; the one that does not
loses eleven.

**Gain at the pickup is not about improving the front end. It is about allowing
a front end to deliver what it already has.**

This also forecloses the follower structurally rather than by judgement. Its
ceiling in the delivered column is set by the converter's noise floor, and
Figure 14's axis does not go below 1 µV. Even at the most favourable value the
plot admits, the follower reaches about 77 dB — still short. No value of the
unknown reverses the ordering.

### 2.2 Interference on the cable run

The cable from each pickup to the control cavity is short, unshielded and loose,
and it passes within inches of a Bluetooth module's antenna in a cavity that
cannot be shielded (`bluetooth-constraints.md`). Interference coupled onto that
run is *additive* — it does not scale with the signal — so gain applied ahead of
the cable improves signal-to-interference by the full amount of the gain, with
nothing working against it.

This is categorically different from the thermal analysis above, where an
amplifier's own noise scales with its gain and the ratio is unchanged. Against
interference there is no such cancellation. It is the one place where more gain
is unambiguously better, and it is the reason to prefer gain of 8 over the gain
of 2 that would already be sufficient to swamp the converter.

For scale: at unity the cable would carry 25 mV peak-to-peak. A conventional
instrument's wiring carries 400 mV from a source impedance of kilohms. With gain
the cable carries 320 mV from an operational amplifier's output impedance — more
signal *and* lower source impedance than the conventional case that is known to
work.

### 2.3 The control-cavity board's summing loss

The analog cavity board sums four channels per pickup passively, which costs
12 dB, ahead of its first gain stage. With a unity front end that loss lands on
a signal already 20 dB light, and the cavity board reads 63 dB. With gain at the
pickup the same board reads 75 dB without a component changed, and its own
contribution falls to about one decibel of the total.

The converter path avoids this entirely — each channel reaches its own
programmable gain amplifier before any summing occurs, and summation happens in
the digital domain where it is noiseless. That asymmetry is worth stating because
it explains why the analog board is the harder case despite being the simpler
one.

---

## 3. Why an operational amplifier and not a JFET gain stage

The superseded design rejected a gain stage, and that rejection was correct for
the device it considered. It does not extend to an operational amplifier.

A JFET common-source stage sets its drain at the supply less the product of drain
current and drain load. Drain current varies five to one across the Idss
distribution of any device in this class, so on a 3 V rail the drain lands
anywhere from roughly 2 V to below ground depending on which part is fitted.
That is unworkable rather than merely inelegant. The stage would also present a
drain-load output impedance in the kilohm range, which makes the cable *more*
susceptible to capacitive coupling — so it would buy signal in §2.2 and give back
more than it bought.

An operational amplifier has neither problem. Gain is a resistor ratio, exact and
matched channel to channel to the tolerance of the resistors. Output impedance is
ohms. Offset is tens of microvolts rather than a five-to-one spread.

**Device: OPA376** (Texas Instruments), SC70-5 or SOT-23-5.

| Parameter | Value | Why it matters |
|---|---|---|
| Voltage noise at 1 kHz | 7.5 nV/√Hz | sets the system noise floor (§2.1) |
| Quiescent current | 760 µA | eight channels is 6.1 mA — see §7 |
| Supply range | 2.2–5.5 V | operates on the 3.3 V analog rail |
| Gain bandwidth | 5.5 MHz | 690 kHz at the gain used; ample |
| Power supply rejection | 86 dB typ, >80 dB across the audio band | this is what frees the supply choice (§4) |
| Input | CMOS, 23 fA/√Hz | the coil's rising impedance costs nothing |
| Common-mode range | specified to (V+) − 1.3 V | bounds the bias point (§5) |

The part is stocked as an LCSC extended part at roughly $1. At eight per
instrument this is not a consideration; it would become one only if the design
moved to volume.

---

## 4. Consequence: the boards run from the 3.3 V analog rail

The superseded design took the buffer supply from the converter's MICBIAS
output. The justification was noise isolation and nothing else — it explicitly
ruled out regulation as a factor — and it was necessary because a source
follower ties its drain straight to the supply and rejects almost nothing.

An operational amplifier rejects more than 80 dB across the audio band. **The
justification does not survive the device change.** The pickup boards take the
3.3 V analog rail.

Three costs recorded against MICBIAS in the superseded design disappear with it:
the boards no longer depend on their converter being brought up over I²C before
they have power, a converter fault no longer takes its own pickup down, and the
mic-bias current budget stops being a question that needs answering.

What is given up is real but small: MICBIAS provided current limiting that
protected the system rail from a crushed pickup wire, and a firmware power switch
for free. If either is wanted back, a load switch or a resettable fuse restores
it at one part per board.

---

## 5. Consequence: the bias point is a design variable

A self-biased source follower's DC output is whatever its gate-source voltage
happens to be — 0.13 to 0.67 V across the part distribution, uncontrollable, and
the origin of a selection rule, a clamp diode, a startup sequencing constraint
and a downstream calibration step.

With an operational amplifier the output rests at whatever the bias divider is
set to. **Specify 1.0 V.**

That value is chosen, not inherited. It places the front-end output below the
converter's self-bias of 1.375 V by 375 mV, which:

- **preserves the coupling capacitor's polarity** as already drawn in
  `adc-netlist.md` — the converter side remains the positive one, so nothing
  about the coupling network or its clamp diode changes;
- **provides a healthy bias** on the polarised coupling part, rather than the
  132 mV that a naive mid-rail choice on a 3.0 V supply would have given;
- **keeps the amplifier's input inside its specified common-mode region**, well
  clear of the (V+) − 1.3 V boundary above which common-mode rejection is not
  guaranteed;
- **costs only asymmetric swing** — roughly 950 mV downward against 2.25 V
  upward, against signal peaks of 160 mV. Six times the margin required.

The selection rule in the superseded design — that a substitute device's
gate-source pinch-off voltage must sit below the converter's input bias — is
replaced by something simpler and enforced by a resistor ratio: **the front-end
bias point must sit below the converter's input bias, with margin.**

---

## 6. Consequence: the low-frequency corner is a digital problem

The requirement that sets the front end's low-frequency behaviour is the capture
of the pluck as the string is released — the finger drawing the string aside and
the moment it lets go. That requirement has been carried through this project as
a demand for near-DC analog response. **The framing is wrong, and it is worth
writing down why, because acting on it buys expensive analog parts that fix
nothing.**

**A magnetic pickup is a velocity transducer.** Its output is
−N·(dΦ/dx)·(dx/dt): flux linkage varies with string position, and a voltage
appears only while that position is changing. A string held statically at any
displacement, however far it has been pulled aside, produces exactly zero volts.
The transducer therefore carries a first-order zero at DC of its own, ahead of
every capacitor in the chain.

**Nothing below the coupling corners is being lost, because the pickup never
generates it.** What a release event presents is a velocity transient: a small,
slow signal while the finger draws the string aside, and a large fast one at the
moment of release. Both are alternating. The design question is therefore not
how close to DC the chain reaches, but whether the slow portion arrives with
usable signal-to-noise. That is a level question, settled in the noise budget —
not a corner-frequency question to be settled with capacitance.

### 6.1 What the specified chain does below 10 Hz

Two shaping mechanisms sit between the coil and the converter's digital output,
and they are different in kind.

**The gain network is a shelf, not a high-pass.** With the specified 15 kΩ
feedback resistor, 2.2 kΩ lower leg and 22 µF return capacitor, the stage has a
zero at 0.42 Hz and a pole at 3.29 Hz. Gain falls from eight in the passband to
**unity at DC** — it does not fall to zero. Relative to the passband the −3 dB
point is **3.24 Hz** and the response flattens at **−17.9 dB** below it.

**The converter's coupling network is a true high-pass.** 4.7 µF into the 20 kΩ
programmable input impedance gives a genuine zero at DC with a corner at
**1.69 Hz** (§2 of `adc-netlist.md`).

Cascaded, the two corners sit close enough together to compound: the system
reaches −3 dB at about **3.9 Hz** and −9.6 dB at 1.7 Hz. Two poles this close is
the least efficient arrangement available — it doubles the phase contribution
and reaches barely lower than one of them alone.

### 6.2 The shaping is recoverable; the correction belongs in the processor

Both mechanisms are fixed, minimum-phase and bounded. The shelf inverts exactly
with one pole and one zero, and its 17.9 dB span is the whole of what the
correction has to supply. **Recover the low-frequency shape digitally rather
than in copper.**

**Apply the correction on the analysis branch only, not in the signal path.**
The low-frequency content exists to serve onset detection and pluck
characterisation; nothing in the audio path needs it. Correcting before the
branch would push 17.9 dB of subsonic boost, and the converter's own residual
offset with it, into audio that has no use for either.

**This forecloses the converter's biquads as the place to do it.** Their output
is the single stream both paths derive from, so a correction there is
necessarily in the signal path. It belongs in the processor, downstream of the
branch, which is also where the existing signal-node probing convention puts it.

**The noise arithmetic is favourable, and for a structural reason.** The
analysis branch is band-limited to a few tens of hertz, so it integrates noise
over roughly 20 Hz where the audio path integrates over 20 kHz — about 30 dB of
margin before anything is spent. The 17.9 dB of correction sits comfortably
inside it.

### 6.3 Consequences for the hardware

- **Do not buy the low-frequency corner with noise.** The gain network's
  resistor values, the gain leg return capacitor and the converter blocking cap
  all stay as specified. The alternatives, and what they cost, are in §8.
- **The converter's digital high-pass filter must be placed below the analysis
  band.** It is the one low-frequency loss in the chain that no downstream
  correction can undo, because it discards the content before the processor sees
  it. Requirements are in §8 of `adc-netlist.md`.
- **The noise figure to budget against is not the 1 kHz one.** The analysis band
  sits in the amplifier's 1/f region, where the 7.5 nV/√Hz midband specification
  understates the floor. Budget against the 0.1–10 Hz peak-to-peak
  specification — §9 item 5.

---

## 7. Power

| Configuration | Eight channels | Context |
|---|---|---|
| Front end as specified | 6.1 mA | |
| Superseded follower | 0.5–2.4 mA | |
| Commercial active bass, measured | 11.2 mA | more than this design |
| EMG active pickup pair | 0.16 mA | the exceptional low end of the field |

Six milliamps is comfortably inside normal practice for an active instrument and
below the measured draw of a mainstream commercial one. It also sits well under
the threshold the superseded design used when it rejected a higher-current JFET
class on battery grounds — that objection was framed at 16 to 40 mA and does not
reach this.

On the instrument the front end is powered continuously while the instrument is
plugged in, so battery life is plugged-in time rather than elapsed time.

---

## 8. Evaluated and not adopted

**JFET source follower, no gain.** Complete and preserved at
`superseded/preamp-board-jfet.md`. The quietest front end available here and
still the wrong one, for the reason in §2.1. It also remains the reference for
the device characterisation — the Idss and gate-source spread analysis in its §2
exists nowhere else, and would be needed by any future composite (below).

The condition under which it returns is compound and narrow: RF rectification
would have to rule out a CMOS input *and* the composite below would have to prove
unstabilisable. Recorded so the option is retrievable, not held open.

**JFET input stage inside an operational amplifier's feedback loop.** A
genuinely better circuit on paper — roughly 8 nV/√Hz at about 220 µA per channel,
so three decibels quieter than the specified part at a third the current, using a
low-cost amplifier. The JFET becomes the input device; the amplifier supplies
only open-loop gain, DC accuracy and output drive, and its noise is referred back
divided by the JFET stage's gain. The JFET's operating point is set by the loop
rather than by Idss, which is what makes a common-source stage viable on 3 V at
all.

Not adopted, for three reasons. Its headline noise figure is conditional on the
JFET stage reaching a gain of roughly six — below that the amplifier's noise
dominates and the composite ends up *worse* than the single-amplifier design.
Stabilising a gain stage inside a feedback loop requires a compensation network
whose values depend on drain-node capacitance, hence on layout, so it cannot be
finalised on paper. And it occupies roughly 50% more board area per channel.

The decisive argument is none of those: **the only benefit is power, and power
is not what these boards are for.** Single-string coils exist to serve the DSP
system, whose processor and radio dominate the supply budget by an order of
magnitude. Optimising the analog fallback's current draw optimises the wrong
thing. Revisit only if a future application makes the front end the dominant
load.

**A low-cost general-purpose amplifier in place of the OPA376.** At 30 nV/√Hz
the front end reads 72 dB delivered — worse than the follower it would replace,
and no amount of gain recovers it, because the amplifier's own floor scales with
the signal. The part choice, not the topology, is what makes this design work.

**Pseudo-differential transmission to the cavity.** The converter supports it,
and it addresses §2.2 by rejection rather than by level: 60–80 dB of common-mode
rejection for 6 dB of signal, against 42 dB of available programmable gain.
Rejection is usually cheaper than level. It was not adopted because it needs a
cold conductor per channel — nine conductors instead of six — so it is a
connector and cable change rather than a board change, and the gain the front end
now provides addresses the same exposure. **This remains the correct fallback if
bench measurement finds cable interference to be a real problem**, and it
requires no change to the pickup boards.

**Finer magnet wire.** §1. Four decibels against a twenty decibel deficit, and no
improvement at all to the coil's own signal-to-noise ratio.

**Scaling the gain network's resistors to lower the shelf pole.** Holding the
gain leg return capacitor at 22 µF and raising both resistors in proportion
preserves the gain of eight and moves the pole down. It is rejected because it
spends noise in precisely the wrong place. The feedback network's thermal
contribution referred to the input is √(4kT·(Rf‖Rg)), which at the specified
1.92 kΩ is **5.6 nV/√Hz** — already the second-largest term in the 10.5 nV/√Hz
budget of §2.1, behind only the amplifier itself. Scaling by k scales that term
by √k:

| Scale | Feedback / lower leg | Shelf pole | Feedback noise | Total input-referred | Penalty |
|---|---|---|---|---|---|
| 1× (specified) | 15 kΩ / 2.2 kΩ | 3.29 Hz | 5.6 nV/√Hz | 10.5 nV/√Hz | — |
| 2× | 30 kΩ / 4.4 kΩ | 1.64 Hz | 8.0 nV/√Hz | 11.9 nV/√Hz | +1.1 dB |
| 3× | 45 kΩ / 6.6 kΩ | 1.10 Hz | 9.8 nV/√Hz | 13.2 nV/√Hz | +2.0 dB |

At 2× the feedback network has overtaken the amplifier as the dominant source.
Note that the CMOS input does not object — 23 fA/√Hz through 4.4 kΩ is 0.1 nV,
nothing — so this fails on thermal noise alone. It buys a corner that §6 shows
is recoverable for free.

**A larger low-voltage Class II capacitor in the gain leg.** Capacitance costs
no noise, so 47 µF or 100 µF in the same 0805 footprint would move the pole to
1.54 Hz or 0.72 Hz at no thermal penalty, and the part sees only about a volt so
a 6.3 V rating is amply derated. It is rejected on **piezoelectricity**, the
same mechanism that rules Class II out of the converter's coupling network. This
part already stands as a deliberate exception to the Class I rule; a
higher-capacitance dielectric in the same volume generates more charge under
mechanical stress, and a voltage developed across it appears in series with the
lower gain leg — referred to the input at Rf/(Rf+Rg) = 0.87, essentially one for
one. On a board rigidly mounted to a struck instrument that is a microphonic
path straight into the signal, and it is the one respect in which raising the
value makes things worse: the voltage-coefficient argument in `preamp-board.md`
§8 improves with capacitance, but piezoelectric generation does not, because it
is a source rather than a nonlinearity. **Retain 22 µF.** If the value is ever
revisited, tap-test the assembled board and observe the output before accepting
it.

---

## 9. Open questions

These are bench measurements, not analysis. Each is recorded against the
verification list of the document it affects.

1. **Confirm the converter's input-referred noise** at the channel gain actually
   used, from the trace of Figure 14 rather than its axis. This is the number the
   whole of §2.1 turns on. It does not change the ordering — the axis floor
   forecloses that — but it sets how much margin the design actually has.

2. **RF rectification at a CMOS input.** The RF treatment carried forward into
   `preamp-board.md` was reasoned around rectification at a JFET gate junction.
   A CMOS input rectifies too, possibly differently. This is the one identified
   risk that could invalidate the direction, and it is measurable only on the
   real board in the real instrument — a breadboard would not reproduce the RF
   environment.

3. **The coil's resonance with the input filter's shunt capacitor** — 62 kHz at a
   Q of roughly 20, a consequence of the coil's very low DC resistance. Out of
   band and removed by the converter's decimation filter, but it is 26 dB of gain
   for anything living near it, and the front end now amplifies it by eight
   rather than attenuating it. First place to look if an unexplained noise
   appears.

4. **Converter operating point.** At 320 mV peak-to-peak the source sits roughly
   17 dB below full scale rather than the 30–40 dB assumed when the converter was
   selected. The part clears the bar either way, but the programmable gain
   setting, and possibly the case for the Dynamic Range Enhancer, should be
   reconsidered against the real level.

5. **Low-frequency noise, from the right specification.** §6 argues that the
   analysis branch has ample margin for 17.9 dB of digital correction, and that
   argument rests on a noise figure this document does not yet carry. The
   7.5 nV/√Hz in §1 is a 1 kHz number and understates the floor in the 1/f
   region where the analysis band sits. Take the amplifier's **0.1–10 Hz
   peak-to-peak** specification and refer it to the pull-phase signal level.
   If it closes, §6 closes with it and no board change follows. This is a
   datasheet reading, not a bench measurement, and should be done before the
   next review gate rather than at bring-up.

6. **The pull-phase signal level itself.** The measured 40 mV peak-to-peak in §1
   is a nominal-playing figure. The slow draw before release is a far smaller
   velocity and no measurement of it exists. It is the numerator of item 5 and
   is measurable on the existing test board with the current front end — the
   coupling network's shaping is known and can be divided out.

---

## 10. Where the rest lives

| Topic | Document |
|---|---|
| Per-string front-end circuit, values, connector, layout | `preamp-board.md` |
| Control-cavity analog board for the fallback instrument | `cavity-preamp-board.md` |
| Converter input stage, coupling network, main-board connections | `adc-netlist.md` |
| Why the converter, and what the architecture demands of it | `adc-selection.md` |
| Register configuration, gain calibration, bring-up | `adc-firmware-init.md` |
| Digital high-pass placement and the low-frequency correction | `adc-netlist.md` §8, `adc-firmware-init.md` §7 |
| Radio placement, cavity shielding constraints | `bluetooth-constraints.md` |
| Phase gates, bring-up order, risk register | `multichannel-audio-board-plan.md` |
| The superseded follower design, and its device characterisation | `superseded/preamp-board-jfet.md` |
