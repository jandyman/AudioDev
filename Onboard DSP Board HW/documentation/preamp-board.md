# Pickup Preamp Boards — Design

**Status:** Specified. Two identical 4-channel boards, one per pickup (neck,
bridge), each mounted under its pickup bobbin.

⚠ **Revised 2026-08-26 to the buffered-reference, DC-coupled stage.** The stage
specified here has no capacitor in the gain leg and no high-pass anywhere in the
preamp. That decision was taken in the simulation work and recorded next to the
schematic — `../OPA376 String Preamp/reference-architecture.md` and the project
note *OPA376 String Preamp — simulation and pre-fab notes* — and this document
had not been reconciled to it. Sections 3, 8 and 9 previously specified a gain
leg returning to ground through a capacitor and an unbuffered, bypassed divider;
both are superseded. The reasoning that produced the change is in
`analog-front-end.md` §6.

**Scope:** the offboard per-string front-end boards — the circuit, the
per-channel values, the connector and cable to the control cavity, and the
layout rules specific to these boards. The main board's converter input stage,
coupling network and connections are **not** here — see `adc-netlist.md`.
Main-board layout is `layout-notes.md`.

**The reasoning is not here either.** Why the front end amplifies rather than
buffers, why it runs from the analog rail, and why the bias point is where it is
are all argued in `analog-front-end.md`. This document specifies the board.

---

## 1. What these boards do

**One amplifier per string coil, providing gain.** Each channel presents an
effectively infinite input impedance to its coil, applies a gain of
approximately eight, and drives the cable to the control cavity from an output
impedance of ohms.

The gain is the point. The pickup delivers about 40 mV peak-to-peak — some 20 dB
below a conventional pickup — and everything downstream is quieter than the
front end only if the front end is allowed to lift the signal first. A unity
buffer would throw away eleven decibels at the converter and twenty-two at the
analog cavity board (`analog-front-end.md` §2).

**Every channel is identical, and identical by construction.** Gain is a
resistor ratio, so channel-to-channel spread is the tolerance of the resistors
rather than a property of the semiconductor. Offset is tens of microvolts. This
is what allows per-channel correction downstream to be a small trim rather than
a calibration step.

---

## 2. Device

**OPA376** (Texas Instruments), SC70-5 or SOT-23-5, one per channel.

The governing requirements are voltage noise, operation from a 3.3 V single
supply, and a CMOS input. Noise sets the system floor once gain is present, so
this is the one parameter worth paying for — a 30 nV/√Hz general-purpose part
would put the front end *below* the follower it replaces. A CMOS input matters
because the coil is inductive above 772 Hz and reaches roughly 4 kΩ at 10 kHz;
current noise at 23 fA/√Hz costs nothing against that, where a bipolar input
would not.

Rail-to-rail output is used. Rail-to-rail input is not required — the input sits
at 1.0 V — but common-mode rejection is specified only up to (V+) − 1.3 V, which
bounds the bias point (§5).

| Parameter | Value |
|---|---|
| Voltage noise, 1 kHz | 7.5 nV/√Hz |
| Quiescent current | 760 µA |
| Gain bandwidth | 5.5 MHz — 690 kHz at the gain used |
| Supply | 2.2–5.5 V |
| Power supply rejection | 86 dB typ, >80 dB across the audio band |
| Offset | 5 µV typ, 25 µV max |

Stocked as an LCSC extended part. Confirm the assembly feeder charge is
acceptable when the order is placed; at four parts per board it is not a design
constraint.

---

## 3. Input biasing — the reference is the bias path

**Tie each coil's cold end to the strip's reference, not to ground.** The coil
then defines its amplifier's input potential directly, carrying only the input's
picoamps of bias current, and the signal swings symmetrically about the
reference.

**Return the lower gain leg to that same reference, not to ground.** This is the
one arrangement detail that decides the character of the whole stage. With the
reference at both nodes no DC flows in the gain leg, so none flows in the
feedback resistor, and the output rests at the reference regardless of the AC
gain. The stage is **DC-coupled and flat to DC**: no input coupling capacitor, no
per-channel bias network, and no capacitor in the gain leg.

**The reference is a divider on the analog rail followed by a unity-gain
buffer**, one per board, distributed as a strip-wide net (§8). The buffer is what
makes the arrangement affordable — an unbuffered divider cannot hold a node that
four gain legs draw signal current from.

### Why the leg returns to the reference and not to the non-inverting input alone

Reference-borne noise and rail ripple reach the output at a gain of **exactly
one** when both nodes sit on the reference, while the signal sees the full stage
gain — a **17.9 dB ratio** at the design gain. Bias the non-inverting input from
the divider and return the gain leg anywhere else, and reference noise arrives at
the output at Rf/Rg ≈ 6.8 instead. Same part count, same schematic complexity,
17 dB apart.

