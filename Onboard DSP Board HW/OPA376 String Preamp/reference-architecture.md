# String preamp — supply filtering and buffered mid-rail reference

Intended architecture for the four-channel string preamp strip. The stage is
DC-coupled: there is no capacitor in the gain leg, and no high-pass anywhere in the
preamp. Low-frequency limiting happens once, at the tantalum coupling capacitors on
the DSP board.

<svg viewBox="0 0 1120 510" style="width:100%;height:auto;max-width:1120px" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Schematic of supply filtering and buffered mid-rail reference">
<rect x="0" y="0" width="1120" height="510" fill="#fbfaf7"/>
<g font-family="ui-sans-serif,-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif">

<text x="26" y="34" font-size="17" font-weight="600" fill="#1f2933">Supply filtering and buffered mid-rail reference</text>
<text x="26" y="55" font-size="12.5" fill="#5a6672">DC-coupled stage — no capacitor in the gain leg, no high-pass in the preamp</text>
<line x1="26" y1="68" x2="1094" y2="68" stroke="#d8d3c8" stroke-width="1"/>

<g stroke="#1f2933" stroke-width="1.6" fill="none" stroke-linecap="round">

<!-- ===== rail ===== -->
<path d="M 90 120 H 118"/>
<rect x="118" y="110" width="42" height="20" fill="#ffffff"/>
<path d="M 160 120 H 250"/>
<path d="M 186 120 V 142"/>
<path d="M 174 142 H 198 M 174 150 H 198"/>
<path d="M 186 150 V 166 M 175 166 H 197 M 179 170 H 193 M 183 174 H 189"/>
<path d="M 222 120 V 98"/>
<path d="M 250 120 V 152"/>

<!-- ===== optional pre-filter block ===== -->
<rect x="196" y="142" width="132" height="124" stroke="#a8b0b8" stroke-width="1.2" stroke-dasharray="5 4" fill="none"/>
<rect x="238" y="152" width="24" height="44" fill="#ffffff"/>
<path d="M 250 196 V 216"/>
<path d="M 250 216 H 292 M 292 216 V 228"/>
<path d="M 280 228 H 304 M 280 236 H 304"/>
<path d="M 292 236 V 248 M 281 248 H 303 M 285 252 H 299 M 289 256 H 295"/>

<!-- ===== divider ===== -->
<path d="M 250 216 V 272"/>
<rect x="238" y="272" width="24" height="46" fill="#ffffff"/>
<path d="M 250 318 V 342"/>
<rect x="238" y="342" width="24" height="46" fill="#ffffff"/>
<path d="M 250 388 V 404 M 239 404 H 261 M 243 408 H 257 M 247 412 H 253"/>

<!-- ===== tantalum tap cap ===== -->
<path d="M 250 330 H 400"/>
<path d="M 320 330 V 350"/>
<path d="M 306 350 H 334 M 306 360 H 334"/>
<path d="M 320 360 V 376 M 309 376 H 331 M 313 380 H 327 M 317 384 H 323"/>

<!-- ===== buffer ===== -->
<path d="M 400 330 V 338 H 420"/>
<path d="M 420 290 L 420 354 L 486 322 Z" fill="#ffffff"/>
<path d="M 486 322 H 556"/>
<path d="M 506 322 V 278 H 406 V 306 H 420"/>

<!-- ===== channel: pickup ===== -->
<path d="M 622 189 H 660"/>
<path d="M 660 189 q 8.5 -15 17 0 q 8.5 -15 17 0 q 8.5 -15 17 0 q 8.5 -15 17 0"/>
<path d="M 728 189 H 764"/>
<rect x="764" y="179" width="44" height="20" fill="#ffffff"/>
<path d="M 808 189 H 856"/>
<path d="M 830 189 V 208"/>
<path d="M 818 208 H 842 M 818 216 H 842"/>
<path d="M 830 216 V 232 M 819 232 H 841 M 823 236 H 837 M 827 240 H 833"/>

<!-- ===== channel: amp, feedback, gain leg ===== -->
<path d="M 856 138 L 856 206 L 922 172 Z" fill="#ffffff"/>
<path d="M 922 172 H 962"/>
<path d="M 938 172 V 112 H 802 V 155 H 856"/>
<rect x="856" y="102" width="44" height="20" fill="#ffffff"/>
<path d="M 802 130 H 748"/>
<rect x="704" y="120" width="44" height="20" fill="#ffffff"/>
<path d="M 704 130 H 622"/>

</g>

<!-- junction dots -->
<g fill="#1f2933">
<circle cx="186" cy="120" r="3.2"/><circle cx="222" cy="120" r="3.2"/>
<circle cx="250" cy="216" r="3.2"/><circle cx="250" cy="330" r="3.2"/>
<circle cx="320" cy="330" r="3.2"/><circle cx="506" cy="322" r="3.2"/>
<circle cx="830" cy="189" r="3.2"/><circle cx="938" cy="172" r="3.2"/>
<circle cx="802" cy="130" r="3.2"/>
<path d="M 217 102 L 222 94 L 227 102 Z"/>
</g>

