# Pickup Preamp Boards — Design

**Status:** Schematic entered, layout in progress. Two identical 4-channel
boards, one per pickup (neck, bridge), each mounted under its pickup bobbin.

**Scope:** the offboard JFET buffer boards — why the circuit is what it is,
the per-channel values, the optional test summing stage, the connector and cable
to the control cavity, and the layout rules that apply to these boards
specifically. The main board's ADC input stage, coupling caps, and MICBIAS
generation are **not** here — see `adc-netlist.md`. Main-board layout is
`layout-notes.md`.

**Origin note.** Consolidated 2026-08-11 from a separate JFET-preamp thread.
That material assumed a Daisy Seed host at 48 kHz; the host-side content was
discarded in favour of this project's discrete STM32H725 / SAI4_B / 32 kHz
architecture (`multichannel-audio-board-plan.md`). What survives here is the
analog circuit, which is unaffected by the host choice.

---

## 1. What these boards do, and what they deliberately do not

**Impedance conversion only — no gain.** One JFET source follower per string
coil. All gain lives in the ADC's channel PGA (`adc-selection.md` §2), so the
per-channel circuit stays at roughly five parts and every channel is identical.

A gain stage here was considered and rejected: a common-source stage raises
output impedance back into the kΩ range, defeating the buffer's purpose, and
recovering it needs a second JFET — roughly doubling the board. Idss spread
would also make the gain vary channel to channel, which is the one thing the
DSP most wants to avoid.

**Why buffer at the pickup at all.** Op-amps in the control cavity work but
consume cavity area as channel count grows, and the cavity is a fixed size
already committed to the main board. Per-channel fully-differential drivers
(THS4551-class) were evaluated and rejected on the same grounds — six to eight
packages plus four precision resistors each reintroduced the space problem they
were meant to solve.

**The key structural point:** per-string buffers *and* per-channel cavity
op-amps together are strictly worse than either alone. The buffers only became
worthwhile once the ADC absorbed the entire cavity-side analog front end.

---

## 2. Why a JFET source follower works on a single low-voltage supply

A depletion-mode N-JFET self-biases: the gate sits at 0 V DC through the coil,
the source rises above it, and the resulting negative gate-source voltage is
what the device wants. No bias network, no input coupling cap, no rail
splitting — which matters because the pickup signal swings below ground and an
op-amp topology would need a physically large input blocking cap.

Points that justify the topology:

- **Below-rail input is safe.** Gate-source breakdown is −25 to −40 V; a few
  hundred mV below ground is nowhere near it.
- **The coil is the gate bias resistor.** Gate leakage is picoamps, so
  essentially no DC flows through the coil — it only defines gate potential.
  Without it the design would need a 1–10 MΩ gate resistor.
- **AC input impedance is hundreds of MΩ.** Loading on the coil is a few pF of
  gate and trace capacitance.
- **Supply regulation does not set the bias.** Idss and the source resistor do.
  Battery sag does not move the operating point as long as the device stays in
  saturation. This is worth remembering when evaluating supply options — it
  removes regulation from the argument entirely (§5).
- **Offset is part-dependent.** Unlike an emitter follower's fixed ~0.7 V, the
  offset here is the JFET's gate-source voltage, which varies with Idss. Per
  channel DC offsets must be calibrated out downstream (`adc-firmware-init.md`).

**Device: MMBFJ201 in SOT-23** (onsemi; LCSC C891687, available for assembly at
the intended fab). The governing constraint is **pinch-off headroom on a 3.0 V
rail**, not noise: the buffer's DC output equals its gate-source voltage
magnitude, so a device whose |Vgs(off)| runs to −4 V, −6 V or −7.5 V — which is
most of the SOT-23 JFET catalogue — cannot be biased sensibly here and puts the
downstream coupling cap's polarity in doubt (§6). Low-pinch-off, low-Idss
devices of this class are the only ones that fit, and this one is the volume
part in that class.

