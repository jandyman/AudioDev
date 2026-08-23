# Noise analysis by hand — the string preamp

Four facts get you a noise figure for any op-amp stage in a few minutes. Applied
here to the actual preamp, they land within 0.5 % of what ngspice produces — which
is why hand analysis is the check on the simulator, not the other way round.

## The four facts

**1. A resistor makes √(4kTR) volts per root hertz.**
At room temperature that is **0.1287 × √R** nV/√Hz. Worth memorising one anchor and
scaling by √R from there:

| resistance | 100 Ω | 1 k | 2.2 k | 10 k | 15 k | 100 k | 1 M |
|---|---|---|---|---|---|---|---|
| nV/√Hz | 1.29 | **4.07** | 6.04 | 12.87 | 15.76 | 40.7 | 128.7 |

Ten times the resistance is only about three times the noise. This is why lowering
resistor values buys less than you would expect, and why raising them costs less.

**2. An op amp has two noise numbers on its datasheet.**
`en`, a voltage in series with the input, and `in`, a current that flows through
whatever source impedance you present. For this part: **7.4 nV/√Hz**, and a current
noise of 2 fA/√Hz that is irrelevant at these impedances (2 fA through 1 k is
0.002 nV/√Hz). There is also a **flicker corner at 54 Hz**, below which the voltage
noise rises as 1/√f.

**3. Every source has its own gain to the output — and they are not all the same.**
This is the part that is easy to get wrong. Anything in series with the input sees
the full noise gain 1 + Rf/Rg. The gain-leg resistor sees Rf/Rg. The feedback
resistor sees 1.

**4. Uncorrelated sources add in power.**
Root-sum-square the contributions, then multiply by √(bandwidth) for an RMS figure.
Because it is a square law, the largest contributor dominates hard: a source 3×
smaller than another adds only 5 % to the total.

## The stage, with each multiplier marked

<svg viewBox="0 0 1000 430" style="width:100%;height:auto;max-width:1000px" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Preamp stage annotated with each noise source and its gain to the output">
<rect x="0" y="0" width="1000" height="430" fill="#fbfaf7"/>
<g font-family="ui-sans-serif,-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif">

<text x="26" y="32" font-size="16" font-weight="600" fill="#1f2933">Each noise source reaches the output through a different gain</text>
<line x1="26" y1="48" x2="974" y2="48" stroke="#d8d3c8" stroke-width="1"/>

<g stroke="#1f2933" stroke-width="1.6" fill="none" stroke-linecap="round">
<path d="M 40 156 H 90"/>
<rect x="90" y="146" width="56" height="20" fill="#ffffff"/>
<path d="M 146 156 H 260"/>
<path d="M 260 132 L 260 228 L 352 180 Z" fill="#ffffff"/>
<path d="M 352 180 H 440"/>
<path d="M 400 180 V 260 H 230 V 204 H 260"/>
<rect x="290" y="250" width="56" height="20" fill="#ffffff"/>
<path d="M 265 260 V 280"/>
<rect x="253" y="280" width="24" height="46" fill="#ffffff"/>
<path d="M 265 326 V 346"/>
</g>

<g fill="#1f2933"><circle cx="400" cy="180" r="3.4"/><circle cx="265" cy="260" r="3.4"/>
<path d="M 34 151 L 46 156 L 34 161 Z"/></g>

<g fill="#ffffff" stroke="#b4531a" stroke-width="1.6">
<path d="M 210 346 H 300 L 310 358 L 300 370 H 210 Z"/></g>
<text x="255" y="362" font-size="11.5" font-weight="600" fill="#b4531a" text-anchor="middle">VREF</text>

<g font-size="12" font-weight="600" fill="#1f2933">
<text x="268" y="161">+</text><text x="268" y="210">&#8722;</text>
</g>
<g font-size="12" fill="#1f2933">
<text x="118" y="139" text-anchor="middle">1 k</text>
<text x="318" y="243" text-anchor="middle">15 k</text>
<text x="288" y="308">2.2 k</text>
<text x="44" y="140">in</text>
<text x="412" y="168">out</text>
</g>

<g font-size="12.5" font-weight="600" fill="#b4531a">
<text x="118" y="185" text-anchor="middle">&#215; 7.82</text>
<text x="196" y="128" text-anchor="middle">&#215; 7.82</text>
<text x="318" y="286" text-anchor="middle">&#215; 1</text>
<text x="288" y="326">&#215; 6.82</text>
<text x="196" y="391" text-anchor="middle">&#215; 1</text>
</g>
<text x="196" y="112" font-size="11" fill="#5a6672" text-anchor="middle">amplifier</text>
<text x="196" y="406" font-size="11" fill="#5a6672" text-anchor="middle">buffer noise</text>

