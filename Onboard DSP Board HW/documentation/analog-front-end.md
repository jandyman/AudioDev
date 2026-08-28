# Analog Front End — Design Basis

**Status:** Committed. The per-string front end is a low-noise operational
amplifier with gain, sited at the pickup. The circuit is `preamp-board.md`.

⚠ **Revised 2026-08-26.** The stage is DC-coupled from a buffered reference; §6
is rewritten around that and the low-frequency shelf argument it previously
carried is withdrawn. §6.3 raises a proposal to carry the reference to the
converter and delete the coupling network as well.

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
| Quiescent current | 760 µA | eight channels plus two reference buffers is 7.6 mA — see §7 |
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

With an operational amplifier the output rests at whatever the reference is set
to. **Specify 1.0 V**, from a divider on the analog rail, filtered at its tap and
buffered (§6.1).

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

⚠ **That rule exists only to protect a polarised coupling capacitor, and the
proposal in §6.3 deletes the capacitor.** If it is adopted the rule goes with it
and the value stops being a downstream constraint at all. It is then set by three
things that can be written down — the amplifier's input common-mode ceiling at
(V+) − 1.3 V, its output swing requirement, and the converter's preference for
its own reference midpoint — which between them give an allowed window of
0.71 V to 1.98 V with a midpoint of 1.345 V, against a converter preference of
**1.375 V**. The two agree to within 30 mV, so nothing is traded: 1.375 V is
3 dB better than 1.0 V on the binding downward swing and still 625 mV clear of
the common-mode boundary, and the change is the divider's bottom leg alone
(100 kΩ / 71.5 kΩ). Derivation, headroom arithmetic and the rail-rejection
invariance are `preamp-board.md` §5. **Do not move the value while the coupling
network stands**; move it as part of adopting the proposal.

**And once it moves, the bias point stops interacting with the gain.** The
stage's DC gain to the reference is exactly one, so the operating point is the
reference whatever the AC gain is, and the reference is set by the converter
rather than by a coupling network. Gain can be retuned after simulation or bench
measurement without reopening the bias question — which is not a small
convenience, because gain is the one lever with real range if headroom turns out
tight.

---

## 6. Consequence: the front end is DC-coupled

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

**All of which remains true, and is no longer the reason the stage is
DC-coupled.** The stage is DC-coupled because the capacitor that would have made
it otherwise turned out to be indefensible on its own terms, and removing it cost
nothing. §6.1 is that argument.

### 6.1 Why the gain-leg capacitor went, and what replaced it

The superseded stage returned its lower gain leg to ground through a 22 µF Class
II part, and both this document and `preamp-board.md` waved that part through as
a deliberate, called-out exception to an otherwise strict Class I rule. The
justification given was that although it carries signal current, the voltage
developed across it in band is a few millivolts — "effectively no voltage across
it to be non-linear about".

**That justification does not survive contact with the two mechanisms it was
meant to answer, and it fails differently against each.**

- **It is a signal-path part by the only definition that matters.** It carries the
  whole gain-setting current, so its capacitance *is* the gain network's low
  corner. A high-K dielectric in a small package loses the majority of its
  nominal capacitance under bias, and this part sits with about a volt across it
  — the inverting input rests at the bias point and the far end is at ground.
  Losing capacitance moves the designed corner and steepens the local slope that
  produces distortion. The "few millivolts of signal" argument bounds the
  distortion; it says nothing about the corner.
- **Piezoelectric generation is a source, not a non-linearity, so it does not
  scale down with signal.** §8 of this document had already worked out that a
  voltage developed across this part is referred to the input at
  Rf/(Rf+Rg) = 0.87 — essentially one for one — and had used exactly that
  arithmetic to reject a *larger* Class II part in the same position. The same
  arithmetic condemns the part that was there. Holding both positions at once was
  the error: the small-signal argument answers voltage coefficient and was
  silently reused against microphonics, which it does not touch.

**Provenance.** The inconsistency was raised externally — Gemini disputed the
assertion that this part was essentially not a signal-path capacitor — and it
held up. What followed is larger than the part: the natural repair is not a
better dielectric but **no capacitor at all**, and once the leg has to return
somewhere other than ground through a capacitor, returning it to a buffered
reference is both the cheapest option and the one that makes the stage flat to
DC. A defect in a justification therefore produced a topology improvement, and
the same reasoning is now propagating to every other large capacitor in the
system, the converter's coupling network included (§6.3).

