# Pickup Preamp Boards — Design

**Status:** To be entered. Two identical 4-channel boards, one per pickup (neck,
bridge), each mounted under its pickup bobbin.

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

## 3. Input biasing — the coil is the bias path

**Tie each coil's cold end to the board's bias reference, not to ground.** The
coil then defines its amplifier's input potential directly, carrying only the
input's picoamps of bias current, and the signal swings symmetrically about the
reference.

This is the property that makes the circuit small. Without it, a single-supply
amplifier looking at a coil that swings below ground would need an input
coupling capacitor and a bias network per channel. With it there is neither —
five parts per channel, the same count as a source follower.

Two consequences to hold during layout and bring-up:

- **The cold ends are not grounds.** They connect to a bias node that is an AC
  ground only by virtue of its bypass capacitor. Route them as signals.
- **The coils inject nothing into that node**, because the input draws no
  current. Channel-to-channel coupling through the shared reference comes from
  the gain network, not from the coils, and is addressed in §8.

---

## 4. Single-ended, not differential

The control cavity cannot be shielded, because the Bluetooth module's antenna is
in it (`bluetooth-constraints.md`). That makes interference into the wire run the
governing question.

Single-ended is adopted because the front end's gain addresses that exposure
directly: the cable carries 320 mV peak-to-peak from an output impedance of ohms,
which is more signal and lower source impedance than a conventional instrument's
wiring, which works. Twisted pairs into differential receivers would add 40–50 dB
of rejection that the level and impedance already make unnecessary, at the cost
of four twisted pairs and a larger connector.

**Future-proofing: switching later requires no change to these boards.** The
converter supports pseudo-differential input — run each channel's output as hot
and a ground reference as cold, twisted. That costs 6 dB against 42 dB of
available programmable gain. It does require a cold conductor per channel, so it
is a connector and cable change (§10). **This is the documented fallback if bench
measurement finds cable interference to be a real problem.**

---

## 5. Bias point and output level

**Specify the bias reference at 1.0 V**, from a divider on the 3.3 V analog rail,
shared by all four channels on a board and bypassed.

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

**Board current** is roughly 3.1 mA per board, four amplifiers plus the divider.

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
| Feedback resistor | 15 kΩ | 0402 | with the leg below, gain 7.8 |
| Lower gain leg | 2.2 kΩ | 0402 | inverting input to the return capacitor |
| Gain leg return capacitor | 22 µF X5R | 0805 | **to ground, not to the bias node** — see below |
| Local supply decoupling | 100 nF | 0402 | at the amplifier supply pin |
| Coil landing pads | — | custom THT | magnet-wire pads; hot to the input resistor, cold to the bias node |
| RF damping network | 27 kΩ + 1 nF | 0402 ×2 | **footprints only, do not populate** (§7) |

Shared per board:

| Function | Value | Package | Notes |
|---|---|---|---|
| Bias divider | 100 kΩ / 43.2 kΩ | 0402 | 3.3 V analog rail to ground, producing 1.0 V |
| Bias node bypass | 10 µF X5R | 0805 | shunts the divider's own noise across the audio band |

**The gain leg returns to ground through its capacitor, not to the bias node.**
This is the one arrangement detail that is easy to get wrong and expensive to get
wrong. Returning all four legs to the shared bias node would put each channel's
signal-frequency feedback current into a node of finite impedance, coupling it
into the other three at roughly −28 dB at 30 Hz — fatal for a design whose entire
premise is per-string isolation. Returning to ground gives identical DC behaviour
(no current flows through the leg at DC either way, so the output still rests at
the bias voltage) while sending the signal current into the ground pour.

**No DC-blocking capacitor is required in the gain network.** Because the coil
biases the non-inverting input to the reference directly, both ends of the gain
network sit at the same potential and the DC gain is one by construction.

**The gain leg return capacitor is a deliberate exception to §9's dielectric
rule.** It carries signal current, but the voltage developed across it in band is
a few millivolts — at 30 Hz its reactance is about a tenth of the resistor it
sits under, and a twentieth of a decibel of gain error follows. A Class II part
has effectively no voltage across it to be non-linear about. Mark it as
intentional on the schematic so it does not read as an oversight.

