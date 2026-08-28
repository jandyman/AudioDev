<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 940 470" width="100%" style="max-width:940px">
  <style>
    .bg   { fill: #fbfbfa; }
    .wire { stroke: #3a3a38; stroke-width: 2.2; fill: none; stroke-linecap: round; stroke-linejoin: round; }
    .comp { stroke: #c25a3a; stroke-width: 2.4; fill: none; stroke-linecap: round; stroke-linejoin: round; }
    .plate{ stroke: #c25a3a; stroke-width: 3.2; stroke-linecap: round; }
    .amp  { stroke: #4a6fa5; stroke-width: 2.4; fill: #fbfbfa; stroke-linejoin: round; }
    .node { fill: #3a3a38; }
    .sym  { fill: #3a3a38; font: 600 15px ui-sans-serif, system-ui, sans-serif; text-anchor: middle; }
    .role { fill: #7a7a74; font: 400 12px ui-sans-serif, system-ui, sans-serif; text-anchor: middle; }
    .pin  { fill: #4a6fa5; font: 700 19px ui-sans-serif, system-ui, sans-serif; text-anchor: middle; }
    .io   { fill: #3a3a38; font: 600 15px ui-sans-serif, system-ui, sans-serif; }
    .bias { fill: #7a7a74; font: 400 11px ui-sans-serif, system-ui, sans-serif; text-anchor: middle; }
    .ttl  { fill: #3a3a38; font: 700 16px ui-sans-serif, system-ui, sans-serif; }
    @media (prefers-color-scheme: dark) {
      .bg { fill: #1c1c1a; }
      .wire { stroke: #d6d3cd; } .node { fill: #d6d3cd; }
      .comp, .plate { stroke: #e08a63; }
      .amp { stroke: #7fa3d8; fill: #1c1c1a; }
      .sym, .io, .ttl { fill: #e8e6e1; }
      .role, .bias { fill: #9a9790; }
      .pin { fill: #7fa3d8; }
    }
  </style>
  <rect class="bg" x="0" y="0" width="940" height="470"/>
  <text class="ttl" x="24" y="30">Equal-component Sallen-Key low-pass with input attenuator</text>

  <text class="io" x="24" y="206">In</text>
  <line class="wire" x1="45" y1="200" x2="95" y2="200"/>
  <path class="comp" d="M 95 200 L 105 200 L 111 190 L 123 210 L 135 190 L 147 210 L 153 200 L 165 200"/>
  <text class="sym"  x="130" y="178">R_top</text>
  <text class="role" x="130" y="162">attenuator, top leg</text>
  <line class="wire" x1="165" y1="200" x2="250" y2="200"/>

  <circle class="node" cx="250" cy="200" r="4.5"/>

  <line class="wire" x1="250" y1="200" x2="250" y2="268"/>
  <path class="comp" d="M 250 268 L 250 278 L 240 284 L 260 296 L 240 308 L 260 320 L 250 326 L 250 336"/>
  <line class="wire" x1="250" y1="336" x2="250" y2="358"/>
  <line class="wire" x1="232" y1="358" x2="268" y2="358"/>
  <line class="wire" x1="239" y1="366" x2="261" y2="366"/>
  <line class="wire" x1="246" y1="374" x2="254" y2="374"/>
  <text class="sym"  x="190" y="296">R_bot</text>
  <text class="role" x="190" y="312">attenuator, bottom leg</text>
  <text class="bias" x="250" y="394">mid-rail bias</text>

  <line class="wire" x1="250" y1="200" x2="250" y2="86"/>
  <line class="wire" x1="250" y1="86" x2="455" y2="86"/>
  <line class="plate" x1="455" y1="66" x2="455" y2="106"/>
  <line class="plate" x1="464" y1="66" x2="464" y2="106"/>
  <line class="wire" x1="464" y1="86" x2="760" y2="86"/>
  <text class="sym"  x="459" y="54">C</text>
  <text class="role" x="516" y="90">feedback cap</text>

  <path class="comp" d="M 285 200 L 295 200 L 301 190 L 313 210 L 325 190 L 337 210 L 343 200 L 355 200"/>
  <line class="wire" x1="250" y1="200" x2="285" y2="200"/>
  <line class="wire" x1="355" y1="200" x2="405" y2="200"/>
  <text class="sym"  x="320" y="178">R</text>
  <text class="role" x="320" y="162">filter resistor</text>

  <circle class="node" cx="405" cy="200" r="4.5"/>
  <line class="wire" x1="405" y1="200" x2="405" y2="268"/>
  <line class="plate" x1="385" y1="268" x2="425" y2="268"/>
  <line class="plate" x1="385" y1="277" x2="425" y2="277"/>
  <line class="wire" x1="405" y1="277" x2="405" y2="302"/>
  <line class="wire" x1="387" y1="302" x2="423" y2="302"/>
  <line class="wire" x1="394" y1="310" x2="416" y2="310"/>
  <line class="wire" x1="401" y1="318" x2="409" y2="318"/>
  <text class="sym"  x="462" y="266">C</text>
  <text class="role" x="462" y="282">shunt cap, same value</text>
  <text class="bias" x="405" y="338">mid-rail bias</text>

  <line class="wire" x1="405" y1="200" x2="405" y2="170"/>
  <line class="wire" x1="405" y1="170" x2="490" y2="170"/>

  <polygon class="amp" points="490,130 490,270 585,200"/>
  <text class="pin" x="509" y="177">+</text>
  <text class="pin" x="509" y="240">&#8722;</text>

  <line class="wire" x1="490" y1="230" x2="462" y2="230"/>
  <line class="wire" x1="462" y1="230" x2="462" y2="388"/>
  <circle class="node" cx="462" cy="388" r="4.5"/>

  <path class="comp" d="M 462 398 L 462 408 L 452 414 L 472 426 L 452 438 L 472 450 L 462 456 L 462 466"/>
  <line class="wire" x1="462" y1="388" x2="462" y2="398"/>
  <text class="sym"  x="410" y="426">R_a</text>
  <text class="role" x="410" y="442">to bias &#8212; with R_b sets Q</text>

  <line class="wire" x1="462" y1="388" x2="520" y2="388"/>
  <path class="comp" d="M 520 388 L 530 388 L 536 378 L 548 398 L 560 378 L 572 398 L 578 388 L 590 388"/>
  <line class="wire" x1="590" y1="388" x2="760" y2="388"/>
  <text class="sym"  x="555" y="422">R_b</text>

  <line class="wire" x1="585" y1="200" x2="760" y2="200"/>
  <circle class="node" cx="760" cy="200" r="4.5"/>
  <line class="wire" x1="760" y1="86" x2="760" y2="388"/>
  <line class="wire" x1="760" y1="200" x2="860" y2="200"/>
  <text class="io" x="868" y="206">Out</text>
</svg>

# Sallen-Key Low-Pass — Design Guide

Design reference for the pickup-resonance simulator stage: a second-order
low-pass with a deliberate resonant peak, standing in for the electrical
resonance of a magnetic pickup. Names below are the symbols used in the
equations, not schematic annotations.

Component values are synthesised by `Sallen Key.py` in this folder. This
document is the reasoning behind what that script does and why the topology
was chosen; the script is the arithmetic.

## What the stage has to do

A magnetic pickup rolls off second order above a resonance set by its
inductance and the total shunt capacitance, with a peak of roughly +6 dB at
Q near 2. The simulator reproduces that shape from a low-impedance source, so
the preamp under test sees the right *frequency response*. It does not
reproduce the pickup's high and strongly reactive source impedance — a
separate concern, and a reason not to use this stage when characterising
anything impedance-dependent.

Targets: f₀ in the low kHz, Q near 2, and **unity passband gain**, so the
stage can be inserted without re-referencing every level measurement
downstream.

## The governing equations

For the general Sallen-Key low-pass with equal filter resistors R, a feedback
capacitor C₁, a shunt capacitor C₂, and non-inverting gain K = 1 + R_b/R_a:

$$\omega_0 = \frac{1}{R\sqrt{C_1C_2}} \qquad
\frac{1}{Q} = \frac{2 - n(K-1)}{\sqrt{n}}, \quad n = \frac{C_1}{C_2}$$

Two special cases matter:

- **Equal capacitors** (n = 1): Q = 1/(3 − K), so **K = 3 − 1/Q**. Gain is not
  a free choice — Q dictates it. f₀ = 1/(2πRC).
- **Unity gain** (K = 1): Q = ½√(C₁/C₂). Gain is free, but Q now costs
  capacitor ratio: Q = 2 needs 16:1.

Everything in between is available, which is the useful part.

## Why gain and Q cannot both be chosen

Solving the Q equation for the capacitor ratio gives a real n only when

$$K > 2 - \frac{1}{4Q^2}$$

At Q = 2 that floor is K = 1.9375. **Letting the two filter resistors diverge
does not help** — with equal capacitors the achievable gain is pinned near 2
regardless of the resistor ratio. The knob that decouples gain from Q is the
capacitor ratio, not the resistor ratio. This is worth stating explicitly
because the opposite is an easy and plausible-sounding assumption.

## The impedance trade

For a given largest capacitor C_max, the resistors scale as

$$R = \frac{\sqrt{n}}{\omega_0 \, C_{max}}$$

so buying gain freedom with capacitor ratio costs resistance as its square
root. At Q = 2:

| stage gain K | | ratio n | R, in units of 1/(ω₀·C_max) |
| :--- | :--- | :--- | :--- |
| 1.00 | 0 dB | 16.00 | 4.00 |
| 1.20 | +1.6 dB | 4.62 | 2.15 |
| 1.50 | +3.5 dB | 2.44 | 1.56 |
| 2.00 | +6.0 dB | 1.41 | 1.19 |
| 2.50 | +8.0 dB | 1.00 | **1.00** |

The equal-component case is the impedance optimum, and by a factor of four
against the unity-gain case. That is the one thing it is good at, and with a
capacitor ceiling in the single-digit nF it is decisive.

## The chosen form: equal component, gain removed at the input

Take the equal-component filter for its impedance, then delete its unwanted
gain with an attenuator whose Thévenin resistance *is* the first filter
resistor. For a target overall gain A and stage gain K, with α = A/K:

$$R_{top} = \frac{R}{\alpha} \qquad R_{bot} = \frac{R}{1-\alpha}$$

which satisfies R_top ∥ R_bot = R and R_bot/(R_top + R_bot) = α exactly. The
filter sees an unchanged source resistance, so f₀ and Q are untouched. Cost is
one extra part: the top leg replaces the filter resistor that was already
there, and only the bottom leg is new.

Consequences to accept:

- **Overall gain can never exceed K = 3 − 1/Q.** The attenuator only reduces.
- **The attenuator throws away signal before the noise is added**, so this is
  about 2 dB noisier input-referred than a true unity-gain divergent-cap
  design at the same f₀. That is a good trade only because the divergent-cap
  version needs four times the resistance, which more than gives the 2 dB back.
- **Both shunt legs return to the buffered mid-rail, not to ground.** A return
  to ground puts the bias voltage across the attenuator and shifts the
  operating point.

### One knob per parameter

A property worth protecting when tuning: in this form the **capacitors set f₀
and nothing else**, and the **R_b/R_a pair sets Q and nothing else**. Swap the
capacitor pair to move the resonance; the peak height does not move. In the
divergent-cap form the two are coupled — changing a capacitor moves both — so
retuning frequency means changing both capacitors in proportion.

## Sensitivity and what actually limits the build

$$S^Q_K = K \cdot Q$$

At Q = 2 that is 5: a 1% error in the R_b/R_a ratio is a 5% error in Q. Q is
the loose parameter in this design, and it is loose in the resistors.

Meanwhile f₀ depends directly on capacitance (sensitivity 1) and Q does not
depend on it at all — matched capacitors cancel out of Q entirely. So:

- **f₀ error is capacitor tolerance.** 5% capacitors give ±4% on f₀, which
  swamps any value-series rounding. Tightening resistors does nothing for f₀.
- **Q error is resistor tolerance in the Q network, multiplied by five.** 1%
  resistors give Q a roughly ±30% window at Q = 2. Only 0.1% parts in that
  one pair meaningfully narrow it.

Design for this rather than against it: if the resonance height matters, spend
on the Q pair; if the resonance frequency matters, spend on the capacitors.
The script's Monte Carlo prints both spreads.

## Which frequency is "f₀"

At Q = 2 the natural frequency, the response peak and the −3 dB point are
three different numbers spread 1.6:1. Specifying the wrong one is the most
common way one of these comes out wrong.

| | frequency | level relative to passband |
| :--- | :--- | :--- |
| peak | f₀·√(1 − 1/2Q²) = 0.935·f₀ | +20·log₁₀(Q/√(1 − 1/4Q²)) = +6.3 dB |
| f₀ | f₀ | +20·log₁₀(Q) = +6.0 dB |
| −3 dB | 1.485·f₀ | −3 dB |

The script takes the target in whichever sense is wanted and reports all three.

## Value series

Synthesise in E96 for the fab order. For hand-stuffing from a bench kit,
re-synthesise on the coarser series rather than rounding the E96 values — the
three resistors trade against each other, so a joint search on a 10%-spaced
grid does far better than 10%.

At f₀ ≈ 4.9 kHz, Q = 2, unity gain, 5.6 nF:

| series | error in f₀ | error in Q |
| :--- | :--- | :--- |
| E96 | −0.5% | −0.9% |
| E24 | −4.0% | −4.7% |
| E12 | +1.0% | +11.5% |
| E6 | −8.4% | −16.0% |

E24 costs less than the capacitor tolerance already present, so a kit build is
a reasonable stand-in for a fab build. E6 is not.

Note that **E48 lacks 1.50**, so it cannot form the exact 15k/10k ratio that
Q = 2 wants, and scores worse than E24 on that target despite being finer. A
series that is missing the one value the design leans on loses to a coarser
series that has it.

## Board-level requirements

**Do not hang capacitance on the output.** The filter's feedback capacitor
returns from the op-amp output, so anything that compromises that node
compromises the response. A capacitive load with insufficient series isolation
destabilises the amplifier and flattens the resonance completely — the peak
disappears and the corner collapses, while the passband gain stays correct, so
it does not look like a filter fault. Any downstream network that presents
capacitance to this node needs a series resistor sized for isolation first and
its filtering role second; a few tens of ohms is enough for isolation, and
anything larger should be chosen so its own corner sits clear of the audio
band.

**Op-amp gain-bandwidth.** A 1 MHz part is comfortable for f₀ up to about
5 kHz at Q = 2 — simulated peak height with the vendor macromodel differs from
the ideal-amplifier result by under 0.4 dB. Verify with the macromodel rather
than assuming, since the Q sensitivity amplifies any gain droop by K·Q.

**Bias node.** The attenuator bottom leg, the shunt capacitor and the Q
network all return to the buffered mid-rail. That node carries three returns
for this stage alone; anything on it couples directly into the response, so it
needs to stay well bypassed and low impedance across the audio band.

**Noise.** The filter resistors put roughly 40–60 nV/√Hz input-referred into
the signal path, depending on f₀ and the capacitor ceiling. That is several
times the input noise of a modern low-noise preamp, so this stage must be
bypassable if the board is also used to measure preamp noise.

## Verification checklist

- Feedback capacitor returns from the amplifier output, not from the bias rail
  — tying it to bias turns the circuit into a cascaded passive RC pair, Q
  collapses to about 0.33, and the passband gain is unchanged, so the fault is
  invisible except in the response shape.
- Attenuator Thévenin resistance equals the filter resistor.
- Overall gain does not exceed 3 − 1/Q.
- Both shunt legs and the Q network return to the buffered mid-rail.
- f₀, Q and gain recomputed from the snapped values, not the ideal ones.
- No unisolated capacitance on the output node.
- Frequency target stated in a known sense — f₀, peak, or −3 dB.

## Rejected alternatives

**Multiple-feedback (MFB).** Genuinely decouples gain, Q and f₀, but its
capacitor ratio requirement is C_shunt/C_fb ≥ 4Q²(1+A₀) — 32:1 for unity gain
at Q = 2, against 16:1 for the unity-gain Sallen-Key and 1:1 here. Since the
resistors scale as 1/(ω₀√(C₁C₂)), that ratio drives the geometric-mean
capacitance down and the resistors up: at a 5.6 nF ceiling, unity gain at
Q = 2 lands on 85 kΩ resistors and about 37 nV/√Hz. Bringing them to 10 kΩ
needs a shunt capacitor near 47 nF, which is out of C0G in any sensible
package and into X7R — voltage coefficient and dielectric distortion in the
signal path. Big capacitor or big resistor, and at audio neither is acceptable
here. Rejected on impedance, not on the ratio itself.

**Unity-gain Sallen-Key with divergent capacitors.** Correct and clean, with
lower Q sensitivity (0.5 rather than K·Q), but 16:1 ratio means four times the
resistance of the equal-component form — 59 kΩ against 15 kΩ at the same f₀
and capacitor ceiling. The attenuator approach reaches the same unity gain at
a quarter of the impedance. Worth revisiting only if the capacitor ceiling
rises substantially, at which point its better Q sensitivity starts to win.

**Gyrator-based synthetic inductor.** Explored first, as the most literal
model of a pickup. Abandoned after initial experimentation: more parts, an
extra amplifier in the signal path, and tuning behaviour that is harder to
reason about, in exchange for a response shape a two-pole section already
produces. Only worth reconsidering if the simulator ever needs to present a
realistic source *impedance* as well as a response, which a gyrator can do and
an active filter fundamentally cannot.