**The replacement.** A divider on the analog rail, filtered at its tap and
buffered, distributed as a strip-wide reference; the coil cold ends and the lower
gain legs both return to it. Circuit and values are `preamp-board.md` §3 and §8;
the distribution and supply filtering are in
`../OPA376 String Preamp/reference-architecture.md`.

**What it costs and what it buys.** One amplifier and one capacitor per board,
against four capacitors deleted. Reference-borne noise now reaches the output at
a gain of exactly one while the signal sees the full stage gain — a 17.9 dB
ratio, where biasing the non-inverting input from a bare divider would have put
it at Rf/Rg ≈ 6.8. **That ratio is not a rejection**; nothing cancels, it is
bounded by the stage gain, and it shrinks if the gain is lowered. Turning it into
a real rejection is what the proposal in §6.3 is for.

### 6.2 What is left below 10 Hz

**The preamp contributes nothing.** No pole, no zero, no shelf; the stage is flat
to DC and its DC gain to the reference is exactly one.

⚠ **This supersedes the shelf analysis previously in this section** — a zero at
0.42 Hz, a pole at 3.29 Hz, unity gain at DC and −17.9 dB of relative loss below
the corner — together with the 17.9 dB digital correction that was specified on
the analysis branch to undo it, and the statement that the two low-frequency
corners compound to −3 dB at about 3.9 Hz. **There is now only one analog
corner.** No low-frequency correction is required in the processor for the
preamp, and none should be written.

**The converter's coupling network is the whole of what remains**: 4.7 µF into
the programmable 20 kΩ input impedance, a genuine zero at DC with a corner at
**1.69 Hz** (`adc-netlist.md` §2). Below it the chain loses content that no
downstream correction recovers exactly, because a true high-pass has no bounded
inverse at DC — unlike the shelf it replaced, which did.

**The digital high-pass in the converter is still the one loss that no correction
can undo at all**, because it discards content before the processor sees it.
Requirements are unchanged: `adc-netlist.md` §8.

### 6.3 Consequence: the converter's coupling network is now the odd one out

Everything the front end gains from DC coupling — no tolerance-mismatched phase
shift at the low fundamentals, no time constant tilting the baseline under an
attack transient in exactly the window an envelope or attack estimator reads — is
given back at the converter, by eight polarised capacitors whose value tolerance
is ±20% and whose corners therefore differ string to string.

⚠ **PROPOSAL (2026-08-26): carry the instrument's reference to the converter's
cold input pins on one added conductor and take the converter's inputs DC-coupled
differential.** The buffer on the pickup board exists already — it becomes a
re-buffer of an incoming reference rather than the generator of a local one — so
the board-side cost is one conductor and one connector position. It deletes the coupling capacitors, their clamp diodes and their
matching capacitors — a material area saving on a control-cavity board where area
is the binding constraint — removes the last analog high-pass in the chain, and
converts the reference from an unrejected common term into a common-mode one that
the converter's own rejection subtracts. The argument, the register settings, the
open checks and the retrofit path are `adc-netlist.md` §2.1;
`preamp-board.md` §4 covers the board side.

**The reference is generated at the far end, not on the pickup board**, and the
reason comes from the other instrument entirely. The control-cavity board blends
two pickups into one output, so its signal chain has exactly one reference node;
two independently generated references differ by divider tolerance and a blend
control puts that difference across a wiper as a DC step, which no tolerance
budget removes. The pickup boards are identical in both instruments, so the
instrument that has the requirement sets the direction for both. The converter
instrument has no such requirement of its own — its two references never meet,
and the digital high-pass removes any DC difference — and the term it gives up by
reversing is inter-string crosstalk at about −93 dB, which the pickup board's
local re-buffer then reduces to −108 dB. Both sit below the front end's own noise
floor. `preamp-board.md` §3.1.

**Status: proposal, pending simulation and confirmation of the converter's
DC-coupled common-mode window.** Until it is adopted, the coupling network of
`adc-netlist.md` §2 stands as specified, and so does the bias point of §5 above.

### 6.4 Consequences for the hardware

- **Do not buy a low-frequency corner with noise.** The gain network's resistor
  values stay as specified. There is no longer a gain-leg capacitor to argue
  about, and the alternatives that were argued against it are recorded in §8 as
  history rather than as live options.