A BF862-class device would give roughly 100 Ω output impedance and lower noise
(0.8 nV/√Hz), but needs 2–5 mA per channel. That is genuinely unacceptable on
battery — 16 to 40 mA of continuous idle draw across the instrument's eight
channels. ⚠ **It is not, however, a MICBIAS violation**, and earlier revisions
of this document said it was: each MICBIAS output supplies only its own board's
**four** channels, so the load is 8–20 mA per device against a 20 mA per-device
capability. Tight, not impossible. The battery argument carries this decision on
its own; the supply-budget argument does not, and the pinch-off argument above
is the stronger reason regardless.

**Operating point across the part spread.** With a 2.2 kΩ source resistor on the
3.014 V rail, solving the square-law self-bias at the datasheet corners
(Idss 0.2–1.0 mA, pinch-off −0.3 to −1.5 V):

| Corner | Quiescent current | Source-node DC | Output impedance | Buffer gain |
|---|---|---|---|---|
| Low Idss, low pinch-off | 61 µA | 0.134 V | 1.36 kΩ | 0.62 |
| Mid | 159 µA | 0.349 V | 1.42 kΩ | 0.61 |
| High Idss, high pinch-off | 305 µA | 0.671 V | 1.36 kΩ | 0.62 |

**Gain is far more stable than the raw spread suggests, and this is structural.**
Transconductance-times-source-resistor works out to 2(1−x)/x, where x solves
(1−x)/x² = Idss·Rs/|Vgs(off)| — so gain depends only on the **ratio** of Idss to
pinch-off voltage, not on either alone. Those two parameters are physically
correlated in a real device, and this part's datasheet extremes happen to share
the same ratio exactly, which is why both corners land on the same gain and the
same output impedance. Devices scattered off that line will vary; the realistic
expectation is a couple of dB of channel-to-channel spread, not the −11 dB to
−2 dB the independent-corner box would imply.

What **does** vary five-to-one is the **DC set point and the quiescent current**,
and both are benign: the DC is calibrated out downstream and stays far below the
converter's input bias (§6), and four channels draw 0.24–1.22 mA against a 20 mA
rail budget (§5) — under a tenth of it.

**Insertion loss is fixed, not variable.** Buffer gain of ~0.62 plus the output
impedance working against the converter's 20 kΩ input impedance gives about
**−4.75 dB** end to end. That is a constant offset consuming roughly 5 dB of the
converter's 42 dB channel gain range, not a per-channel unknown. Raising the
source resistor to 10 kΩ would recover about 2 dB, but pushes the DC set point to
1.02 V (eating most of the coupling-cap margin in §6), nearly doubles output
impedance, and drops quiescent current to 20–100 µA where device noise starts to
matter. **Keep 2.2 kΩ.**

Per-channel gain trim and DC offset calibration remain **required**, not
optional (`adc-firmware-init.md`), and the numbers above are analysis to be
confirmed on the parts actually fitted (§11 item 5).

---

## 3. Single-ended, not differential

The control cavity cannot be shielded, because the Bluetooth module's antenna
is in it (`bluetooth-constraints.md`). That makes interference into the wire
run the governing question.

Passive twisted pairs from the coils into differential amplifiers in the cavity
(60–80 dB CMRR) were seriously entertained — that approach eliminates these
boards entirely. It was rejected because the low source impedance already does
the noise-rejection work over a short run inside an instrument body, where the
aggressors are RF and high-frequency digital rather than mains hum. The extra
40–50 dB is not needed, and single-ended saves four twisted pairs and eight
coupling caps.

**Future-proofing:** switching later requires **no change to these boards**.
The ADC supports pseudo-differential input — run the buffer output as hot and a
ground reference as cold, twisted. That costs 6 dB of signal, which is
irrelevant against 42 dB of available PGA, and CMRR still works.

---

## 4. RF immunity — the mechanism that actually matters

2.4 GHz energy from the Bluetooth module rectifies at the JFET's gate junction
and produces **baseband** artifacts. Once rectified, no downstream filtering can
remove it — it looks like signal. This is the same mechanism as a phone buzzing
through a guitar amp, and it is the reason the front end needs deliberate RF
treatment rather than just careful routing.

**Treatment: a series resistor at the gate with a shunt capacitor to ground**,
placing the corner far above audio and far below 2.4 GHz. Two 0402 parts per
channel, sited directly at the gate. This is more robust than cable shielding
and is what makes cable shielding unnecessary.