**The 17.9 dB is a gain ratio, not a rejection.** Nothing cancels. It is bounded
by the stage gain and shrinks if the gain is ever lowered. Whether it can be
turned into a real rejection is the subject of §4.

### Consequences to hold during layout and bring-up

- **The cold ends are not grounds.** They connect to the reference, which is an
  AC ground only by virtue of the filter capacitor ahead of its buffer. Route
  them as signals.
- **The coils inject nothing into the reference**, because the input draws no
  current. What does flow into it is the summed gain-leg current of all four
  channels, so **the buffer's output impedance sets inter-string isolation** —
  budget it from peak leg current against full-scale input. The requirement is
  loose at bass fundamentals and scales with frequency; about a megahertz of
  gain-bandwidth is ample.
- **Star the reference from the buffer output**, do not daisy-chain it.
- **Do not hang a large bypass on the buffer output.** Its noise is already at
  the output by then, the capacitor only forms a pole with milliohms of output
  impedance up in the megahertz, and it works against stability into the
  resistive load the four gain legs present. The filtering belongs on the divider
  tap, ahead of the buffer.
- **Every input DC error now sees the full stage gain**, which is what makes the
  amplifier's offset specification load-bearing rather than incidental. At 25 µV
  that is under 200 µV at the output against roughly a volt of headroom. The
  buffer's own offset moves the reference and every output together, so it is
  close to a don't-care.
- **Fit a very high value bleeder from each non-inverting input to the
  reference** so that an open pickup coil leaves the input defined rather than
  floating, and does not slam the output to a rail.

## 4. The connection to the converter

**Specified: single-ended, one signal conductor per channel, AC-coupled at the
converter.** The control cavity cannot be shielded, because the Bluetooth
module's antenna is in it (`bluetooth-constraints.md`), which makes interference
into the wire run the governing question. Single-ended answers it by level rather
than by rejection: the cable carries 320 mV peak-to-peak from an output impedance
of ohms, which is more signal and lower source impedance than a conventional
instrument's wiring, which works. Twisted pairs into differential receivers would
add 40–50 dB of rejection that the level and impedance already make unnecessary,
at the cost of four twisted pairs and a larger connector.

Two differential options exist against that baseline, and they are not the same
option. Neither requires any change to the channel circuit of §8.

**Pseudo-differential, a cold conductor per channel.** Run each channel's output
as hot and a ground reference as cold, twisted. This addresses cable interference
by rejection, and it is the response if bench measurement finds interference to be
a real problem. It costs a cold conductor per channel — nine conductors instead
of six — so it is a connector and cable change (§10).

**⚠ PROPOSAL (2026-08-26): one reference conductor, DC-coupled differential.**
Carry the buffered reference itself over a **single** added conductor, present it
to the converter's cold input pins, and configure the converter for a DC-coupled
differential input. This is a different mechanism from the option above and buys
different things:

- **It turns §3's 17.9 dB ratio into a rejection.** The reference appears at
  every channel output at a gain of one and at the cold pin at a gain of one, so
  the converter's common-mode rejection subtracts it. Rail ripple arriving
  through the divider — the dominant reference-borne term, and coherent in every
  channel because it is literally the same node — stops being a per-channel spur.
- **It cancels inter-string crosstalk through the buffer**, because the
  perturbation the summed gain-leg currents produce across the buffer's output
  impedance is also common to every output and to the reference conductor. This
  requires the conductor to be sensed **at the reference star node**, not
  somewhere down the distribution.
- **It rejects the ground-return offset between the two boards**, which a
  reference reproduced locally at the converter could not do. That is the reason
  the conductor has to come from this board rather than being generated at the
  far end.
- **It removes the last high-pass in the chain.** With the preamp flat to DC, the
  converter's coupling capacitors are the only analog low-frequency limit left,
  and they impose exactly the tolerance-mismatched phase shift at the low
  fundamentals that DC-coupling this stage was meant to avoid.
- **It costs no converter channels.** See `adc-netlist.md` §2.1 — the converter
  records four analog channels per device whether its input pairs are configured
  differential or single-ended.

**Status: proposal, pending simulation and a datasheet confirmation** of the
converter's DC-coupled common-mode window. The board-side cost is one conductor
and one connector position (§10); there are no new parts, because the buffer this
depends on is already required by §3. The full argument, the register settings
and what it deletes from the main board are in `adc-netlist.md` §2.1.

⚠ **This supersedes the statement, previously carried here and in the reference
architecture note, that a differential connection would require twice the
converter channels.** It would not.

## 5. Bias point and output level

