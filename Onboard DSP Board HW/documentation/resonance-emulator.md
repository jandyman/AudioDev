# Resonance Emulator — Design

**Status:** To be simulated, then entered. One amplifier section on the cavity
preamp board, replacing the buffer after the pan control.

**Scope:** the circuit that gives the instrument a pickup-like resonant peak,
the theory behind the simulated inductor it uses, and the tone control that
loads it. The board it sits on is `cavity-preamp-board.md`.

---

## 1. What this is for

The pickups measure **66 mH**, which puts their electrical resonance around
62 kHz — three and a half octaves above where a conventional pickup's sits. The
result is a sensor that is flat from DC past 20 kHz. That is exactly what the
DSP system wants and it is why the pickup is immune to cable capacitance
(`analog-front-end.md`), but it is also why the instrument does not sound like an
electric bass: the resonant peak at 2–5 kHz *is* the electric-instrument voice,
and this pickup has none.

The digital system will synthesise that peak properly, per string and tunable.
This circuit is the analog stand-in, so the pickups can be judged as instruments
before the DSP hardware exists.

**Two controls, both set by ear:** resonant frequency and boost, on trimmers
inside the cavity. Plus one player control — a tone pot that loads the resonance
the way a passive instrument's does.

---

## 2. Theory: making an inductor out of an amplifier

A resonance needs an inductor. A real one of the value required here — around
one henry — would be a physically large wound part with a lossy core and a
tendency to pick up hum, which is the wrong thing to put in a control cavity
next to a radio. A **gyrator** synthesises one from an amplifier, two resistors
and a capacitor.

### 2.1 The circuit

```
                          Cg
                  ┌───────┤├────────┐
                  │                 │
   A ──┬─── R1 ───┴──── (−)\        │
       │                    >───────┴─── (amplifier output)
       │          Vref ─── (+)/     │
       │                            │
       └─────────── R2 ─────────────┘
```

Port **A** behaves as an inductor to ground. The amplifier's non-inverting input
sits at the board's mid-rail reference, which is the AC ground everything here is
referred to.

### 2.2 Why it works

The amplifier holds its inverting node at Vref, so a voltage at A drives a
current through R1 that has nowhere to go but into Cg:

```
    V_A / R1  =  −V_out · sCg        →        V_out = −V_A / (s·R1·Cg)
```

The output is an **integrated, inverted copy** of the port voltage. R2 feeds that
back to the port. Because the output swings *opposite* to the port and grows as
frequency falls, the current R2 injects into A opposes the applied voltage more
and more strongly at low frequency — which is precisely what an inductor does.

Summing the currents into A:

```
    I  =  V_A/R1 + (V_A − V_out)/R2  =  V_A [ 1/R1 + 1/R2 + 1/(s·R1·R2·Cg) ]
```

so

```
    1/Z  =  1/R1 + 1/R2 + 1/(sL)          with      L = R1 · R2 · Cg
```

**An inductance L = R1·R2·Cg, shunted by R1∥R2.** The shunt is the loss term —
a real inductor's finite Q, arriving here as the parallel resistance that limits
how sharp the resonance can be.

### 2.3 What the equations tell you

Three consequences worth having in hand before choosing values:

**The inductance is a product of two resistors, so it scales fast.** Doubling
either resistor doubles L; the frequency moves as the square root, so a 4:1
resistor sweep gives a 2:1 frequency sweep. That is a comfortable ratio for a
trimmer — enough range to cover the useful territory without the ends being
useless.

**Q depends on R1 + R2, not on either alone.** Writing the tank Q with a series
resonating capacitor Cs:

```
    Q  =  √(R1 · R2 · Cs / Cg) / (R1 + R2)
```

Sweeping R2 for frequency therefore barely touches Q — it varies as
√R2/(R1+R2), which is symmetric about R2 = R1 and changes by only a few percent
over a 4:1 sweep. **Frequency and resonance sharpness are effectively
independent**, which is the property that makes this worth building rather than
a two-pole active filter, where they are locked together.

**High Q wants a small Cg.** Q rises as Cg falls, while L falls with it — so the
design pressure is toward a small gyrator capacitor and large resistors. 100 pF
with resistors in the tens of kilohms lands where we want; 10 nF with kilohm
resistors gives an inductance so heavily damped that the port looks resistive.
This is the one place where a plausible-looking set of values fails completely,
and it fails quietly.

### 2.4 What it is not

