# Cavity Preamp Board — Design

**Status:** Schematic drawn (`String Preamp Test Board`). A single board in the
control cavity of a test instrument, taking the eight per-string signals and
producing a conventional instrument output.

**Scope:** the analog cavity electronics for a playable instrument built around
the multi-coil pickups without the DSP hardware present. The pickup boards
themselves are `preamp-board.md`; they are identical in both instruments and
nothing here changes them.

⚠ **Revised 2026-08-26 to a DC-coupled chain on a generated reference.** This
board now **generates the instrument's reference** and sends it to both pickup
boards, the passive summing network is replaced by a true summing amplifier, and
every internal coupling capacitor and gain-leg return capacitor is deleted. The
reference decision is §3.1 and it is the one that reached back into
`preamp-board.md`: with two pickups and a blend control, this board's chain has
exactly one reference node, and two independently generated references would
differ by divider tolerance and put that difference across the blend wiper.

---

## 1. What this board is for, and what it is not

**It exists so the pickups can be played and judged before the DSP hardware is
finished.** Coil design, string balance, aperture, attack and the tonal
consequence of a resonance-free pickup are all questions that want a bass, an
amp and a room — not a bench. Waiting for the digital system to answer them puts
the two hardest development problems in series.

**It is temporary but it must be a real instrument.** Rehearsal-capable, not
demonstration-capable. That sets a floor on noise and on battery life and rules
out anything that needs supervision to stay working.

**It is not a product and not a fallback for the DSP board.** It is not on the
critical path, it does not need to be cost-optimised, and it should not accrete
features. If a decision here is close, take the one that gets the instrument
playing sooner.

---

## 2. Signal chain

```
                    reference generator ─┬─→ neck pickup board
                                         ├─→ bridge pickup board
                                         └─→ VG, the board's analog datum
                                              │
8 × pickup board → trim → summing amp (×2) → blend → buffer → filter → volume → output buffer → jack
                                                                                        ↑
                                                                             battery + charger
```

Per pickup group of four channels: a trimmer per string sets relative string
level, and four resistors carry the trimmed signals into a summing amplifier's
virtual ground. The two group outputs feed a blend control, then a buffer, the
filter, a volume control, and an output buffer into the jack.

**The chain is DC-coupled throughout and every stage rests at VG.** There is no
coupling capacitor and no gain-leg return capacitor anywhere on the board. The
one capacitor that remains is at the jack, and it is unavoidable because the
outside world is ground-referenced.

**Gain is now unity per input at the summing stage**, with the feedback resistor
fitted as an 0603 so it can be changed. ⚠ This supersedes the gain of eleven
previously specified here and the gain of five discussed alongside it: **both
figures had the passive network's 4:1 summing attenuation built into them.** A
true summing amplifier has no such attenuation, so a per-input gain of five would
put a single string at 1.6 V peak-to-peak and clip hard on anything more than
one. Unity gives roughly conventional pickup level from one string and leaves the
volume control to trim.

**The volume control is still downstream of the gain**, so turning down cannot
rescue a clipping summing stage. See §5.

**Six amplifier sections for the whole board** — two summing stages, a buffer
after the blend, the filter, the output buffer, and the reference buffer. That
count is still small, and it is a direct consequence of the pickup boards
providing gain: the signal arrives at conventional instrument level from an output
impedance of ohms, so this board does very little. Earlier
thinking about this board — per-channel gain stages, a coupling capacitor per
channel, careful low-noise resistor scaling, thirty-six decibels of makeup gain —
was all compensating for a front end that no longer exists.

---

## 3. Why the design is simple now

Three properties of the incoming signal do the work:

**Level.** 320 mV peak-to-peak per channel, which is already about conventional
instrument level, so the summing stage runs at **unity per input** rather than
supplying makeup gain (§2). No
bandwidth problem, no need to split gain across stages, no need for a fast part.

**Impedance.** Ohms, not kilohms. The trimmers can be any convenient value and
the summing network can be chosen for noise rather than for loading.

**A common, known DC level.** Every channel arrives at VG — not at a value
*matched* to VG but at VG itself, since this board generates the reference the
pickup boards run from (§3.1). The match is the pickup boards' re-buffer offset,
tens of microvolts, rather than a resistor tolerance. **No coupling capacitor is
needed anywhere on the board**, which is stronger than the "two suffice"
previously claimed here.

---

## 4. Values

**Per channel (×8):**

| Function | Value | Notes |
|---|---|---|
| Level trimmer | 10 kΩ single-turn SMT (Bourns TC33X or equivalent) | wired as a **rheostat in series with the summing resistor** — wiper tied to one end, forming part of the path from the channel to the virtual ground. It connects to VG nowhere |
| Summing resistor | 20 kΩ | in series with the trimmer, into the summing amplifier's virtual ground |