**Specify the reference at 1.0 V**, from a divider on the 3.3 V analog rail,
filtered at the divider tap and buffered, shared by all four channels on a board
(§3, §8).

Every channel's output therefore rests at 1.0 V, to the tolerance of two
resistors. The value is chosen for what happens at the far end:

- It sits **375 mV below the converter's input self-bias** of 1.375 V, so the
  converter side of the coupling network remains the positive one. The polarity
  and clamp orientation drawn in `adc-netlist.md` are unchanged, and 375 mV is a
  healthy bias for a polarised part.
- It keeps the input **inside the amplifier's specified common-mode region**,
  clear of the (V+) − 1.3 V boundary even on signal peaks.
- It costs only asymmetric swing — about 950 mV downward against 2.25 V upward.
  Signal peaks are 160 mV, so there is more than six times the margin required,
  and a transient at four times nominal level still fits.

> **Selection rule for any future device or supply change:** the front-end bias
> point must sit below the converter's input bias with margin. Unlike the rule it
> replaces, this one is enforced by a resistor ratio rather than by a
> distribution of semiconductor parameters.

⚠ **The ratio is open, and the two reasons to change it point the same way.**
1.0 V sits well below half the rail and costs several dB of symmetric headroom
for no benefit that survives the move to a buffered reference — the value was
chosen to protect a polarised coupling part, and nothing else here depends on it.
Under the §4 proposal that constraint disappears entirely and is replaced by a
preference in the opposite direction: the converter's own optimum DC bias for a
DC-coupled input is its reference midpoint, **1.375 V** at the specified
full-scale setting. That value is still comfortably inside the amplifier's
common-mode region — 625 mV clear of the (V+) − 1.3 V boundary — and it gives
1.375 V of downward swing against 1.9 V upward, materially more symmetric than
the present 950 mV. **Do not move it while the AC-coupled arrangement stands**,
because the selection rule above still governs there; move it as part of adopting
§4, and re-derive the divider ratio at the same time.

**Level.** 40 mV peak-to-peak at the coil becomes approximately 320 mV
peak-to-peak on the cable, placing the source roughly 17 dB below the converter's
full scale. This is a materially better operating point for the converter than
the 30–40 dB assumed at selection, and the programmable gain setting should be
chosen against the measured level rather than the original assumption
(`adc-firmware-init.md`).

---

## 6. Board supply

**Each board is powered from the 3.3 V analog rail.** One power conductor per
board carries it.

The amplifier rejects more than 80 dB of supply noise across the audio band,
which is what makes a rail shared with digital loads acceptable. This is the
whole argument; there is no second reason, and it is examined against the
alternative in `analog-front-end.md` §4.

**Local decoupling per channel**, sited at the amplifier's supply pin. A series
resistor from the board's supply bus into each channel's local node is optional
here — the amplifier's own rejection does the work that the resistor would have
done, and the residual case for it is RF isolation rather than crosstalk. Fit it
if board area is not pressing.

**Board current** is roughly **3.8 mA per board** — four channel amplifiers, the
reference buffer, and the divider. ⚠ This supersedes the 3.1 mA previously stated
here, which counted four amplifiers and no buffer.

---

## 7. RF immunity

2.4 GHz energy from the Bluetooth module can rectify at the amplifier's input and
produce **baseband** artifacts. Once rectified, no downstream filtering removes
it — it looks like signal. This is the reason the front end needs deliberate RF
treatment rather than careful routing alone.

**Treatment: a series resistor at each input with a shunt capacitor to ground**,
sited directly at the amplifier's input pin. Two parts per channel.

⚠ **This is the identified risk to the design.** The treatment is carried forward
from a front end whose input was a JFET gate junction. A CMOS input rectifies
too, and not necessarily in the same way or to the same degree. There is no
analysis that settles it and no breadboard that would reproduce the RF
environment — it is measured on the real board, in the instrument, with the radio
transmitting (§12 item 1). If it fails, the pseudo-differential option in §4 is
the response, not a larger filter.

**The network is not a simple lowpass, and this matters.** With 66 mH of coil in
the loop it is an RLC: flat to about 30 kHz, **peaking roughly 26 dB at 62 kHz**,
then rolling off at 12 dB/octave so that the intended RF attenuation above a few
hundred kilohertz is delivered as designed. The high Q is a direct consequence of
the coil's 320 Ω DC resistance and cannot be tuned away with the capacitor value
— reducing it raises both the frequency and the Q.

The peak is out of band and is removed by the converter's decimation filter. Its
significance is that it represents 26 dB of gain for any interference living near
it — switching supplies and lighting drivers are plausible neighbours — and the
front end now amplifies that by eight rather than attenuating it.