- **The converter's digital high-pass filter must be placed below the analysis
  band**, unchanged. `adc-netlist.md` §8.
- **The noise figure to budget against is not the 1 kHz one.** The analysis band
  sits in the amplifier's 1/f region, where the 7.5 nV/√Hz midband specification
  understates the floor. Budget against the 0.1–10 Hz peak-to-peak specification
  — §9 item 5. Note that the flicker corner extracted from the manufacturer's
  simulation model sits near 55 Hz, squarely inside the bass fundamental range.

## 7. Power

| Configuration | Eight channels | Context |
|---|---|---|
| Front end as specified | 7.6 mA | four channel amplifiers and one reference buffer per board, two boards |
| Superseded follower | 0.5–2.4 mA | |
| Commercial active bass, measured | 11.2 mA | more than this design |
| EMG active pickup pair | 0.16 mA | the exceptional low end of the field |

Under eight milliamps is comfortably inside normal practice for an active
instrument and below the measured draw of a mainstream commercial one. ⚠ The
6.1 mA previously stated here omitted the reference buffer. It also sits well under
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

**JFET input stage inside an operational amplifier's feedback loop.** Simulated
in full and parked. The circuit, the numbers and the conditions for revisiting
it are in `jfet-composite-front-end.md`; the LTspice model, netlist and
loop-gain bench are in `../simulation/jfet-composite-ltspice.zip`.

A matched dual N-JFET differential pair replaces the amplifier's own input
stage. Both circuit objections previously recorded here fail. The loop forces
the two drain currents equal and therefore the two gate voltages equal, so the
output rests on the bias reference across the whole Idss spread — the property
the follower could never have. And a lead-lag network across the drains gives
66 degrees of phase margin, with a four-degree sensitivity to 20 pF of stray at
each drain, so the compensation *can* be finalised on paper.

What survives is smaller than this entry previously claimed and differently
shaped: **1.8 dB of noise rather than three, and half the supply current rather
than a third.** In exchange there is a new obstacle, and it is about supply
rather than circuits — the topology needs a matched dual N-JFET satisfying
**|Vgs(off)| ≤ (rail) − (bias reference) − (drain drop)**, which is 1.46 V at
the values simulated. That rules out the low-noise audio duals, whose pinch-off
runs to −2 V and beyond, and it rules out the grade the fab stocks.

The decisive argument is unchanged. **The benefits are power and a modest noise
figure, and power is not what these boards are for.** Single-string coils exist
to serve the DSP system, whose processor and radio dominate the supply budget by
an order of magnitude. Revisit if RF rectification at the CMOS input proves to
be a real problem (§9 item 2), if a low-pinch-off matched dual becomes a stocked
low-cost part, or if a future application — most plausibly a multi-coil
commercial pickup rather than one coil per string — makes the front end the
dominant load.

**A low-cost general-purpose amplifier in place of the OPA376.** At 30 nV/√Hz
the front end reads 72 dB delivered — worse than the follower it would replace,
and no amount of gain recovers it, because the amplifier's own floor scales with
the signal. The part choice, not the topology, is what makes this design work.

**Pseudo-differential transmission to the cavity, a cold conductor per channel.**
The converter supports it, and it addresses §2.2 by rejection rather than by
level: 60 dB of common-mode rejection for 6 dB of full-scale utilisation, against
42 dB of available programmable gain. Rejection is usually cheaper than level. It
was not adopted because it needs a cold conductor per channel — nine conductors
instead of six — so it is a connector and cable change rather than a board
change, and the gain the front end now provides addresses the same exposure.
**This remains the correct fallback if bench measurement finds cable interference
to be a real problem**, and it requires no change to the pickup boards.

⚠ **Do not confuse it with the single-reference-conductor proposal of §6.3**,
which is a different mechanism aimed at a different term. That proposal rejects
what is common to the reference and every output — rail ripple through the
divider, buffer-impedance crosstalk, the inter-board ground offset — and deletes
the coupling network. It does **not** reject near-field pickup that differs wire
to wire in a loose bundle, and it introduces one exposure the present
arrangement does not have: interference captured by the reference conductor alone
arrives in all four channels at unity, where today the converter's cold pins sit
on a stiff local AC ground and have no injection path at all. The two options are
compatible and address different problems; adopting one does not settle the
other.