The gyrator makes a **grounded** inductor — one end is committed to the
reference. Floating inductors need two amplifiers. That is not a limitation
here, because the resonant branch is a shunt leg anyway.

It also cannot store energy the way a real inductor does; it is an amplifier
pretending, and it stops pretending when the amplifier runs out of output swing
or bandwidth. Both are checked in §7.

---

## 3. Producing the bump

The gyrator's port, in series with a capacitor, makes a **series-resonant
branch** — high impedance everywhere except near resonance, where it collapses
to its loss resistance. Hang that across the gain-setting leg of an otherwise
unity-gain stage and the stage develops a peak exactly there.

```
                             ┌──────── Rf ────────┐
                             │                    │
   IN ──────────────────────(+)\                  │
                               >──────────────────┴──── OUT
                        ┌────(−)/
                        │
                        ├──── Rg ──── Vref
                        │
                     R_boost                 ← trimmer: peak height
                        │
                        ├──────┬─── C_tone ── R_tone ──┐   ← player control: §5
                       Cs      │                       │
                        │      └───────────────────────┘
                        │
                   [ gyrator port A ]
```

**Away from resonance** the branch is high-impedance, the leg is just Rg, and
with Rg ≫ Rf the stage passes signal at unity. **At resonance** the branch
impedance drops to R_boost plus the tank's equivalent series loss, the leg
impedance collapses, and the gain rises to 1 + Rf/(R_boost + R_ESR).

Two properties fall out of this that the two-pole filter alternative does not
have:

**Passband gain does not move with the boost setting.** In a Sallen-Key section
the amplifier's gain sets Q, so the two are locked and turning up the resonance
turns up the whole signal. Here the boost control only affects a shunt branch
that is out of circuit except near resonance. Nothing upstream needs
rebalancing, and setting the control by ear is not confounded by level.

**There is no stability edge.** A Sallen-Key's Q goes to infinity at a gain of
exactly 3 — a trimmer that reaches it oscillates. Nothing in this topology has a
pole that can cross into the right half plane; the worst a trimmer at an extreme
can do is give a peak you dislike.

And one that is accidental but correct: **boost and sharpness are coupled the way
they are in a real pickup.** Raising the boost lowers the branch's series
resistance, which raises Q as well as height — so a taller peak is automatically
a narrower one, which is how coil resonances actually behave.

---

## 4. Values

| Function | Value | Sets |
|---|---|---|
| Gyrator R1 | 82 kΩ | with R2, the inductance |
| Gyrator R2 | 47 kΩ fixed **+ 200 kΩ trimmer** | **resonant frequency** |
| Gyrator Cg | 100 pF C0G | inductance and Q scaling |
| Series resonating cap, Cs | 6.8 nF C0G | with L, the frequency |
| Boost | 2.2 kΩ fixed **+ 20 kΩ trimmer** | **peak height** |
| Stage feedback, Rf | 10 kΩ | peak height with the branch |
| Stage lower leg, Rg | 1 MΩ | keeps the passband at unity |

Which gives:

| | Trimmer at minimum | Trimmer at maximum |
|---|---|---|
| Simulated inductance | 0.39 H | 2.0 H |
| Resonant frequency | **3.11 kHz** | **1.36 kHz** |
| Tank Q | 4.0 | 3.6 |
| Peak height (boost trimmer) | **+9.5 dB** | **+2.9 dB** |
| Passband gain | +0.09 dB — unity for practical purposes | |

The frequency range covers the territory a bass pickup's resonance actually
occupies. Q lands near 4 across the whole sweep, which is at the sharp end of
what real pickups do — deliberately, since the boost control only ever damps it
further.

**The boost control's law is compressed at the top.** Most of its travel covers
+3 to +6 dB and the last fifth covers +6 to +9.5 dB, because peak height goes as
the reciprocal of the branch resistance. That is acceptable for a set-once
trimmer; if it proves annoying, raise the fixed 2.2 kΩ to compress the range
rather than fighting the taper.

**Both capacitors must be Class I.** Cs carries the resonant current and Cg sets
the inductance — a dielectric with a voltage coefficient would make the
resonant frequency signal-dependent, which is a genuinely unpleasant failure
mode. This is the strongest case for C0G anywhere on the board.

---

## 5. The tone control that loads the resonance

A passive instrument's tone control is a pot and a capacitor **across the
pickup's own resonant tank**. Turning it down does two things at once: it adds
capacitance, which walks the resonance downward, and it adds damping, which
flattens it. The peak sweeps down and softens. A treble cut placed *after* a
fixed peak does not sound like that — it just removes the top.