**Provision a damping network per channel and leave it unpopulated.** A series
resistor and capacitor across the coil, around 27 kΩ with 1 nF, brings Q to
approximately one. It is not fitted by default because a shunt of that value
costs about a decibel at 10 kHz against the coil's rising impedance. Two 0402
footprints per channel is cheap insurance against a respin.

**Secondary path:** the Bluetooth packet envelope rides on the supply at
audio-rate frequencies. This is a distinct mechanism from RF at the input, and it
is what §6's supply rejection and local decoupling address.

---

## 8. Per-channel circuit

Values are given by function; take designators from the schematic at entry.

| Function | Value | Package | Notes |
|---|---|---|---|
| Amplifier | **OPA376** | SC70-5 or SOT-23-5 | §2 |
| Input series resistor | 1 kΩ | 0402 | RF filter, coil hot terminal to amplifier input |
| Input shunt capacitor | 100 pF C0G | 0402 | RF filter to ground, at the input pin |
| Input bleeder | ≥ 10 MΩ | 0402 | non-inverting input to the reference, so an open coil leaves the input defined rather than floating (§3). In parallel with a 320 Ω coil it is electrically invisible |
| Feedback resistor | 15 kΩ | 0402 | with the leg below, gain 7.8 |
| Lower gain leg | 2.2 kΩ | 0402 | inverting input **to the reference**, not to ground, and with no capacitor in series — §3 |
| Feedback damping network | ⚠ per the stability sweep | 0402 | a feedback capacitor and series resistor across the feedback resistor, added after this document's previous revision. **Take the values from the schematic and the simulation notes, not from this table** |
| Local supply decoupling | 100 nF | 0402 | at the amplifier supply pin |
| Coil landing pads | — | custom THT | magnet-wire pads; hot to the input resistor, cold to the reference |
| RF damping network | 27 kΩ + 1 nF | 0402 ×2 | **footprints only, do not populate** (§7) |

Shared per board:

| Function | Value | Package | Notes |
|---|---|---|---|
| Supply entry resistor | 47 Ω | 0402 | analog rail into the strip supply bus, with the capacitor below |
| Supply entry capacitor | 100 nF | 0402 | strip supply bus to ground |
| Reference divider | 100 kΩ / 43 kΩ | 0402 | analog rail to ground, producing 1.0 V — ratio open, §5 |
| Reference filter capacitor | 47 µF tantalum | — | **on the divider tap, ahead of the buffer.** Sets the reference pole; carries no signal current |
| Reference buffer | **OPA376**, unity gain | SC70-5 or SOT-23-5 | divider tap to the strip-wide reference net (§3) |

**The gain leg returns to the reference, not to ground, and carries no
capacitor.** This is the arrangement §3 argues for and it is the difference
between a stage that is flat to DC and one that is not. It is also the one detail
most likely to be "corrected" by someone reading an older revision of this
document — mark it on the schematic as intentional.

**No DC-blocking capacitor is required anywhere in the channel.** Because the
coil biases the non-inverting input to the reference directly and the gain leg
returns to the same node, both ends of the gain network sit at the same potential
and the DC gain to the reference is one by construction.

**The reference filter capacitor is not optional and not merely decoupling.** The
divider's own thermal noise and the rail spectrum that reaches it appear at every
channel's output identically — correlated across channels, so they do not average
down through any downstream summing, and they land as a coherent spur rather than
as noise. The capacitor value is the knob that sets how far down they arrive; a
series resistor ahead of the divider is not, because the Thevenin impedance is
dominated by the shunt leg and adding resistance in the top leg moves the pole
almost not at all while shifting the reference by hundreds of millivolts.

**Thermal noise from the reference is not worth engineering against** — it costs
under a tenth of a decibel. The rail spectrum reaching it is a different matter
and is the open gate in §12.

**The buffer is an OPA376 because one is already on the board's bill of
materials.** Its noise enters every channel at unity, against roughly
84 nV/√Hz arriving from the channel amplifier at the design gain, so a 7.5 nV/√Hz
part costs about 0.03 dB where a 30 nV/√Hz general-purpose part would cost half a
decibel. Introducing a second amplifier type also means a new symbol, a new
footprint assignment and a new simulation-model mapping, each of which is a fresh
opportunity for the pin-mapping errors recorded in the simulation notes.

**Do not make the reference a replica gain stage** in an attempt to match the
noise path of a real channel. Matching would require the same gain of eight,
which would inject 84 nV/√Hz of *uncorrelated* noise into all four channels at
unity and cost roughly 3 dB. Unity buffer only.

## 9. Component type rules

These apply board-wide and are stated here because they are easy to lose when
values are picked from a stock list.