The shunt cap sits across the coil, but with deliberately low-inductance
single-string coils this is negligible — and it is a fixed, known capacitance
replacing variable cable capacitance, which is an improvement in itself.

**Secondary path:** the Bluetooth *packet envelope* rides on the supply at
audio-rate frequencies. This is a distinct mechanism from RF at the gate and is
addressed by the supply choice (§5) plus per-channel supply filtering (§7).

> Note for the main board: this treatment is at the gate, on these boards. It
> does not change `adc-netlist.md` §2's separate decision to keep a series
> resistor *out* of the ADC input path, where it would shift the coupling
> corner and add noise into a low-level node.

---

## 5. Board supply

**Each board is powered from its own ADC's MICBIAS output** — the neck board
from one device, the bridge board from the other, never tied together
(`adc-netlist.md` §1). One power conductor per board carries it.

**Why MICBIAS rather than the system rail:** isolation from the dirtiest rail
in the system — Bluetooth transmit bursts, MCU load steps, charger switching.
The output is specified at 1.6 µVrms noise, gives a firmware power switch for
free, and its current limiting protects the system rail from a crushed pickup
wire. Headroom is ample: four buffers per board against a 20 mA per-device
capability (`layout-notes.md` §6.1).

**Arguments that do not apply:** regulation. As §2 notes, a source follower's
bias is set by Idss and the source resistor, so battery sag would not move the
operating point regardless. The benefit is noise isolation only.

**Costs accepted:** the buffers depend on their ADC being brought up over I²C
before they have power, a fault in either device takes its own pickup down, and
startup sequencing gains a step — a step that turns out to be load-bearing for
the coupling-cap polarity, so it is specified rather than incidental (§6,
`adc-firmware-init.md` §3.4).

**The budget is not close to tight.** Four channels draw 0.24–1.22 mA across the
part spread (§2) against a 20 mA per-device capability — under a tenth of it. The
ceiling does not, on its own, foreclose higher-current device classes here; the
battery-life argument and the pinch-off-headroom argument in §2 are what do.

**Documented fallback:** the 3.3 V analog rail — regulated, no device
dependency, no current limit, but shared with digital loads. This is a
**one-net schematic change** either way, so the decision is cheap to revisit if
MICBIAS startup behaviour disappoints on the bench.

---

## 6. Output coupling — on the main board, not here

The buffer output leaves the board **DC-coupled**, at the JFET source
potential. The blocking capacitor that removes that DC sits at the ADC input on
the main board, where it forms the high-pass corner against the ADC's
programmable input impedance (`adc-netlist.md` §2).

This is deliberate and worth stating explicitly, because it is easy to get
wrong in both directions:

- Putting a series cap **here as well** would put two blocking caps in the
  signal path, moving the corner and defeating the near-DC requirement.
- The main board's cap is polarised (tantalum), **positive terminal toward the
  converter**, with a parallel silicon clamp diode, cathode the same way.

**Why that polarity is safe, and what keeps it safe.** The converter self-biases
its AC-coupled input pins to VREF/2 ≈ 1.375 V. The buffer presents its source
node, 0.13–0.67 V across the full part spread (§2). The converter side is
therefore higher by at least 0.7 V in every steady state, including with MICBIAS
gated off — the buffers take their rail from the converter, so they cannot be
live while it is not.

The guarantee is structural rather than a property of the chosen part. A
self-biased source follower's DC output *is* its gate-source voltage magnitude,
which cannot exceed the device's |Vgs(off)| — at pinch-off the device stops
conducting and the source node cannot rise further. So:

> **Selection rule for any future JFET substitution:** the device's |Vgs(off)|
> **maximum** must sit below the converter's input bias. Then the coupling cap
> cannot reverse at any source-resistor value, anywhere in the Idss
> distribution, under any supply.

The chosen device's −1.5 V spec limit is nominally just above that bias, but
that limit is only approached as the source resistor tends to infinity and drain
current to zero; at 2.2 kΩ the worst corner lands at 0.67 V. This is the same
constraint that eliminates most of the SOT-23 JFET catalogue in §2, arriving
from the other direction.

The remaining exposure was a power-sequencing transient — buffer rail live
before the converter's input common-mode is established — and it is closed from
two directions: firmware powers the input channels before MICBIAS
(`adc-firmware-init.md` §3.4), and the clamp diode covers the window regardless.
Full treatment in `adc-netlist.md` §2.