**Per pickup group (×2):**

| Function | Value | Notes |
|---|---|---|
| Feedback resistor | 20 kΩ, **0603** | unity per input with the summing resistor above; 0603 so the gain can be changed after the instrument is played hard (§5) |
| Non-inverting input | — | **directly to VG**, no divider and no series resistor. The CMOS input draws femtoamps, so a bias-balancing resistor is not merely unnecessary — it would add thermal noise at the stage's noise gain |
| Local decoupling | 100 nF | at the amplifier |

**Deleted from this table, and why.** The coupling capacitor, the 1 MΩ bias
resistor, the lower gain leg and its 22 µF return capacitor are all gone. With
every source resting at VG and the summing junction held at VG by feedback, both
ends of every summing resistor sit at VG, so no current flows at DC, none flows
in the feedback resistor, and **the output rests at VG exactly** — for any
trimmer setting, with no capacitor and no trimming. The only DC errors left are
the amplifier's offset multiplied by the noise gain, about 125 µV, and bias
current through the feedback resistor, which is nothing.

**Shared:**

| Function | Value | Notes |
|---|---|---|
| Mid-rail divider | 100 kΩ / 100 kΩ | from the battery rail |
| Divider bypass | 10 µF X5R | shunts divider noise across the audio band |
| Pan control | 100 kΩ, fed through 22 kΩ from each group output | zero DC across the wiper |
| Volume control | 100 kΩ audio taper | after the pan |
| Resonance emulator | replaces the post-pan buffer | **`resonance-emulator.md`** — gyrator-based peak, frequency and boost on trimmers |
| Tone control | 100 kΩ audio taper with 22 nF, loading the resonant tank | player control; see `resonance-emulator.md` §5. **Sits before the volume, not after** |
| Output coupling | 10–22 nF C0G | 7–16 Hz into a megohm load — **no polarised part is needed here** |
| Charger | TP4054, 30 kΩ program resistor | ≈33 mA into a 100 mAh cell |
| Output jack | 3-conductor, sleeve switching the supply | draw is plugged-in time only |

### 3.1 The reference — this board generates it, and it is the board's datum

**A divider on the battery rail, filtered at its tap, followed by a unity-gain
buffer.** The buffer's output is **VG**, and VG replaces ground as the return for
everything in the signal path. It drives:

- the non-inverting input of every amplifier on the board;
- the cold end of every trimmer;
- the cold end of every control that sits before the output capacitor — blend,
  volume, tone, and any ground-referenced return in the filter or the resonance
  emulator;
- **out to both pickup boards**, one conductor each, where it is filtered and
  re-buffered locally (`preamp-board.md` §3.1, §8).

Ground keeps only supply returns and the far side of the output capacitor.

**Why the generator is here rather than on the pickup boards.** This board blends
two pickups into one output, so its chain has exactly one reference node. Two
independently generated references differ by divider tolerance — ±38 mV with 1%
parts, ±4 mV with 0.1% — and a blend control puts that difference directly across
a wiper as a DC step. No tolerance budget makes it zero. The converter instrument
has no equivalent requirement, but the pickup boards are identical in both, so
this requirement sets the direction for both.

**The pickup boards re-buffer rather than using the incoming node raw**, which is
what keeps their gain-leg current off the cable. That matters at the converter,
not here; the reasoning is `adc-netlist.md` §2.1.

**Ratiometric, not a fixed voltage.** The reference is a fraction of the battery
rail, so it tracks the cell — headroom scales with charge state, which is what a
battery-powered board wants. A hard 1.85 V would sit above the amplifiers'
common-mode ceiling at end of discharge and would leave barely a volt of upward
swing there. §6 sets the ratio.

**Rail rejection is set by the top leg and the capacitor, not by the ratio.**
Above the filter pole the rail-to-VG transfer is 1/(2π·f·C·R_top), independent of
the divider ratio — so the ratio is free to set the voltage and the rejection is
tuned with the capacitor. ⚠ The rail here carries the charger, so this is worth
measuring rather than assuming (§7).

**Tantalum for the filter capacitor, not Class II** — VG is the worst place on
the board for a piezoelectric element, because it injects into every stage in
phase. ⚠ This supersedes the previous instruction *not* to buffer the mid-rail
node. That instruction was correct for an unbuffered divider feeding
non-inverting inputs only; it does not survive a node that four gain legs and
eight trimmers draw signal current from, and the buffer's noise is negligible
against what arrives from the front end.