**No Class II ceramic (X5R, X7R, Y5V) anywhere in a signal path or on the
reference, board-wide.** Class I (C0G/NP0), tantalum or polymer only. Supply
bypasses sitting behind the amplifier's supply rejection are the only exception,
and §8 names them.

⚠ **This is stricter than the rule previously stated here**, which permitted a
Class II part in the gain leg and another on the bias node as called-out
exceptions. Both parts are gone from §8, and the exception that licensed them
does not survive review. Two independent mechanisms drove the change, and both
get *worse* with DC bias, because bias poles the ferroelectric dielectric:

- **Voltage coefficient.** A high capacitance value in a small package is
  necessarily an extreme high-K dielectric, and at a bias of about a volt such a
  part can lose the majority of its nominal capacitance. That both moves the
  designed corner and steepens the local slope that produces the distortion.
  Second harmonic reaching a tenth of a percent at full scale near the bottom of
  the range is achievable with a poor choice, against a converter floor around
  −95 dB.
- **Piezoelectricity.** The strip mounts on the pickup bobbin with the coil wires
  soldered directly to it — the most mechanically excited location in the
  instrument — and a narrow strip is compliant in bending. Strain-induced charge
  from a biased Class II part is injected into the signal at close to unity
  referred to the input, in the same 30–200 Hz band as the signal, correlated
  with body vibration and therefore not separable downstream. **A shared
  reference capacitor is the worst case of all**, because it injects the same
  body vibration into every channel in phase and defeats exactly the per-string
  isolation the multichannel architecture exists to provide. This is why the
  reference filter is specified as a tantalum on a low-impedance divider rather
  than a Class I part on a high-impedance one: both remove the piezoelectric
  path, and the low-impedance version is roughly 20 dB better on rail rejection,
  which is the axis that actually matters.

**Thin film wherever DC crosses a signal-path resistor.** Thick film's excess
(current) noise is 1/f and scales with the DC voltage across the part, and thick
film carries a voltage coefficient of roughly ±100 ppm/V producing distortion
under the same condition. **In this design no signal-path resistor carries DC**
— the input resistor passes picoamps, and both ends of the gain network sit at
the same potential — so thick film is correct throughout and the rule costs
nothing here. It is recorded because it is not obviously satisfied and a future
change could break it.

Note that neither mechanism appears in a SPICE netlist: the resistor primitive
models 4kTR thermal noise only, with no excess noise and no voltage coefficient.
Simulated noise floors for this board should be read as optimistic lower bounds.

---

## 10. Connector and cable

**Constraints.** 0.75″ pickup width; very low profile under the bobbin; the cable
passes through a hole to the control cavity; very little space at the main board
edge; crimping avoided where possible.

**Selected: 2.00 mm pitch single-row right-angle through-hole header, 6-way**,
mounted on the bottom side. Body height is roughly 2 mm above the board surface —
*lower* than the 1.0 mm surface-mount part it replaces, which is the opposite of
what a coarser pitch suggests. ⚠ Confirm against the part actually fitted;
right-angle bodies in this pitch vary more than the pitch does.

⚠ **This supersedes the 1.0 mm pitch wire-to-board SMT selection** previously
specified here, and with it the fine-pitch crimping advice, the
brand-compatibility caution and the mounting-pad note that selection carried.

**Why the pitch went up.** Not profile, and not anything electrical — **the 1 mm
crimp contacts were the problem.** They are awkward to handle and to seat, and
the finished termination is fragile enough to become the least reliable thing in
the assembly. Everything else about that part was acceptable. Doubling the pitch
is a bet that contacts twice the size are enough more workable to fix it, and it
brings a fallback the smaller part never had — see *Termination* below.

Evaluated and rejected:

- **FFC/ZIF** — the lowest profile available and no crimping, but it needs a ZIF
  socket at both ends and there is no room at the main board edge.
- **0.1″ right-angle headers** — roughly 8 mm tall.
- **1.0 mm pitch wire-to-board (JST SH class)** — the previous selection,
  rejected on the fragility of its crimp terminations rather than on anything
  electrical. It also put a surface-mount part on the side that is hand-soldered
  anyway, offered no way to fall back to a soldered joint, and bought no profile
  advantage over the part now specified.

**What the coarser pitch buys.** A through-hole part on the hand-soldered side,
mating hardware that is a de facto standard rather than a per-manufacturer
compatibility claim, contacts large enough that crimping may become practical,
and — the part that does not depend on that bet paying off — the option of
soldering the cable to the same holes.

