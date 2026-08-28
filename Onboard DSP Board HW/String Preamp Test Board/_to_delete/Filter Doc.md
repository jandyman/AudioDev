<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 940 460" width="100%" style="max-width:940px">
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
  <rect class="bg" x="0" y="0" width="940" height="460"/>
  <text class="ttl" x="24" y="32">Multiple-feedback low-pass — inverting, second order</text>

  <!-- input resistor -->
  <text class="io" x="24" y="256">In</text>
  <line class="wire" x1="46" y1="250" x2="95" y2="250"/>
  <path class="comp" d="M 95 250 L 105 250 L 111 240 L 123 260 L 135 240 L 147 260 L 153 250 L 165 250"/>
  <text class="sym"  x="130" y="228">R_in</text>
  <text class="role" x="130" y="212">sets gain with R_fb</text>
  <line class="wire" x1="165" y1="250" x2="255" y2="250"/>

  <!-- summing node -->
  <circle class="node" cx="255" cy="250" r="4.5"/>
  <text class="role" x="255" y="290">summing node</text>

  <!-- shunt cap to bias -->
  <line class="wire" x1="255" y1="250" x2="255" y2="312"/>
  <line class="plate" x1="235" y1="312" x2="275" y2="312"/>
  <line class="plate" x1="235" y1="321" x2="275" y2="321"/>
  <line class="wire" x1="255" y1="321" x2="255" y2="348"/>
  <line class="wire" x1="237" y1="348" x2="273" y2="348"/>
  <line class="wire" x1="244" y1="356" x2="266" y2="356"/>
  <line class="wire" x1="251" y1="364" x2="259" y2="364"/>
  <text class="sym"  x="318" y="310">C_shunt</text>
  <text class="role" x="318" y="326">the LARGE cap</text>
  <text class="bias" x="255" y="384">mid-rail bias</text>

  <!-- feedback resistor: summing node up and over to output -->
  <line class="wire" x1="255" y1="250" x2="255" y2="100"/>
  <line class="wire" x1="255" y1="100" x2="430" y2="100"/>
  <path class="comp" d="M 430 100 L 440 100 L 446 90 L 458 110 L 470 90 L 482 110 L 488 100 L 500 100"/>
  <line class="wire" x1="500" y1="100" x2="790" y2="100"/>
  <text class="sym"  x="465" y="78">R_fb</text>
  <text class="role" x="465" y="62">DC feedback, sets gain</text>

  <!-- coupling resistor: summing node to inverting input -->
  <path class="comp" d="M 300 250 L 310 250 L 316 240 L 328 260 L 340 240 L 352 260 L 358 250 L 370 250"/>
  <line class="wire" x1="255" y1="250" x2="300" y2="250"/>
  <line class="wire" x1="370" y1="250" x2="430" y2="250"/>
  <text class="sym"  x="335" y="228">R_couple</text>
  <text class="role" x="335" y="212">second Q / f&#8320; lever</text>
  <line class="wire" x1="430" y1="250" x2="430" y2="225"/>
  <line class="wire" x1="430" y1="225" x2="515" y2="225"/>
  <circle class="node" cx="430" cy="225" r="4.5"/>

  <!-- feedback cap: inverting input up and over to output -->
  <line class="wire" x1="430" y1="225" x2="430" y2="155"/>
  <line class="wire" x1="430" y1="155" x2="580" y2="155"/>
  <line class="plate" x1="580" y1="135" x2="580" y2="175"/>
  <line class="plate" x1="589" y1="135" x2="589" y2="175"/>
  <line class="wire" x1="589" y1="155" x2="790" y2="155"/>
  <text class="sym"  x="584" y="196">C_fb</text>
  <text class="role" x="584" y="212">the SMALL cap</text>

  <!-- op-amp -->
  <polygon class="amp" points="515,195 515,315 610,255"/>
  <text class="pin" x="534" y="232">&#8722;</text>
  <text class="pin" x="534" y="295">+</text>
  <line class="wire" x1="515" y1="285" x2="470" y2="285"/>
  <line class="wire" x1="470" y1="285" x2="470" y2="348"/>
  <line class="wire" x1="452" y1="348" x2="488" y2="348"/>
  <line class="wire" x1="459" y1="356" x2="481" y2="356"/>
  <line class="wire" x1="466" y1="364" x2="474" y2="364"/>
  <text class="bias" x="470" y="384">mid-rail bias</text>

  <!-- output -->
  <line class="wire" x1="610" y1="255" x2="790" y2="255"/>
  <line class="wire" x1="790" y1="100" x2="790" y2="255"/>
  <circle class="node" cx="790" cy="155" r="4.5"/>
  <circle class="node" cx="790" cy="255" r="4.5"/>
  <line class="wire" x1="790" y1="255" x2="870" y2="255"/>
  <text class="io" x="878" y="261">Out</text>