**The claim that a differential connection would cost converter channels is
false, and was blocking both options.** The converter records four analog
channels per device whether its four input pairs are configured differential or
single-ended; in single-ended mode the cold pin is not a second channel, it is an
AC ground behind a matching capacitor. The eight-per-device figure applies only
to digital microphones. `adc-netlist.md` §2.1.

**Finer magnet wire.** §1. Four decibels against a twenty decibel deficit, and no
improvement at all to the coil's own signal-to-noise ratio.

**Scaling the gain network's resistors to lower the shelf pole.** ⚠ **Recorded as
history — there is no shelf.** The stage is flat to DC (§6), so there is no pole
to move and this option no longer exists. Its arithmetic is preserved because the
conclusion it reached still governs the resistor values that remain: the feedback
network's thermal contribution referred to the input is √(4kT·(Rf‖Rg)), which at
the specified 1.92 kΩ is **5.6 nV/√Hz** — the second-largest term in the
10.5 nV/√Hz budget of §2.1, behind only the amplifier itself. Scaling both
resistors by k scales that term by √k: at 2× it reaches 8.0 nV/√Hz and has
overtaken the amplifier as the dominant source; at 3×, 9.8 nV/√Hz. **Do not scale
the gain network up.** The CMOS input does not object — 23 fA/√Hz through 4.4 kΩ
is a tenth of a nanovolt — so the objection is thermal noise alone.

**A larger low-voltage Class II capacitor in the gain leg.** ⚠ **Recorded as
history — there is no capacitor in the gain leg**, and the reasoning that would
have rejected a larger one is what removed the original (§6.1). The mechanism is
worth keeping in view because it now applies board-wide rather than to one part:
capacitance costs no thermal noise, so a higher value in the same footprint looks
free, and it is not. A Class II dielectric generates charge under mechanical
stress, that voltage appears in series with whatever it sits under, and unlike a
voltage coefficient the mechanism does not scale down with signal level. On a
board rigidly mounted to a struck instrument it is a microphonic path straight
into the signal, and it is the one respect in which raising the value makes
things worse. The board-wide rule that follows is `preamp-board.md` §9.

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

5. **Low-frequency noise, from the right specification.** ✅ **Closed as a
   datasheet reading; one bench number left.** The amplifier's 0.1–10 Hz
   specification is **0.8 µV peak-to-peak**, input referred — the 7.5 nV/√Hz in
   §1 is a 1 kHz figure and understates the floor in the 1/f region where the
   analysis band sits. Against the 40 mV peak-to-peak nominal-playing level that
   is 94 dB, so **the pull phase has roughly 54 dB of headroom below nominal
   playing before the amplifier's own low-frequency noise reaches 40 dB of
   signal-to-noise in the analysis band.**

   ⚠ **The shelf that this item previously had to reason around is gone** — the
   stage is flat to DC (§6), so the ratio at the input is simply the ratio at the
   output and no correction moves either. §6 therefore closes unless item 6 finds
   the pull phase more than about 54 dB down. ⚠ A first-principles
   estimate — finger draw at centimetres per second against string velocity at
   tenths of a metre per second — puts it 20 to 40 dB down, comfortably inside
   the budget, but that is an estimate and item 6 is the measurement. **No board
   change is expected to follow.**

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
| Reference architecture, distribution, supply filtering | `../OPA376 String Preamp/reference-architecture.md` |
| Symbol/footprint/model traps, capacitor policy, the rail-spectrum gate | project note *OPA376 String Preamp — simulation and pre-fab notes* |
| Noise budget worked by hand | `../OPA376 String Preamp/noise-by-hand.md` |
| Control-cavity analog board for the fallback instrument | `cavity-preamp-board.md` |
| Converter input stage, coupling network, main-board connections | `adc-netlist.md` |
| Why the converter, and what the architecture demands of it | `adc-selection.md` |
| Register configuration, gain calibration, bring-up | `adc-firmware-init.md` |
| Digital high-pass placement and the low-frequency correction | `adc-netlist.md` §8, `adc-firmware-init.md` §7 |
| Radio placement, cavity shielding constraints | `bluetooth-constraints.md` |
| Phase gates, bring-up order, risk register | `multichannel-audio-board-plan.md` |
| The superseded follower design, and its device characterisation | `superseded/preamp-board-jfet.md` |
| The JFET/amplifier composite: circuit, simulation, and what would bring it back | `jfet-composite-front-end.md` |