**Configuration: 6-way** = four signals plus supply and ground. Six positions and
no mounting pad — a plain 1×6 at 2.00 mm pitch, 0.8 mm drill, on the bottom side.
⚠ **Under the §4 proposal this becomes 7-way**, the added position carrying the
reference. A 1×7 and a 1×8 in this pitch and profile are ordinary stock items, so
the choice is a footprint change and never a connector search — but see
*Polarity* below, where the extra position is not free.
A seventh *conductor* for a second ground was considered and rejected — with
loose round wires you do not control conductor adjacency, so flanking grounds buy
nothing. That idea only makes sense with ribbon or flat cable, where conductor
positions are fixed.

⚠ **This supersedes the ribbon-cable treatment** previously in `layout-notes.md`
§6.3, including its recommended conductor ordering — that analysis assumed flat
ribbon with controlled adjacency.

### Termination — deliberately still open

**The footprint does not care how the cable is attached, and that is the point.**
The same 1×6 through-hole pattern carries three terminations, so the choice can
be deferred until boards and samples are in hand:

| Termination | Profile on the bottom | Detachable | Status |
|---|---|---|---|
| Header fitted, mating socket on 2 mm crimp contacts | roughly 2 mm | yes | **preferred — sockets and contacts on order to evaluate** |
| Header fitted, wires soldered to its pins | roughly 2 mm | no | available |
| No header, wires soldered straight into the holes | essentially none | no | **the backup, and the lowest profile of the three** |

**What is being evaluated is whether 2 mm crimp contacts are workable enough to
be worth having.** They are the only route to a detachable cable, and detachable
is what buys assembly and service access under the bobbin. If they turn out to
share the fragility of the 1 mm contacts, soldering wins and **nothing about the
board changes** — that is the whole value of having landed on a through-hole
footprint.

**What soldering gives up** is separating the board from its cable without an
iron. Weigh it against the main-board end, which is soldered already: a soldered
pickup end makes the cable captive at both ends and the harness a single unit.

⚠ **A soldered joint needs strain relief.** The fragility that drove the pitch
change does not disappear, it relocates — 28 AWG soldered into a plated hole
fatigues at the joint if the cable can move. Anchor the cable mechanically before
it leaves the assembly, whichever termination is chosen.

### Polarity

**The connector is unkeyed and the board carries no reverse-polarity
protection.** This is accepted for development. **The board is marked and the
cable is coded**, and that is the whole of the protection.

Record the failure mode plainly, because it is not a soft one — and because the
pin order changes how bad it is. Reversing a 6-way connector maps position 1 to
6, 2 to 5 and 3 to 4. Supply can never land back on supply, so a reversed
insertion is always a fault; what the ordering decides is which fault.

> **Do not place supply and ground at mirror positions** — 1 and 6, 2 and 5, or
> 3 and 4. That is the one family of arrangements in which reversal exchanges
> them outright, applies the analog rail backwards across every amplifier on the
> board, and should be expected to destroy all four.

With supply and ground anywhere else, reversal instead leaves the board
unpowered and drives the rail into two amplifier *outputs* through the cable.
Those outputs clamp to their own floating supply through the output protection,
so the board part-powers itself into an undefined state. That is not a good
outcome either, but it is the recoverable one, and it costs nothing to choose it
at schematic entry.

Two retrofits exist should reversal stop being theoretical, neither needing more
than a footprint change:

- **Keying by omission** — a header with one position more than the conductor
  count, that pin removed and the matching housing cavity plugged. Costs one
  position and no parts. ⚠ Under the §4 proposal this needs an 8-position part,
  not the 7-position one that would otherwise have served.
- **A reverse-polarity series element** on the board's supply input. A Schottky
  is one part but drops roughly 0.2 V, which drags the bias divider's output down
  with it; a P-channel MOSFET costs area and almost no voltage.

Production hardware wants a keyed housing rather than either of those.

**A soldered termination removes the hazard at this end entirely** — a captive
cable cannot be inserted backwards. Apply the mirror-position rule anyway. It
costs nothing at schematic entry and it keeps the socket option open.

⚠ **The §4 proposal changes this analysis and makes it worse.** Seven positions
reverse as 1↔7, 2↔6, 3↔5 with 4 fixed, so the mirror set to avoid changes.
More importantly, with the converter's coupling capacitors deleted there is no
longer a series capacitor between a signal conductor and a converter input pin,
so a reversal that lands the supply conductor on a signal position applies the
analog rail directly to that pin. Both boards sit on the same analog rail and the
converter's analog pins are rated to its own supply plus 0.3 V, so it is
survivable while powered and not while it is not. **Redo the position assignment
when the proposal is adopted, and take keying from optional to specified at the
same time.**

**Neither differential option in §4 constrains this choice.** The
pseudo-differential fallback would raise the conductor count to nine and the
reference-conductor proposal raises it to seven; 1×7, 1×8 and 1×10 in this pitch
and profile are all ordinary stock items, so either remains a board revision
rather than a connector search. That open item is closed.