### 3.2 Which stages load VG, and which do not

Worth writing down because it decides topology choices elsewhere:

| Stage | Loads VG? |
|---|---|
| Summing amplifier | **No.** Its plus input draws only a CMOS bias current; the signal current circulates between the sources and the amplifier's own output through the virtual ground |
| Trimmers | **No.** They sit in series in the summing path, between a source at VG and a virtual ground at VG, and connect to the reference nowhere |
| Sallen-Key filter | **Yes** — its capacitor to the reference, of order 20 µA at the corner. **The only VG load in the signal chain** |
| Any follower | **No** connection at all |
| A non-inverting stage *with gain* | **Yes**, and heavily — its lower gain leg carries the full feedback current |

**The rule that follows: where a stage needs gain, prefer the inverting form.**
Where it needs unity, a follower touches VG not at all. The board as drawn needs
no non-inverting gain stage anywhere.

The totals are tens of microamps into a buffer output impedance of milliohms, so
none of this is a current problem. It is a topology guide.

**Amplifier: OPA2376**, one dual package. The alternative is a low-power
general-purpose dual, which costs about 1.4 dB here and buys two and a half hours
of runtime — see §6. At these levels the front end dominates either way, so this
is a comfortable choice rather than a critical one.

**Single-turn linear trimmers are correct here — multiturn is not needed.**
A linear taper puts the useful region where a screwdriver can reach it:
attenuation is 20·log₁₀ of the wiper fraction, so −1 dB sits 11% into the
travel, −3 dB at 29% and −6 dB at 50%. Over roughly 250° of rotation that is
about **27° per decibel** near full-up, which makes half-decibel balancing a
visible nudge. (This reasoning does *not* transfer to the audio-taper volume
control, where the top of the range is deliberately compressed.)

⚠ **The DC-draw argument that previously chose 20 kΩ over 10 kΩ no longer
applies.** In series the trimmer draws **no DC at all**, so there is nothing to
halve, and the 0.40 mA it contributed to the battery budget disappears (§6). The
value now sets the trim *range* instead: gain is Rf/(R_sum + αR_pot), so a 10 kΩ
trimmer against a 20 kΩ summing resistor gives **0 to −3.5 dB**. Size it for the
string imbalance actually measured.

⚠ **The trim law changes with the topology, and it changes for the better.** The
divider law previously specified here is compressed at the top — 20·log₁₀ of the
wiper fraction, about 27° per decibel near full-up over 250° of rotation. The
series law is −20·log₁₀(1 + αR_pot/R_sum), which runs about **58° per decibel at
the top and 86° at the bottom**: gentler and far more even, which is what a
balance trim wants. What it gives up is the ability to attenuate to zero, which a
set-and-forget balance control does not need. **This supersedes the linear-taper
reasoning below**, which was written for the divider arrangement — a linear taper
is still correct, but for a different reason.

⚠ **The trimmers no longer carry DC across the wiper, and this supersedes the
warning previously given here** that adjustment would be audible on a live
instrument. In series between a channel output resting at VG and a summing
junction held at VG, the trimmer has the same potential at both ends at DC — so
there is no DC across the element, no step as it is turned, and no DC current
through the wiper contact, which is the classic scratchy-pot mechanism as well.
**Adjustment is silent, and it is silent for a structural reason rather than
because a capacitor is blocking something.**

**They also connect to VG nowhere**, which is what makes the summing stage a zero
VG load: the signal current runs from the channel output through the trimmer and
the summing resistor into the virtual ground, and out through the feedback
resistor to the amplifier's own output. Nothing passes through the reference.

---

## 5. Level and noise

**Output: ≈320 mV peak-to-peak from one string** at unity per input, which is
about conventional pickup level, with the volume control available to trim. ⚠
This supersedes the ≈880 mV previously stated here, which came from the gain of
eleven that a passive summing network required.

**Headroom is set at the summing stage, and it is set against a chord rather than
a note.** A true summing amplifier has no averaging, so four strings sounding
together add: ±156 mV becomes ±626 mV in the worst case of four in phase. Against
the swing available at VG on a nearly flat cell — ±1.42 V at mid-rail on 3.0 V —
that is **19 dB above one string at nominal playing and 7 dB above a
four-string chord**. On a fresh cell both figures improve by about 1.9 dB.

**Fit the feedback resistor as an 0603 and scope the summing stage the first time
the instrument is played hard.** The remaining unknown is still how far a hard
attack sits above the 40 mV nominal, it is still not worth analysing, and the
volume control is still downstream so turning down will not disguise the problem.
The pickup boards clip later and are not the constraint — but their feedback
resistor is worth making 0603 for the same reason, since it is unreachable once
the boards are mounted.