---

## 7. Supply distribution and channel crosstalk

A source follower's drain current is signal-dependent, and a source follower
has poor supply rejection because the drain ties straight to the supply. Shared
supply impedance therefore turns that AC current into channel-to-channel
crosstalk.

**On these boards the effect is negligible.** With a solid supply pour of a few
tens of mΩ, the resulting coupled voltage lands around −100 dB relative to
signal. The crosstalk argument alone does not justify extra components.

**Where it does matter** is the wire run to the cavity, plus MICBIAS's own
output impedance, which rises with frequency — this is the basis of the
datasheet warning about common impedance when MICBIAS feeds multiple loads, and
the reason `layout-notes.md` §7 item 7 calls for star-routing MICBIAS at the
pin rather than daisy-chaining.

**Include a per-channel series resistor and local decoupling capacitor anyway**,
with the capacitor placed *after* the resistor, from the local supply node to
ground. The justification is **RF isolation, not crosstalk**: it makes local
decoupling far more effective at high frequencies and stops each channel
injecting onto the shared bus. The DC drop is a few tens of mV — irrelevant. A
ferrite bead would also work, but at these currents the resistor is simpler and
more predictable.

---

## 8. Per-channel circuit

Values are given by function rather than designator; take designators from the
schematic at entry.

| Function | Value | Package | Notes |
|---|---|---|---|
| N-JFET source follower | **MMBFJ201** (onsemi), LCSC C891687 | SOT-23 | Pin 1 drain, pin 2 source, pin 3 gate. ⚠ **Pinouts differ between manufacturers** — carry the LCSC number on the symbol, and re-verify if the part is ever substituted (§11) |
| Gate series resistor | 1 kΩ | 0402 | RF filter, from coil hot terminal to gate |
| Gate shunt capacitor | 100 pF C0G | 0402 | RF filter to ground, at the gate |
| Source resistor | 2.2 kΩ, **thin film** | 0402 | Sets operating point with Idss (§2). Thin film is required here — see the component rules below |
| Supply series resistor | 100 Ω | 0402 | From shared supply bus to this channel's local node |
| Local supply decoupling | 100 nF | 0402 | Local node to ground, **after** the series resistor, at the drain |
| Coil landing pads | — | custom THT | Magnet-wire pads; hot to the gate resistor, cold to the ground pour |

Per board: one supply bus from the connector to all four channel series
resistors — a pour or wide trace, not a thin trace — and a ground pour on both
layers, stitched.

The coil provides the gate's DC path, so there is no gate bias resistor.

### 8.1 Component type rules

These apply board-wide, including the test summing stage (§12), and are stated
here because they are easy to lose when values are picked from a stock list.

**Class I (C0G/NP0) dielectric for every capacitor in the signal path — no
exceptions.** Class II dielectrics (X7R, X5R) have a voltage coefficient that
converts signal swing across the part into distortion, and they are
piezoelectric, which is a real rather than theoretical concern for a part
rigidly mounted to a vibrating instrument. Class II remains correct for supply
decoupling and for bias-network bypassing, where the AC voltage across the part
is negligible; those two cases are called out explicitly wherever they appear.

**Thin film wherever DC crosses a signal-path resistor.** Thick film's excess
(current) noise is 1/f and scales with the DC voltage across the part, and thick
film carries a voltage coefficient of roughly ±100 ppm/V that produces
distortion under the same condition. On the per-channel circuit this applies to
the **source resistor and only the source resistor** — it carries the follower's
full drain current and sits directly in the signal path as the follower's load.
The gate series resistor passes picoamps of gate leakage, so it has no DC drop
and no exposure; thick film is fine there and everywhere else on the board.

Note that neither mechanism appears in a SPICE netlist: the resistor primitive
models 4kTR thermal noise only, with no excess noise and no voltage coefficient,
and vendor JFET models generally leave the flicker-noise coefficients at zero.
Simulated noise floors for this board should be read as optimistic lower bounds,
and the real numbers come from §11 item 6.

---

## 9. Connector and cable

**Constraints.** 0.75″ pickup width; very low profile under the bobbin; the
cable passes through a hole to the control cavity; very little space at the main
board edge; crimping avoided where possible.