**Cable:** 28 AWG stranded, six conductors — seven under the §4 proposal —
loose, not twisted or shielded. The
low-impedance amplified outputs and the input RC filter are what make that
viable. Runs under the preamp board to the control cavity. Buy long and cut
rather than coiling excess near the Bluetooth module.

**Sourcing and assembly.** The header is through-hole and does not ride the
JLCPCB assembly order — omit it from the assembly BOM and hand-solder it, or omit
it from the board entirely if the cable is soldered into the holes. Assembly
sequence is unchanged: solder the main-board end of the cable first, pull the
wires through the hole, then terminate at the pickup by whichever route
*Termination* above settles on.

---

## 11. Layout

**Board organisation.** Two boards, four channels each, laid out with **Repeat
Layout** from a hierarchical sheet — which requires the schematic to instantiate
one channel four times rather than carry four flat copies. Place all four groups
first, *then* route the supply, bias and output buses, or replication may drop
copied traces onto them. Anchor replication on the amplifier in each instance.

**Connector placement: bottom side, at the end opposite the channels.** Bottom
side is driven by assembly access — room to seat the housing before plugging into
the bottom of the pickup assembly, and better cable-slack management. The cable
runs under the board to the cavity; a continuous ground pour between those wires
and the input nodes is sufficient, since the barrier is capacitive interception
and the aggressors are low-impedance amplified outputs anyway.

**The header is through-hole, so its solder joints land on the top side.** Keep
its pad rings and clearances clear of the input areas at that end, and trim the
leads — that protrusion sits under the bobbin. The height arithmetic below
accounts for it.

**The input node — the one place where less copper is better.** Keep the
coil-to-resistor-to-input copper short and small, and do **not** pour ground
tight against it. Siting the input resistor and shunt capacitor directly at the
amplifier pin shrinks the exposed node to almost nothing. The shunt capacitor's
ground pad wants a via straight down at the pad — its RF function depends on
near-zero inductance to ground, and at 2.4 GHz that inductance, not the
capacitance, is what determines whether the filter works. Same for the local
supply decoupling.

**The reference net.** Route it as a signal, and **star it from the buffer
output** to eight destinations — the four coil cold-end pads and the four gain
legs. Do not daisy-chain it: the gain legs inject the signal-frequency feedback
current of every channel into this node, and a shared segment of copper between
two of them is an inter-string crosstalk path that no amount of buffer quality
recovers. Site the buffer centrally to keep the star arms comparable. The divider
and its filter capacitor sit ahead of the buffer and can go anywhere convenient.

⚠ **This supersedes the previous instruction to star from a bypass capacitor and
to ground each gain leg's return capacitor into the pour.** There is no bypass
capacitor on the reference and no capacitor in the gain leg; both parts are gone
(§3, §8), and the return current they used to send into the ground pour now goes
back to the buffer instead. Plan the copper for that.

**If the §4 proposal is adopted, bring the reference conductor's connector pin
back to the star node itself**, not to the nearest convenient point on a star
arm. The cancellation it buys is exactly the difference between those two
choices.

**Custom footprint for the magnet-wire landings.** Stock wire-connection
footprints bottom out around 1.4 mm outer diameter, far too large. Use **0.4 mm
drill / 0.8 mm pad**; 0.3/0.6 stacks two JLCPCB minimums — drill *and* annular
ring — and invites a DFM flag. Easiest route is to open a stock test-point THT
pad footprint, Save As into a personal library, and edit the pad's hole and size
fields, then redraw silkscreen and courtyard. The hole is a *property of the
pad*, not a separate selectable object.

**Assembly.** Single-sided JLCPCB assembly for the top, hand-solder the
bottom-side header — two-sided assembly incurs a second-pass setup charge not
worth it for one part per board, and a through-hole part would not ride it in any
case. Omit the header from the assembly BOM.

**Heights.** SC70-5 is roughly 1.1 mm and the 0805 capacitors roughly 0.9 mm on
top. The header body is roughly 2 mm on the bottom, and its trimmed leads and
fillets add roughly 0.8 mm on top — under the component stack rather than on top
of it, so the top side is still set by the components. Total stack is therefore
roughly 4.7 mm on a 1.6 mm board and 3.9 mm on 0.8 mm, **lower than the
surface-mount arrangement this replaces** — and roughly 2 mm lower again if the
cable is soldered straight into the holes with no header fitted (§10). ⚠ Confirm
the body height against the part fitted.

**Area.** Approximately 7 × 4.5 mm per channel at the routing density this
project uses, so roughly 130 mm² of channel area per board before the connector
and bias network.

---

## 12. Verification before board spin