**Noise: the active summer costs about a decibel more than the passive network it
replaces**, and the reason is structural rather than a matter of values. In the
passive arrangement the amplifier's own noise was multiplied by its gain while
the signal was multiplied by gain/4, a ratio of 4. In an inverting summer with
four inputs the noise gain is 5 while the signal gain is 1, a ratio of 5 — the
extra factor is the "+1" in the noise gain. **Summing four sources with one
amplifier costs roughly the same either way; active summing is not adopted for
noise.**

| Contributor | nV/√Hz at the output, unity per input |
|---|---|
| Amplifier voltage noise × noise gain of 5 | 45 |
| Four summing resistors (20 kΩ) | 36 |
| Feedback resistor (20 kΩ) | 18 |
| Four trimmers, in series in the summing path | included above |
| **Summing stage total** | **≈ 55** |
| Pickup boards arriving, for comparison | 82 |

So the summing stage costs about **2 dB** on top of what arrives, against roughly
1.2 dB for the passive arrangement. ⚠ **Recompute this against the amplifier
actually fitted** — the figures above assume a 9 nV/√Hz part, and §6 changes the
amplifier selection for one section of the board.

**The lever, if it is ever wanted back, is the summing and feedback resistance
and the amplifier — not the feedback resistor alone.** Halving both resistances
takes the stage total to about 47 nV/√Hz and no further, because at that point
the amplifier's own noise times the noise gain is the floor, and the noise gain
is set by the number of inputs rather than by any resistor value.

**The reasons to go active are the other two.** The trimmers drive a virtual
ground, so their settings stop interacting through a shared passive node; and the
inverting topology keeps the gain network off VG entirely (§3.2).

**This path is not evidence about the DSP system's noise floor.** It contains a
summing network and several amplifiers that the converter path does not, and the
converter path applies its gain per channel before any summation. Judge tone and
playability here; judge noise on the real system.

---

## 6. Power and battery

The pickup boards take their supply from this board. **Feed them from the battery
rail directly**, through a series resistor and bulk capacitor, rather than
regulating to 3.3 V. A Li-ion cell spans roughly 3.0 to 4.2 V, which is inside
the amplifier's supply range at both ends, and a 3.3 V regulator would have no
headroom left at end of discharge. The amplifiers reject more than 80 dB of
supply noise across the audio band, which is what makes this acceptable — it is
the same argument that put them on a shared rail in the first place
(`analog-front-end.md` §4).

The consequence is that **VG tracks the battery**, which is what a
battery-powered board wants — headroom scales with charge state instead of being
fixed at the worst case. The whole chain is DC-coupled and every stage rests on
VG, so a slowly moving reference moves everything together and is invisible right
up to the output capacitor.

⚠ **The ratio is open, and the constraint that decides it is a common-mode
ceiling, not swing.** Mid-rail is the obvious choice and gives the best swing
symmetry — 1.50 V at 3.0 V, 1.85 V at 3.7 V, 2.10 V at 4.2 V. But the amplifier's
common-mode rejection is specified only to (V+) − 1.3 V, which is 1.70 V at end of
discharge, and **a follower's input common mode swings with the full signal**. At
mid-rail on a flat cell a follower carrying ±200 mV reaches exactly 1.70 V: no
margin. Inverting stages are immune, because their plus input never moves, and so
is the summing amplifier.

Two ways out, and they are not equivalent in effort:

- **Take a ratio of about 0.45** — 1.35 V at 3.0 V, 150 mV of margin at peak —
  for roughly 1 dB of swing symmetry. One resistor.
- **Make the exposed stages inverting**, so no common mode on the board ever
  moves: an inverting unity stage drives as well as a follower, and a
  multiple-feedback low-pass replaces a Sallen-Key with its plus input pinned at
  VG. Then mid-rail is comfortable at every state of charge. This is the better
  circuit; it costs redoing the filter in a different topology.

**The filter is a Sallen-Key and it simulates correctly**, so it is one of the
exposed stages rather than an immune one — its non-inverting input carries the
full signal. ⚠ A `Filter Doc.md` alongside the schematic draws a multiple-feedback
arrangement; **that file is stale and does not describe the circuit.** Together
with the buffer after the blend and the output buffer, three stages have a moving
common mode, which is what makes the ratio choice above a real decision rather
than a formality. Converting the filter is the expensive part of the second
option, since its values are already validated.