**Selected: 1.0 mm pitch wire-to-board, right-angle SMT header**, roughly
2.9 mm tall (JST SH SM06B-SRSS-TB or equivalent).

Evaluated and rejected:

- **FFC/ZIF** — lowest profile at 1.0–1.2 mm and no crimping at all, but needs
  a ZIF socket at both ends and there is no room at the main board edge.
  Breakout boards and direct-soldering to FFC conductors were considered and
  judged worse than the alternative.
- **0.1″ right-angle headers** — roughly 8 mm tall.
- **1.5 mm pitch (JST ZH)** — easier to hand-solder but roughly 4.4 mm tall,
  which works against the clearance constraint.

**Configuration: 6-way per board** = four signals plus supply and ground. A
seventh *conductor* for a second ground was considered and rejected — with loose
round wires you do not control conductor adjacency, so flanking grounds buy
nothing. That idea only makes sense with ribbon or flat cable, where conductor
positions are fixed.

Note the schematic symbol carries seven positions against a `1x06-1MP`
footprint: the seventh is the connector's **mounting pad**, not a signal. Tie
it to the ground pour, and expect ERC to want it declared unconnected or
power-flagged rather than left floating.

⚠ **This supersedes the ribbon-cable treatment** previously in
`layout-notes.md` §6.3, including its recommended conductor ordering — that
analysis assumed flat ribbon with controlled adjacency.

**Housing without protrusions** is accepted because it is the stocked variant.
This gives up mechanical keying, so **the silkscreen needs a pin-1 marker and
an orientation outline, and the cable must be marked**. A reversed insertion
puts the supply rail onto a signal line and forward-biases a JFET gate through
the gate series resistor.

**Cable:** 28 AWG stranded, six conductors, loose — not twisted or shielded.
The low-impedance buffered outputs and the gate RC filter are what make that
viable. Runs under the preamp board to the control cavity. Buy long and cut
rather than coiling excess near the Bluetooth module.

**Brand mixing — cautionary.** There is no standard governing 1.0 mm
wire-to-board connectors; "compatible" is a manufacturer claim, not a
specification, and the available cross-reference information is thin and
secondhand. **Do not mix brands at the housing/header mating interface.** If
forced to, resolve it by physically mating sample parts, not by comparing
drawings.

**Sourcing and assembly.** Headers can ride the JLCPCB order; housings and
contacts are better sourced domestically for bench work, since the China route
runs 1–2 weeks. Trying a different pin count is a cheap way around a stock
problem while the board is unfabbed. Assembly sequence: solder the main-board
end first, pull the wires through the hole, *then* insert contacts into the
housing at the pickup — insertion-only, because 1 mm pitch contacts insert
easily but extract fiddlily. Pre-crimped pigtails avoid the crimp tool entirely
and can be cut to length, since the far end is being stripped anyway.

---

## 10. Layout

**Board organisation.** Two boards, four channels each, laid out with **Repeat
Layout** from a hierarchical sheet — which requires the schematic to instantiate
one channel four times rather than carry four flat copies. Place all four
groups first, *then* route the supply and output buses, or replication may drop
copied traces onto them. Anchor replication on the JFET in each instance.

**Connector placement: bottom side, at the end opposite the channels.** Bottom
side is driven by assembly access — room to seat the housing before plugging
into the bottom of the pickup assembly, and better cable-slack management
without pushing excess into the cavity. Centre placement was preferred but
loses to pad clearance against the bobbin locator holes. The cable runs under
the board to the cavity; a continuous ground pour between those wires and the
gate nodes is sufficient, since the barrier is capacitive interception and the
aggressors are low-impedance buffered outputs anyway.

**Gate node — the one place where less copper is better.** Keep the
coil-to-resistor-to-gate copper short and small, and do **not** pour ground
tight against it (stray capacitance and surface leakage). Siting the gate
resistor and shunt cap directly at the gate shrinks the exposed high-impedance
node to almost nothing. The shunt cap's ground pad wants a via straight down at
the pad — its RF function depends on near-zero inductance to ground. Same for
the local supply decoupling cap.