The same behaviour is available here for two parts, by putting the tone network
in parallel with the series resonating capacitor:

| Function | Value |
|---|---|
| Tone capacitor, C_tone | 22 nF C0G |
| Tone pot, R_tone | 100 kΩ audio taper — the existing player control |

**At maximum resistance** the branch is isolated and the resonance sits where the
trimmers put it. **As resistance falls**, C_tone increasingly parallels Cs, the
branch capacitance rises toward 28.8 nF, and the resonance walks down by
√(6.8/28.8) — roughly an octave, so a 2.2 kHz peak descends to about 1.1 kHz.
**In between**, the pot's resistance is dissipating resonant current, which damps
the peak. Maximum damping occurs at mid-rotation, with the peak partly
recovering at the fully-down end.

That mid-rotation dip is not a defect to be engineered out. It is what a passive
tone control does, for the same reason, and it is a large part of why the control
sounds the way it does rather than like an equaliser.

**No DC crosses the pot.** Cs blocks it and the tone branch is in series with its
own capacitor, so there is nothing to make the control scratch as it is swept —
which matters here in a way it does not for the trimmers, because a player turns
this one.

Note this places the tone control **before** the volume rather than after it.
That is the conventional order on active instruments and it is required here:
the control has to reach the tank, and the tank is inside this stage.

---

## 6. Complete stage

```
                                    ┌──────── 10k ────────┐
                                    │                     │
   from pan ───────────────────────(+)\                   │
                                      >───────────────────┴──── to volume
                              ┌─────(−)/
                              │
                              ├─────── 1M ─────── Vref
                              │
                          2.2k + 20k trim              ← boost
                              │
                              ├──────────┬───── 22n ───── 100k pot ────┐
                             6.8n        │                             │
                              │          └─────────────────────────────┘
                              │                                      ← tone
                    ──────────┴──────────  gyrator port A
                              │
                              ├──── 82k ────┬──── (−)\
                              │             │         >──── out
                              │            100p  Vref─(+)/    │
                              │             │                 │
                              │             └───┤├────────────┤
                              │                                │
                              └──── 47k + 200k trim ───────────┘
                                                              ← frequency
```

**Two amplifier sections**, which is what the post-pan buffer and the output
buffer currently occupy. The output buffer's job is absorbed by this stage, whose
output impedance is low enough to drive the volume control directly.

---

## 7. What to check in simulation, before entry

**Simulation files:** `../simulation/resonance-emulator-ltspice.zip` — the full
stage in both schematic and netlist form, a separate port-impedance test for the
gyrator on its own, and a self-contained model library. Run the port-impedance
test first: if the port is not inductive, nothing downstream of it means
anything.

This is the one circuit in the project where LTspice earns its keep. The models
are all ideal enough to be trusted — unlike the noise work, where the device
models are the weak link (`analog-front-end.md` §8).

1. **Confirm the port really is inductive** across the audio band. Drive port A
   with an AC current source and plot the impedance magnitude and phase; it
   should rise at 6 dB/octave with a phase near +90° through the region of
   interest, flattening to R1∥R2 above. If the phase never gets near 90°, the
   loss resistance is swamping the inductance — see §2.3.
2. **Sweep both trimmers across their full travel** and confirm the ranges in §4,
   and that frequency and boost are as independent as the equations claim.
3. **Check the taper of both controls** and adjust the fixed series resistors so
   the useful range occupies most of the travel rather than a corner of it. This
   is quicker to see than to calculate and is the main reason to simulate.
4. **Sweep the tone control** and confirm the peak walks down and damps rather
   than simply rolling off.
5. **Check the amplifier's output swing at maximum boost.** The gyrator's
   amplifier swings its own signal, larger than the port voltage by the
   integrator's gain at low frequency. Confirm it does not clip below the main
   signal path's limits, especially at the low-frequency end of the trimmer
   range.
6. **Check loop stability** with the trimmers at both extremes. Nothing here
   should be marginal, but a gyrator is a feedback loop and it is cheap to
   confirm.
7. **Confirm behaviour with a low battery.** The reference moves with the supply,
   and the gyrator's amplifier has the largest internal swing on the board.

---

## 8. Where the rest lives

| Topic | Document |
|---|---|
| The board this sits on, and the rest of its signal chain | `cavity-preamp-board.md` |
| Why the pickup has no resonance of its own | `analog-front-end.md` |
| The per-string front end | `preamp-board.md` |