1. **Bench-measure the noise floor per channel with the radio transmitting and
   idle.** This validates the RF treatment against a CMOS input and is the
   identified risk to the design (§7). Do it before committing the second board.
2. **Confirm stability with a coil connected.** The input sees an inductive
   source rising to kilohms; check for oscillation at the input node and at the
   output with a wideband probe, not just an audio-band measurement.
3. **Characterise the 62 kHz resonance** on the real board and decide whether to
   populate the damping network (§7). Check with typical stage lighting nearby,
   not only on a clean bench.
4. **Confirm the output bias point** lands at the reference on every channel, and
   that the delta to the converter's input self-bias is as expected and in the
   same direction (§5). This is what protects the polarised coupling part while
   the AC-coupled arrangement stands. Measure the reference itself at the buffer
   output and again at the far end of the distribution — a difference there is
   the crosstalk path of item 6 showing up as a DC error.
5. **Measure channel-to-channel gain spread**, which should be resistor
   tolerance. A larger spread means the gain network is not returning where the
   schematic says it does.
6. **Measure channel-to-channel crosstalk.** The reference is the path to
    suspect if it is worse than expected, and the mechanism is the buffer's
    output impedance against the summed gain-leg current (§3). Check the
    distribution is starred rather than daisy-chained before suspecting the part.
7. **Measure the analog rail spectrum below 1 kHz** on assembled hardware with
    the converters and the processor running. ⚠ **This is the open gate on the
    reference network.** The rail reaches the output by two paths: directly
    through the amplifier, where supply rejection handles it, and through the
    reference divider, where it is not rejected at all — the amplifier sees it as
    a legitimate input and amplifies it faithfully, and it dominates by roughly
    24 dB at 100 Hz. It also appears identically in every channel, so it lands as
    a coherent spur rather than as noise, which is exactly what pollutes a
    per-string estimator. This measurement is the only thing that decides whether
    the reference needs more than a filtered low-impedance divider. Escalation
    order if the rail is dirty: raise the filter capacitor, then derive the
    reference from a dedicated voltage reference rather than the rail. **The §4
    proposal attacks this term directly** — it is common-mode by construction —
    so take this measurement before spending parts on it.
8. **Verify the three transfer functions by simulation before release**, because
    they are near model-independent where a simulated noise figure is not:
    reference to output should be exactly unity, signal to output should be flat
    to DC at the design gain, and rail to output should show the divider path.
    One operating point and one AC sweep cover all three, and the defects found
    on this board so far surfaced from setting up the operating point rather than
    from schematic review.
9. **Confirm the header's top-side lead protrusion clears the bobbin** after
   trimming, and that its pad rings and clearances have not encroached on the
   input areas at that end of the board (§10, §11).
10. **Confirm supply and ground are not at mirror positions** on the connector
   (§10). This is a schematic check, it takes one look, and it is the difference
   between a recoverable mis-insertion and a destroyed board.
11. **Evaluate the 2 mm crimp contacts before committing to a detachable cable**
   (§10). Crimp and seat a full set, mate it, then flex and tug the finished
   termination — fragility rather than fit is what ruled out the previous
   connector, and it is what this pitch change is meant to fix. If it does not
   convince, solder to the same holes and change nothing else. Either way,
   confirm the strain relief and confirm that the pin-1 marking and the cable
   coding are unambiguous read from either end.
12. **Verify the bottom ground pour is not fragmented into islands** under the
    input areas after routing — the cable runs beneath the board and the pour is
    the barrier.
13. **Feed the measured output level back into the converter's gain plan**
    (`adc-firmware-init.md`). At the level this design produces, the programmable
    gain requirement is much lower than originally assumed.

---

## 13. Where the rest lives

| Topic | Document |
|---|---|
| Why the front end amplifies, and what was rejected | `analog-front-end.md` |
| The reference architecture, distribution and supply filtering | `../OPA376 String Preamp/reference-architecture.md` |
| Symbol, footprint and simulation-model traps; capacitor policy; the rail-spectrum gate | project note *OPA376 String Preamp — simulation and pre-fab notes* |
| Noise budget worked by hand | `../OPA376 String Preamp/noise-by-hand.md` |
| Converter input stage, coupling network, main-board connections | `adc-netlist.md` |
| Why the converter, and what the architecture demands of it | `adc-selection.md` |
| Register configuration, gain calibration, bring-up | `adc-firmware-init.md` |
| Control-cavity analog board for the fallback instrument | `cavity-preamp-board.md` |
| Radio placement, cavity shielding constraints | `bluetooth-constraints.md` |
| Phase gates, bring-up order, risk register | `multichannel-audio-board-plan.md` |
| The superseded source-follower design | `superseded/preamp-board-jfet.md` |