**Custom footprint for the magnet-wire landings.** Stock wire-connection
footprints bottom out around 1.4 mm outer diameter, far too large. Use
**0.4 mm drill / 0.8 mm pad**; 0.3/0.6 stacks two JLCPCB minimums — drill *and*
annular ring — and invites a DFM flag. Easiest route is to open a stock
test-point THT pad footprint, Save As into a personal library, and edit the
pad's hole and size fields, then redraw silkscreen and courtyard. The hole is a
*property of the pad*, not a separate selectable object.

**Assembly.** Single-sided JLCPCB assembly for the top, hand-solder the
bottom-side connectors — two-sided assembly incurs a second-pass setup charge
that is not worth it for one part per board. Ask JLCPCB to leave the connector
pads unpasted, or omit the connector from the assembly BOM. 1 mm pitch
hand-soldering is comparable to TSSOP: tack opposite corners, drag-solder with
flux, wick bridges.

**Heights.** SOT-23 is the tallest part on top at roughly 1.1 mm; the connector
is roughly 2.9 mm on the bottom. Total stack is roughly 5.6 mm on a 1.6 mm
board, 4.8 mm on 0.8 mm.

---

## 11. Verification before board spin

1. **JFET SOT-23 pinout — resolved for the specified part.** The chosen device
   is pin 1 drain, pin 2 source, pin 3 gate, which is what the schematic symbol
   maps, so the footprint and layout stand as drawn. ⚠ **This remains the
   highest-risk error in the layout if the part is ever substituted** — netlist
   review cannot catch a symbol-to-footprint pin mismatch, and the alternatives
   genuinely differ (the BF545 family, for instance, is pin 1 source, pin 2
   drain). Carry the distributor part number as a symbol field so the ordered
   part and the drawn pinout cannot drift apart.
2. **Connector mounting pad** — confirm it lands on the ground pour and is
   handled cleanly by ERC (§9).
3. **Physically mate connector samples** before committing to two boards,
   especially if brands end up mixed. Confirm housing stock and pin count
   before finalising the footprint.
4. **Verify the bottom ground pour is not fragmented into islands** under the
   gate areas after routing — the cable runs beneath the board and the pour is
   the barrier.
5. **Bench-measure the operating point** per channel — quiescent current,
   source voltage, and output impedance across the parts actually fitted (§2).
   This feeds the PGA and offset calibration constants in
   `adc-firmware-init.md`, and confirms the MICBIAS budget.
6. **Bench-measure noise floor per channel with the radio on and off** — this
   is what validates the gate RC filters (§4).
7. **Confirm MICBIAS startup behaviour** is acceptable as the buffer supply,
   else fall back to the 3.3 V analog rail (§5, one net).
8. **Confirm the summing bridges actually restore isolation** — measure
   channel-to-channel crosstalk with them open and closed (§12.4). Open should be
   indistinguishable from a board without the stage; if it is not, the leakage
   path is layout, not the resistors.
9. **Check the summing stage's operating point** on a fitted board — summed node
   DC, output resting voltage, and low-frequency corner (§12.2). The summed DC
   depends on where the fitted JFETs land in the Idss distribution, so it is
   worth recording alongside the per-channel measurements in item 5.
10. **Confirm the test header is dead when unpopulated** — no path from the
    amplifier's supply pin to the buffer rail with the header absent.

---

## 12. Test-only summing stage

**Purpose.** Sum the four buffered outputs to a single mono signal, so a fitted
preamp board can be played in an ordinary instrument — one with a single output
jack and a conventional active electronics board — with no main board present.
The point is to get playing feedback on the pickups themselves, in parallel with
DSP development rather than after it. Judgements about coil design, string
balance, aperture and attack should not have to wait on the digital hardware.

**Not present on production boards.** Every path into the stage is broken by a
solder-bridge footprint, and the stage's supply arrives on a header that is
simply left unpopulated. With the bridges open the board is electrically what it
would have been without the circuit.

### 12.1 Topology

**Passive summing into an active gain stage.** Four resistors from the four
buffer outputs into a common node, then one coupling capacitor into a
non-inverting amplifier biased at mid-rail.