</svg>

# Multiple-Feedback Low-Pass — Synthesis Guide

Design reference for choosing components when laying out an MFB second-order
low-pass section. Component names below are the symbols used in the equations,
not schematic annotations.

## When to choose this topology

MFB is inverting and second order. Unlike Sallen-Key — where the non-inverting
gain directly sets the damping, so passband gain and Q are the same knob — MFB
lets you choose passband gain, Q and f₀ independently, subject to one capacitor
ratio constraint.

That independence is the reason to reach for it. The cost is impedance: see
"The practical constraint" below, which is usually what decides the question at
audio frequencies.

Being inverting, the stage contributes 180° at DC. On a single supply the
non-inverting input goes to the buffered mid-rail, and **the shunt capacitor
returns to that same bias node, not to ground** — returning it to ground
puts the bias voltage across it and wastes headroom.

## Component roles

- **R_in** — sets input impedance, and passband gain together with R_fb.
- **R_fb** — DC feedback from output to the summing node; A₀ = R_fb / R_in.
- **R_couple** — feeds the summing node into the inverting input; the second
  lever on Q and f₀.
- **C_shunt** — summing node to the bias rail. **This is the large capacitor.**
- **C_fb** — inverting input to output; the AC feedback path that makes the
  roll-off second order. **This is the small capacitor.**

## Design equations

$$A_0 = \frac{R_{fb}}{R_{in}} \qquad
\omega_0^2 = \frac{1}{R_{fb}\,R_{couple}\,C_{fb}\,C_{shunt}}$$

$$\frac{1}{Q} = \omega_0\,C_{fb}\left[R_{fb} + R_{couple}(1 + A_0)\right]$$

## The capacitor ratio constraint

Solving those for real resistor values gives a quadratic in R_fb whose
discriminant is non-negative only when

$$\frac{C_{shunt}}{C_{fb}} \;\ge\; 4\,Q^2\,(1 + A_0)$$

**The shunt-to-bias capacitor is the large one.** Getting this backwards — a
large feedback capacitor and a small shunt capacitor — has no solution at all;
the synthesis returns imaginary resistors no matter what f₀ you ask for.

Two consequences:

1. Gain costs ratio. Higher A₀ raises the required ratio proportionally.
2. Q costs ratio quadratically. A resonant peak at Q = 2 with unity gain needs
   32:1; Q = 3 needs 72:1.

## The practical constraint: impedance, not capacitance

The ratio requirement is the well-known part. The part that actually decides
whether MFB is usable at audio is what the ratio does to the resistors.

The resistors scale with the **geometric mean** of the two capacitors:

$$R \;\sim\; \frac{1}{\omega_0 \sqrt{C_{fb}C_{shunt}}} \;=\; \frac{\sqrt{C_{shunt}/C_{fb}}}{\omega_0\,C_{shunt}}$$

Pushing the ratio up to buy Q pushes the resistors up as its square root. So
for a given largest capacitor you can afford, high-Q MFB lands on large
resistors — with the thermal noise and bias-current offset that implies. The
only way back down is a physically larger C_shunt.

At f₀ = 2 kHz, Q = 2, unity gain, holding the ratio at 37:1:

| C_shunt | C_fb | R_fb | thermal noise of R_fb |
| :--- | :--- | :--- | :--- |
| 5.6 nF | 150 pF | 82.5 kΩ | 37 nV/√Hz |
| 10 nF | 270 pF | 46.2 kΩ | 28 nV/√Hz |
| 22 nF | 560 pF | 21.0 kΩ | 19 nV/√Hz |
| 47 nF | 1.2 nF | 9.8 kΩ | 13 nV/√Hz |
| 100 nF | 2.7 nF | 4.6 kΩ | 8.7 nV/√Hz |