<!-- VREF net tags -->
<g fill="#ffffff" stroke="#b4531a" stroke-width="1.6">
<path d="M 556 310 H 612 L 622 322 L 612 334 H 556 Z"/>
<path d="M 556 118 H 612 L 622 130 L 612 142 H 556 Z"/>
<path d="M 556 177 H 612 L 622 189 L 612 201 H 556 Z"/>
</g>
<g font-size="11.5" font-weight="600" fill="#b4531a" text-anchor="middle">
<text x="586" y="326">VREF</text><text x="586" y="134">VREF</text><text x="586" y="193">VREF</text>
</g>

<!-- op-amp pin marks -->
<g font-size="12" fill="#1f2933" font-weight="600">
<text x="428" y="343">+</text><text x="428" y="311">&#8722;</text>
<text x="864" y="160">&#8722;</text><text x="864" y="195">+</text>
<text x="443" y="327" font-size="10.5" font-weight="400" fill="#5a6672">&#215;1</text>
</g>

<!-- value labels -->
<g font-size="11.5" fill="#1f2933">
<text x="26" y="124">3V3_A</text>
<text x="139" y="104" text-anchor="middle">47 R</text>
<text x="166" y="147" text-anchor="end">100 nF</text>
<text x="232" y="94">to V+ of all amplifiers</text>
<text x="232" y="180" text-anchor="end">R</text>
<text x="312" y="221">C</text>
<text x="232" y="300" text-anchor="end">100 k</text>
<text x="232" y="370" text-anchor="end">43 k</text>
<text x="320" y="400" text-anchor="middle">47 &#181;F tantalum</text>
<text x="298" y="347" font-size="12" font-weight="600">+</text>
<text x="694" y="216" text-anchor="middle">string pickup</text>
<text x="786" y="173" text-anchor="middle">1 k</text>
<text x="806" y="222" text-anchor="end">100 pF</text>
<text x="878" y="96" text-anchor="middle">15 k</text>
<text x="726" y="114" text-anchor="middle">2.2 k</text>
<text x="968" y="169">to DSP board</text>
<text x="968" y="184" font-size="10.5" fill="#5a6672">(tantalum coupling)</text>
</g>

<!-- section captions -->
<g font-size="10.5" fill="#8a8578" letter-spacing="0.6">
<text x="26" y="92">SUPPLY FILTER AND REFERENCE</text>
<text x="622" y="92">ONE OF FOUR IDENTICAL CHANNELS</text>
</g>

<!-- optional-block caption -->
<g font-size="11" fill="#6b7580">
<text x="344" y="163">Optional pre-filter — add only if</text>
<text x="344" y="179">the rail measurement demands it.</text>
<text x="344" y="195">A series R here shifts VREF, so the</text>
<text x="344" y="211">divider ratio must be re-trimmed.</text>
</g>

<!-- callouts -->
<rect x="622" y="284" width="470" height="86" rx="5" fill="#f2ece0" stroke="#d8cdb4" stroke-width="1.2"/>
<text x="638" y="305" font-size="12" font-weight="600" fill="#7a5a1e">VREF must reach BOTH nodes</text>
<text x="638" y="324" font-size="11.5" fill="#5a5344">Pickup return and gain-leg cold end. Then reference noise is</text>
<text x="638" y="341" font-size="11.5" fill="#5a5344">common-mode to the stage and reaches the output at &#215;1, against</text>
<text x="638" y="358" font-size="11.5" fill="#5a5344">&#215;7.82 for signal. Feed the leg alone and it arrives at &#215;6.8 instead.</text>

<rect x="622" y="384" width="470" height="86" rx="5" fill="#eceff2" stroke="#c6cdd4" stroke-width="1.2"/>
<text x="638" y="405" font-size="12" font-weight="600" fill="#3d4b57">The tap capacitor is the rail-rejection knob</text>
<text x="638" y="424" font-size="11.5" fill="#4a5560">Divider ratio is fixed at 0.30 by the required VREF, and the shunt</text>
<text x="638" y="441" font-size="11.5" fill="#4a5560">leg sets the impedance, so a series R barely moves the pole. Value</text>
<text x="638" y="458" font-size="11.5" fill="#4a5560">is what buys attenuation: 10 &#181;F &#8594; &#8722;56 dB, 100 &#181;F &#8594; &#8722;76 dB at 100 Hz.</text>

</g>
</svg>

## Notes

**The gain leg returns to VREF, not to ground.** That is what makes the stage
DC-coupled: no DC flows in the leg, so none flows in the feedback resistor, and the
output sits at VREF regardless of AC gain.

**A series resistor ahead of the divider does almost nothing for filtering.** The
Thevenin impedance is dominated by the shunt leg — 30.1 k as drawn — so adding 10 k
in the top leg moves the pole from 0.53 Hz to 0.52 Hz while shifting the reference by
a couple of hundred millivolts. Correcting an earlier assumption: the capacitor value
is the knob, not a pre-filter RC.

**Distribution.** VREF is a strip-wide net. Star it from the buffer output rather
than daisy-chaining, and do not hang a large bypass on that output — it works against
stability into the resistive load the four gain legs present.