| Load | Current |
|---|---|
| Eight pickup channels plus two reference re-buffers | 7.6 mA |
| Cavity signal amplifiers (five sections, low-power) | 0.30 mA |
| Reference buffer (low-power — see below) | 0.06 mA |
| Trimmers | **0** — in series between two nodes at VG, so no DC flows |
| Reference divider | 0.02 mA |
| **Total** | **≈ 8.0 mA** |

**The reference buffer can be the low-power part.** ⚠ An earlier revision of this
section argued it could not, on the grounds that the trimmers pushed roughly
125 µA of summed signal current into VG and the buffer's output impedance would
turn that into leakage between the two pickup groups. **The trimmers sit in
series in the summing path and touch VG nowhere** (§3.2, §4), so that current does
not exist. The only signal current into VG is the filter's, of order 20 µA at its
corner, and even several ohms of output impedance puts the resulting leakage below
−70 dB. Confirm it at §7 item 2 rather than spending a milliamp against it in
advance.

**About 12 hours on a 100 mAh cell**, and that is plugged-in time rather than
elapsed time because the output jack's sleeve switches the supply.

The amplifier is a low-power quad, which costs roughly 1.4 dB against a
lower-noise part and saves 1.3 mA. At these levels the front end dominates
either way, so this is the right trade. **The trimmers still draw more than the
amplifiers do**, even at 20 kΩ — worth knowing, but going higher trades against
wiper impedance and buys little. If runtime ever matters, change the cell:
500 mAh is a physically minor difference in a control cavity and buys 4×.

**The charger shares the rail that now feeds the pickup boards.** Supply
rejection should cover it, but this is worth measuring rather than assuming
(§7 item 3).

---

## 7. Verification

1. **Confirm every stage output rests at VG**, on a board fed by real pickup
   boards, and confirm it **does not move with the trimmers**. Movement means a
   trimmer cold end has landed on ground rather than VG, which is the single most
   likely wiring error on this board and the one that quietly undoes the whole
   arrangement (§4).
2. **Measure crosstalk between the two pickup groups** with the blend control at
   centre, and again at each extreme. VG is the path to suspect if it is worse
   than expected, and the mechanism is the reference buffer's output impedance
   against the summed trimmer current (§6). A blend that will not fully isolate
   one pickup is this failure, not a fault in the control.
2a. **Measure VG at the buffer output and again at each pickup connector** with
   the instrument playing. A difference is signal current somewhere it should not
   be.
3. **Measure the noise floor with the charger active and inactive**, and with the
   instrument at various states of charge (§6).
4. **Confirm the pan control is silent through its travel** — both gain stage
   outputs should rest at exactly the same potential, so there should be no DC
   across it and no thump.
5. **Confirm no clipping on the hardest attack available**, at the gain stage and
   at the pickup boards, with a scope rather than by ear.
6. **Set string balance by ear and record the trimmer settings**, then compare
   them against the per-string coil measurements. A large discrepancy points at
   something structural in the pickup rather than at the trim.
7. ⚠ **There is no longer a low-frequency corner to check inside the board.**
   The chain is DC-coupled from the coil to the output capacitor, so the only
   pole is at the jack, into a megohm load. This supersedes the check previously
   here on the group stage's coupling capacitor, which no longer exists.
7a. **Confirm the trimmers are silent through their travel** with the instrument
   live, which they should now be — zero DC across the wiper means no step and no
   wiper current. If they click, the cold end is on ground.
7b. **Confirm the blend is silent through its travel**, which tests the same
   thing at the group level: both summing outputs should rest at exactly VG, so
   there should be no DC across the control.
7c. **Check the reference at power-up.** Its filter time constant sets how long
   the whole board takes to settle, and every stage rides it together — so it
   should appear as a common ramp with no differential artefact, not as a thump
   per stage.
8. **Simulate the resonance emulator before entry** (`resonance-emulator.md` §7).
   It is the only circuit on the board that wants simulation, and the reason is
   trimmer taper rather than risk.
9. **Play the instrument with the resonance defeated first.** Set the boost
   trimmer to minimum and listen to the pickups flat before deciding what the
   emulator should be doing. It is easier to judge what is missing than to judge
   whether a peak is the right peak.

---

## 8. Where the rest lives

| Topic | Document |
|---|---|
| The reference architecture this board now generates for | `preamp-board.md` §3.1 |
| Why the whole chain went DC-coupled | `analog-front-end.md` §6 |
| The resonant peak circuit and its gyrator | `resonance-emulator.md` |
| The per-string front end that feeds this board | `preamp-board.md` |
| Why the front end amplifies, and the system noise analysis | `analog-front-end.md` |
| The DSP instrument this one stands in for | `multichannel-audio-board-plan.md` |