Getting MFB resistors down to the 10 kΩ range at audio needs a shunt capacitor
in the tens of nF, which is out of C0G in any reasonable package. X7R there
brings voltage coefficient and dielectric distortion into the signal path, and
film in that value is physically large. **Big capacitor or big resistor — MFB
at audio makes you pick one.** That is the trade to weigh before choosing this
topology, and it is why a low-noise audio stage usually ends up Sallen-Key.

## Selection table

f₀ = 2 kHz, unity gain, shunt capacitor held at 5.6 nF, feedback capacitor
chosen about 15% past the minimum ratio, lower root:

| Target Q | Min ratio | C_fb | Actual ratio | R_in = R_fb | R_couple |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 0.500 | 2.0 | 2.2 nF | 2.5 | 19.4 kΩ | 26.5 kΩ |
| 0.707 (Butterworth) | 4.0 | 1.2 nF | 4.7 | 29.2 kΩ | 32.3 kΩ |
| 1.000 | 8.0 | 560 pF | 10.0 | 39.3 kΩ | 51.4 kΩ |
| 1.500 | 18.0 | 270 pF | 20.7 | 62.5 kΩ | 67.0 kΩ |
| 2.000 | 32.0 | 150 pF | 37.3 | 82.5 kΩ | 91.4 kΩ |
| 3.000 | 72.0 | 56 pF | 100.0 | 111.5 kΩ | 181.1 kΩ |

Note how the resistors climb with Q even though f₀ never moves.

## Synthesis procedure

1. Pick C_shunt as the largest capacitor the board and dielectric budget allow
   — this sets the impedance level, so bias it upward.
2. Compute the minimum feedback capacitor:
   $$C_{fb,\text{max}} = \frac{C_{shunt}}{4Q^2(1+A_0)}$$
   and choose a standard value **below** it, by 15–30%, for margin.
3. With r = C_shunt / C_fb and ω₀ = 2π f₀:
   $$R_{fb} = \frac{r - \sqrt{r^2 - 4Q^2(1+A_0)\,r}}{2\,Q\,\omega_0\,C_{shunt}}$$
   $$R_{in} = \frac{R_{fb}}{A_0} \qquad
     R_{couple} = \frac{1}{\omega_0^2\,C_{fb}\,C_{shunt}\,R_{fb}}$$
   The other root (`+` instead of `−`) is equally valid and gives a larger
   R_fb with a smaller R_couple; take whichever spreads the values better.
4. Snap the three resistors to E96, then **recompute f₀, Q and A₀ from the
   snapped values** using the design equations above. Rounding each resistor
   on its own moves Q more than it moves f₀.
5. Check the op-amp has gain-bandwidth of roughly
   100 · f₀ · Q · (1 + A₀) or better — 800 kHz for the Q = 2 row above.
   MFB loads the op-amp harder than Sallen-Key near f₀.

Worked example, the Q = 2 row snapped to E96: 82.5 kΩ input, 82.5 kΩ feedback,
90.9 kΩ coupling, 5.6 nF shunt, 150 pF feedback → f₀ = 2005 Hz, Q = 2.00,
A₀ = 1.00.

## Which frequency is "f₀"

f₀ is the natural frequency, and at any interesting Q it is neither the
response peak nor the −3 dB point. Specifying the wrong one is the most common
way these designs come out wrong:

| | frequency | level relative to passband |
| :--- | :--- | :--- |
| peak | f₀·√(1 − 1/2Q²) | +20·log₁₀(Q/√(1 − 1/4Q²)) dB |
| f₀ | f₀ | +20·log₁₀(Q) dB |
| −3 dB | f₀·√((b + √(b²+4))/2), b = 2 − 1/Q² | −3 dB |

At Q = 2 the peak sits at 0.935·f₀ and the −3 dB point at 1.485·f₀ — a 1.6:1
spread between the two.

## Verification checklist

- Shunt capacitor larger than the feedback capacitor, by at least 4Q²(1+A₀).
- Feedback capacitor lands on the inverting input, not the summing node.
  If both feedback elements tie to the summing node the circuit is degenerate:
  no current can flow through the coupling resistor into a virtual ground, so
  the summing node sits at the bias voltage and there is no signal path.
- Shunt capacitor and the non-inverting input both return to the buffered
  mid-rail, not to ground.
- f₀, Q and A₀ recomputed from the snapped E96 values, not from the ideal ones.
- Resistor thermal noise checked against whatever this stage feeds — at high Q
  the values here are large enough to matter.