<rect x="470" y="70" width="504" height="330" rx="6" fill="#f4f1ea" stroke="#ddd6c6" stroke-width="1.2"/>
<text x="492" y="98" font-size="12.5" font-weight="600" fill="#3d4b57">source &#215; its own gain = contribution at the output</text>
<g font-size="12" fill="#3d4b57">
<text x="492" y="128">op-amp voltage noise</text><text x="800" y="128" text-anchor="end">7.40 &#215; 7.82</text><text x="952" y="128" text-anchor="end">57.9</text>
<text x="492" y="152">2.2 k gain leg</text>       <text x="800" y="152" text-anchor="end">6.04 &#215; 6.82</text><text x="952" y="152" text-anchor="end">41.2</text>
<text x="492" y="176">1 k input series</text>     <text x="800" y="176" text-anchor="end">4.07 &#215; 7.82</text><text x="952" y="176" text-anchor="end">31.8</text>
<text x="492" y="200">15 k feedback</text>        <text x="800" y="200" text-anchor="end">15.76 &#215; 1</text> <text x="952" y="200" text-anchor="end">15.8</text>
<text x="492" y="224">buffer, through VREF</text> <text x="800" y="224" text-anchor="end">7.40 &#215; 1</text>  <text x="952" y="224" text-anchor="end">7.4</text>
</g>
<line x1="492" y1="240" x2="952" y2="240" stroke="#c9c0ac" stroke-width="1"/>
<text x="492" y="264" font-size="12.5" font-weight="600" fill="#1f2933">root-sum-square</text>
<text x="952" y="264" font-size="12.5" font-weight="600" fill="#1f2933" text-anchor="end">79.7 nV/&#8730;Hz</text>

<g font-size="12" fill="#4a5560">
<text x="492" y="296">&#215; &#8730;(20 kHz band), plus the 54 Hz flicker tail</text><text x="952" y="296" text-anchor="end">11.33 &#181;V</text>
<text x="492" y="320">&#247; 7.82 to refer it back to the input</text><text x="952" y="320" text-anchor="end">1.449 &#181;V</text>
<text x="492" y="344">against 84.8 mV rms full scale</text><text x="952" y="344" text-anchor="end">95.4 dB SNR</text>
</g>
<line x1="492" y1="360" x2="952" y2="360" stroke="#c9c0ac" stroke-width="1"/>
<text x="492" y="384" font-size="11.5" fill="#6b7580">ngspice, same circuit, legitimate sources only:</text>
<text x="952" y="384" font-size="11.5" font-weight="600" fill="#6b7580" text-anchor="end">1.451 &#181;V</text>

</g>
</svg>

## Where the noise actually comes from

| source | share of noise power |
|---|---|
| op-amp voltage noise | 52.6 % |
| 2.2 k gain leg | 26.7 % |
| 1 k input series | 15.9 % |
| 15 k feedback | 3.9 % |
| buffer, through the reference | **0.9 %** |

The buffer costs **+0.04 dB**. That is the whole point of routing the reference to
both the pickup return and the gain-leg cold end: its noise arrives at ×1 while the
signal arrives at ×7.82. Send the reference to the gain leg alone and it would
arrive at ×6.82 instead — the same 7.4 nV/√Hz would become 50 nV/√Hz at the output
and the buffer would jump from 0.9 % to roughly 29 % of the noise power.

The knobs, if this ever needs to be quieter: the amplifier itself is half the power,
the feedback pair is another quarter, and the input series resistor is a sixth.
Dropping that resistor from 1 k to 100 Ω would remove 15 % of the noise power for
free, if the RF protection it provides can be given up.

## Sanity-checking a simulation in two minutes

1. **Compute the largest single contributor by hand.** Here, 7.4 nV/√Hz × 7.82 = 58
   nV/√Hz. The reported total must be at least that and no more than about twice it.
2. **Divide the output figure by the input-referred figure.** It must equal the
   stage gain. If it does not, the source's AC magnitude is wrong.
3. **Check the shape.** With a 54 Hz flicker corner, the spectrum must rise
   noticeably below about 50 Hz. Dead flat means the flicker is missing or something
   white is swamping it.
4. **Check the floor.** Resistor noise is pure physics from values you know. A total
   below the root-sum-square of the resistors alone is impossible, and means the
   measurement is misconfigured rather than the circuit being quiet.

Check four caught the macromodel problem on this design: the reported total was in
millivolts because roughly a hundred internal resistors that the model intends to be
noiseless were generating thermal noise, swamping every real source by two orders of
magnitude. Everything above was still recoverable, because the individual
contributions are reported per device and the genuine ones can be summed separately.
