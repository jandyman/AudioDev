# Cavity Preamp Board — Design

**Status:** Schematic drawn (`String Preamp Test Board`). A single board in the
control cavity of a test instrument, taking the eight per-string signals and
producing a conventional instrument output.

**Scope:** the analog cavity electronics for a playable instrument built around
the multi-coil pickups without the DSP hardware present. The pickup boards
themselves are `preamp-board.md`; they are identical in both instruments and
nothing here changes them.

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
8 × pickup board → trim → passive sum (×2) → gain ×11 (×2) → pan → resonance → tone → volume → jack
                                                                                       ↑
                                                                            battery + charger
```

Per pickup group of four channels: a trimmer per string sets relative string
level, four resistors sum passively, one capacitor couples into one amplifier
that supplies all of the board's gain. The two group outputs feed a pan control,
then a volume control, a passive treble cut, and an output buffer into the jack.

**All the gain is in the two group stages.** Everything after the pan is unity.
This is deliberate — gain applied before the pan keeps both group outputs at the
same level and the same DC, which is what makes the pan silent — but it has one
consequence worth holding: **the volume control is downstream of the gain, so
turning down cannot rescue a clipping group stage.** See §5.

**Two amplifiers for the whole board.** That is a direct consequence of the
pickup boards providing gain: the signal arrives at conventional instrument level
from an output impedance of ohms, so this board does very little. Earlier
thinking about this board — per-channel gain stages, a coupling capacitor per
channel, careful low-noise resistor scaling, thirty-six decibels of makeup gain —
was all compensating for a front end that no longer exists.

---

## 3. Why the design is simple now

Three properties of the incoming signal do the work:

**Level.** 320 mV peak-to-peak per channel. After passive summing that is 80 mV
at the summing node, so the required gain is five rather than sixty-four. No
bandwidth problem, no need to split gain across stages, no need for a fast part.

**Impedance.** Ohms, not kilohms. The trimmers can be any convenient value and
the summing network can be chosen for noise rather than for loading.

**A common, known DC level.** Every channel arrives at the pickup board's bias
voltage, matched across all eight to resistor tolerance rather than spread five
to one. Passive summing therefore has no DC problem at all, and no per-channel
coupling capacitors are needed — two suffice for the whole board.

---

## 4. Values

**Per channel (×8):**

| Function | Value | Notes |
|---|---|---|
| Level trimmer | 20 kΩ single-turn SMT (Bourns TC33X or equivalent) | wired as a divider to ground, DC-coupled. Trimmer ranges run 1-2-5, so 20 kΩ rather than 22 kΩ |
| Summing resistor | 100 kΩ | four per group into a common node |

**Per pickup group (×2):**

| Function | Value | Notes |
|---|---|---|
| Coupling capacitor | 10 nF C0G | 15.5 Hz against the 25 kΩ node plus the 1 MΩ bias resistor |
| Bias resistor | 1 MΩ | mid-rail node to the non-inverting input |
| Feedback resistor | 22 kΩ | with the leg below, gain 11 |
| Lower gain leg | 2.2 kΩ | to ground through the return capacitor |
| Gain leg return capacitor | 22 µF X5R | to ground, not to the mid-rail node |
| Local decoupling | 100 nF | at the amplifier |

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

**Take the current saving in the pot value, not in an added part.** A fixed
resistor from the lower leg to ground would cap the range and halve the DC draw,
but it costs one part per channel; simply specifying 20 kΩ instead of 10 kΩ
achieves the same halving for nothing. The cost is a wiper impedance of ~5 kΩ
against 100 kΩ summing resistors — a tenth of a decibel of noise and 5% of
channel interaction, both immaterial inside a group whose channels are summed
anyway.

The trimmers carry the incoming DC across the wiper, so adjustment will be
audible if the instrument is live — set them with the amplifier turned down.
This is acceptable for a set-and-forget control inside a cavity and is not worth
eight coupling capacitors to avoid.

**The gain leg returns to ground through its capacitor, not to the mid-rail
node**, for the same reason as on the pickup boards: signal-frequency feedback
current into a shared node couples the two pickup groups together, directly
across the control that is supposed to separate them.

**Do not buffer the mid-rail node with an amplifier.** Noise on that node is
correlated across everything referencing it and does not average down. A passive
divider with a large bypass capacitor has its own thermal noise shunted to
nothing above a fraction of a hertz.

---

## 5. Level and noise

**Output: ≈880 mV peak-to-peak**, roughly twice conventional pickup level, with
the volume control available to trim.

**Headroom is set at the group stage.** With the chain as drawn — 40 mV p-p at
the coil, 7.82 at the pickup board, divided by four, times eleven — that stage
carries 860 mV p-p against 4.16 V p-p of available swing: **13.7 dB above
nominal playing level**, covering an attack roughly 4.8× harder than nominal.

That is a consequence of choosing a hot output rather than a problem. A gain of
5 would put the output at conventional pickup level and return the margin to
about 20 dB; gain of 11 spends 6.7 dB of it to deliver roughly twice
conventional level, which is normal for an active instrument and leaves the
volume control to trim.

**The remaining unknown is how far a hard attack sits above the 40 mV nominal,
and it is not worth analysing.** Fit the feedback resistor as an 0603, scope the
group stage output the first time the instrument is played hard, and change one
part if it clips. Note that the volume control is downstream of this stage, so
turning down will not disguise the problem if it exists. The pickup boards clip
later and are not the constraint — but their feedback resistor is worth making
0603 for the same reason, since it is unreachable once the boards are mounted.

**Signal-to-noise: approximately 75 dB**, A-weighted and peak-referenced,
against a front-end ceiling of 76 dB.

| Contributor | nV/√Hz at the summing node |
|---|---|
| Pickup boards (four channels, summed) | 41 |
| Summing resistors | 20 |
| Gain stage | 9 |
| Trimmers | 5 |
| **Total** | **47** |

**The whole board costs about one decibel.** That is the number worth
remembering, because it means component values here should be chosen for
convenience and for battery life, not for noise. Further optimisation of this
board improves nothing; the front end is the floor.

**This path is not evidence about the DSP system's noise floor.** It contains a
summing network and two amplifiers that the converter path does not, and the
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

The consequence is that the pickup boards' bias point tracks the battery, moving
between roughly 0.91 V and 1.27 V over a charge cycle. **On this instrument that
is harmless** — this board couples through a capacitor before any gain, so a
slowly moving DC reference is invisible. It is only on the main board, where the
bias point must stay in a known relationship to the converter's input bias, that
the value is load-bearing.

| Load | Current |
|---|---|
| Eight pickup channels | 6.08 mA |
| Cavity amplifiers (quad, four sections) | 0.24 mA |
| Trimmer dividers (20 kΩ) | 0.40 mA |
| Bias divider | 0.02 mA |
| **Total** | **≈ 6.7 mA** |

**About 15 hours on a 100 mAh cell**, and that is plugged-in time rather than
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

1. **Confirm the summing node's DC** sits where expected and moves as expected
   with the trimmers, on a board fed by real pickup boards.
2. **Measure crosstalk between the two pickup groups** with the pan control at
   centre. The mid-rail node is the path to suspect if it is worse than expected
   (§4).
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
7. **Check the low-frequency corner against the low string.** The group stage's
   coupling capacitor is the dominant pole in the whole chain — at 4.7 nF it
   lands at 33 Hz, which puts the low E fundamental about 2 dB down. 10 nF moves
   it to 15.5 Hz for no cost and no downside; there is nothing below the
   instrument's range worth blocking that the pickup boards do not already
   block.
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
| The resonant peak circuit and its gyrator | `resonance-emulator.md` |
| The per-string front end that feeds this board | `preamp-board.md` |
| Why the front end amplifies, and the system noise analysis | `analog-front-end.md` |
| The DSP instrument this one stands in for | `multichannel-audio-board-plan.md` |