**The bias node bypass is not optional and not merely decoupling.** The divider's
own thermal noise appears at every channel's input identically — correlated
across channels, so it does not average down through any downstream summing. The
bypass shunts it from a fraction of a hertz upward. **Do not substitute an active
buffer for the bypassed divider**: an amplifier's noise there would be
uncorrelated with nothing and would dominate.

---

## 9. Component type rules

These apply board-wide and are stated here because they are easy to lose when
values are picked from a stock list.

**Class I (C0G/NP0) dielectric for every capacitor in the signal path.** Class II
dielectrics (X7R, X5R) have a voltage coefficient that converts signal swing
across the part into distortion, and they are piezoelectric — a real rather than
theoretical concern for a part rigidly mounted to a vibrating instrument. Class
II remains correct for supply decoupling and for bias-network bypassing, where
the AC voltage across the part is negligible. The two Class II parts in §8 are
both of that kind and are called out individually.

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

- **Keying by omission** — a 7-position header with one pin removed and the
  matching housing cavity plugged. Costs one position and no parts.
- **A reverse-polarity series element** on the board's supply input. A Schottky
  is one part but drops roughly 0.2 V, which drags the bias divider's output down
  with it; a P-channel MOSFET costs area and almost no voltage.

Production hardware wants a keyed housing rather than either of those.

**A soldered termination removes the hazard at this end entirely** — a captive
cable cannot be inserted backwards. Apply the mirror-position rule anyway. It
costs nothing at schematic entry and it keeps the socket option open.

**The pseudo-differential fallback in §4 no longer constrains this choice.** It
would raise the conductor count to nine, and a 1×10 in this pitch and profile is
an ordinary stock item — so taking that option stays a board revision and never
becomes a connector search. That open item is closed.

**Cable:** 28 AWG stranded, six conductors, loose — not twisted or shielded. The
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

**The bias node.** Route it as a signal, star from the bypass capacitor to the
four coil cold-end pads. Site the bypass capacitor centrally rather than at the
divider. The divider itself can sit anywhere convenient.

**Gain leg returns.** Each channel's gain leg return capacitor grounds into the
pour with its own via at the pad. These carry the signal-frequency feedback
currents that §8 keeps off the bias node; do not let them share a return path
back to a single point.

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
4. **Confirm the output bias point** lands at 1.0 V and that the delta to the
   converter's input self-bias is as expected in the same direction on every
   channel (§5). This is what protects the polarised coupling part.
5. **Measure channel-to-channel gain spread**, which should be resistor
   tolerance. A larger spread means the gain network is not returning where the
   schematic says it does.
6. **Measure channel-to-channel crosstalk.** The bias node is the path to
   suspect if it is worse than expected (§8).
7. **Confirm the header's top-side lead protrusion clears the bobbin** after
   trimming, and that its pad rings and clearances have not encroached on the
   input areas at that end of the board (§10, §11).
8. **Confirm supply and ground are not at mirror positions** on the connector
   (§10). This is a schematic check, it takes one look, and it is the difference
   between a recoverable mis-insertion and a destroyed board.
9. **Evaluate the 2 mm crimp contacts before committing to a detachable cable**
   (§10). Crimp and seat a full set, mate it, then flex and tug the finished
   termination — fragility rather than fit is what ruled out the previous
   connector, and it is what this pitch change is meant to fix. If it does not
   convince, solder to the same holes and change nothing else. Either way,
   confirm the strain relief and confirm that the pin-1 marking and the cable
   coding are unambiguous read from either end.
10. **Verify the bottom ground pour is not fragmented into islands** under the
    input areas after routing — the cable runs beneath the board and the pour is
    the barrier.
11. **Feed the measured output level back into the converter's gain plan**
    (`adc-firmware-init.md`). At the level this design produces, the programmable
    gain requirement is much lower than originally assumed.

---

## 13. Where the rest lives

| Topic | Document |
|---|---|
| Why the front end amplifies, and what was rejected | `analog-front-end.md` |
| Converter input stage, coupling network, main-board connections | `adc-netlist.md` |
| Why the converter, and what the architecture demands of it | `adc-selection.md` |
| Register configuration, gain calibration, bring-up | `adc-firmware-init.md` |
| Control-cavity analog board for the fallback instrument | `cavity-preamp-board.md` |
| Radio placement, cavity shielding constraints | `bluetooth-constraints.md` |
| Phase gates, bring-up order, risk register | `multichannel-audio-board-plan.md` |
| The superseded source-follower design | `superseded/preamp-board-jfet.md` |