**Why the summing is passive.** An inverting summing amplifier holds its
virtual ground at mid-rail, and each buffer's source node — 0.13–0.67 V, and
different per channel (§2) — would work against it at DC. Every input would need
its own blocking capacitor, and the resulting output offset would be the sum of
four uncorrelated errors multiplied by the feedback ratio. Summing passively
into a high-impedance node averages the DC offsets instead, so a single
capacitor after the node handles all four channels.

**Why the gain stage is not DC-coupled.** Direct coupling is fine at unity gain
and fails as soon as there is gain, in a way that is easy to miss. The summed DC
is 0.25–0.5 V depending where the fitted parts land in the Idss distribution; at
a gain of six the output would rest somewhere between 1.5 V and 3.0 V on a 3.7 V
rail, unpredictably. Even at unity gain the output would sit only 0.13–0.67 V
above ground, so negative swing would be limited to a couple hundred millivolts.
One coupling capacitor removes both problems.

**The DC-gain-of-one arrangement.** The divider that generates mid-rail must be
a *separate node* from the amplifier's non-inverting input — a bypass capacitor
sitting directly on the input would shunt the signal to ground. So: the divider
produces a bypassed mid-rail node; a bias resistor runs from that node to the
non-inverting input; the coupling capacitor delivers signal to the same input;
and **the lower gain-setting leg returns to the bypassed bias node rather than
to ground**.

That last detail is what keeps this circuit small. Both ends of the gain network
sit at the same DC potential, so DC gain is exactly one and the output rests at
mid-rail with full symmetric swing, while AC gain is set normally by the
resistor ratio. The bias voltage and the gain are then independent choices — the
divider does not have to be scaled to the gain. The bypass capacitor does three
jobs at once: it establishes DC gain of one, provides the AC ground the gain leg
needs, and shunts the divider's own thermal noise across the audio band, which
is what allows the divider resistors to be high-value without a noise penalty.

A useful side effect, given §8.1: **no signal-path resistor in this stage has
any DC across it.** The feedback resistor and the lower gain leg span equal
potentials, and the bias resistor sees zero volts because the coupling capacitor
blocks DC and the input therefore rests at exactly the bias node voltage. Thick
film's excess noise and voltage coefficient both scale with DC bias, so they
vanish here. The summing resistors are the only parts carrying any DC, and it is
at most a couple hundred millivolts.

### 12.2 Values

| Function | Value | Package | Notes |
|---|---|---|---|
| Amplifier | TLV9001 (TI) | SC70-5 or SOT-553 | 1.8–5.5 V, RRIO, 60 µA. CMOS inputs at 23 fA/√Hz, which is what makes the high source impedances free |
| Summing resistors (×4) | 100 kΩ | 0402 | One per channel, buffer output to the summing node |
| Input coupling | 5.6 nF **C0G** | 0402 | 28 Hz against 25 kΩ source plus 1 MΩ bias resistor |
| Bias resistor | 1 MΩ | 0402 | Bias node to non-inverting input |
| Divider pair | 100 kΩ / 100 kΩ | 0402 | Test supply to ground, generating the bias node |
| Divider bypass | 10 µF X5R | 0805 | **Not signal path** — Class II is correct here (§8.1) |
| Lower gain leg | 10 kΩ | 0402 | Returns to the bias node, **not** to ground |
| Feedback resistor | 49.9 kΩ | 0402 | Gain of 6.0 |
| Output coupling | 10 nF **C0G** | 0603 | 16 Hz into 1 MΩ, still 34 Hz into 470 kΩ |
| Amplifier decoupling | 100 nF | 0402 | Supply bypass, Class II fine |

The entire signal path is Class I. There is no polarised capacitor anywhere in
this stage — the megohm-class load is what makes that possible, and it is worth
contrasting with the main board, where the converter's 20 kΩ input impedance is
what forces a polarised part there (§6).

**Sizing notes.** The input coupling corner is set by the summing node impedance
(100 kΩ ÷ 4 = 25 kΩ) in series with the 1 MΩ bias resistor, so 5.6 nF gives
28 Hz — the DSP path's near-DC requirement does not apply to a stage feeding an
instrument amplifier, and relaxing the corner is what brings the capacitor into
Class I at an 0402 size. The divider bypass is sized against the lower gain leg,
not against leakage: it needs an impedance well below 10 kΩ at the lowest
frequency of interest, and 10 µF gives about 5% at 30 Hz.

**On the summing resistor value.** 100 kΩ is chosen on DC and crosstalk grounds,
not noise. Lower values increase the DC cross-current between channels, which
must be absorbed by a follower whose quiescent current falls to 61 µA at the
low-Idss corner (§2); at 100 kΩ the worst case is around 4 µA. They also worsen
the residual channel-to-channel coupling through the summing network with the
bridges closed — roughly −49 dB at 100 kΩ against about −43 dB at 47 kΩ. Noise
does not enter the decision, for the reason in §12.3.

### 12.3 Level and noise

**Gain of six restores coil level.** Passive averaging of four channels costs
12 dB for a single ringing string, since all four channels sum while only one
carries signal; the buffer contributes a further 4 dB (§2). Six times through
the whole chain lands at 0.93, so the stage hands the downstream electronics
roughly what a conventional pickup would. On a 3.7 V rail the output rests at
1.85 V with ±1.8 V available, which is far more headroom than the signal needs.

**Noise is dominated by the amplifier, and that is the design decision.** Referred
to the summing node:

| Contributor | nV/√Hz |
|---|---|
| Amplifier voltage noise | 30 |
| Summing node (25 kΩ) | 20.3 |
| Gain network (10 kΩ ‖ 49.9 kΩ) | 11.7 |
| Bias resistor (1 MΩ, shunted by the 25 kΩ source) | 3 |
| **Total** | **~38** |

About 5.4 µVrms over the audio band, or roughly 73 dB below signal. Because one
term dominates, the passive values are free to be chosen on the DC and crosstalk
grounds above: halving the summing resistors buys about 1.5 dB. The ceiling is
worth knowing before anyone is tempted to optimise — a 7 nV amplifier gains only
4 dB, because the summing node becomes the wall, and pushing both together gains
about 6 dB at 25× the supply current and a worse crosstalk figure. The chain sits
within 6 dB of its floor whatever is fitted, which is the argument for taking the
low-power part and stopping.

> ⚠ **Do not read the production noise floor off this stage.** The buffers
> contribute about 3.6 nV/√Hz at the summing node — negligible here, because
> passive summing attenuates each channel by four while this stage's own noise
> sits after that attenuation. The real signal chain has no summing network and
> no TLV9001 in it. This path is valid for judging tone and playability; it is
> not evidence about the noise performance of the instrument as built.

### 12.4 Test header and disconnection

**A separate 3-conductor THT header**, not additional contacts on the main
connector (§9), which is full at four signals plus supply and ground. Three
positions: summed output, ground, and test supply. Through-hole so it can be
hand-wired for a bench session and left unpopulated otherwise, and because
nothing about it needs to be small. Site it with the summing stage and away from
the gate nodes.

**Supply.** 3.7 V from a battery in the instrument, arriving on this header. The
amplifier would run equally well from the board's normal MICBIAS supply — 60 µA
against a 20 mA budget is nothing, and mid-rail at 1.5 V still leaves ±1.45 V —
but MICBIAS only exists when a converter is up, which by definition it is not in
the case this stage is built for.

**Disconnection: solder-bridge footprints on the four summing resistor inputs.**
These are required rather than belt-and-braces. Leaving them closed keeps a
resistive path between all four channels regardless of whether the amplifier is
powered, and per-channel isolation is the whole premise of the instrument. No
bridge is needed on the output or the supply — both arrive at the unpopulated
header.

For boards built purely for DSP work, simply omitting the four summing resistors
from the assembly BOM achieves the same isolation with nothing to solder. The
bridges exist so that a *fitted* board can be moved between the two modes.

---

## 13. Where the rest lives

| Topic | Document |
|---|---|
| ADC input stage, coupling caps, corner frequency, main-board connections | `adc-netlist.md` |
| Why the ADC, and what the architecture demands of it | `adc-selection.md` |
| Register configuration, gain and offset calibration, bring-up | `adc-firmware-init.md` |
| MICBIAS current budget and star-routing | `layout-notes.md` §6.1, §7 |
| Radio placement, cavity shielding constraints | `bluetooth-constraints.md` |
| Phase gates, bring-up order, risk register | `multichannel-audio-board-plan.md` |
