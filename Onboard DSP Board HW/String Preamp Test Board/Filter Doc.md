<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 380" width="100%" height="100%" style="background-color: #1e1e2e; font-family: system-ui, -apple-system, sans-serif;">
  <style>
    .line { stroke: #cdd6f4; stroke-width: 2.5; fill: none; stroke-linecap: round; stroke-linejoin: round; }
    .wire-green { stroke: #a6e3a1; stroke-width: 2.5; fill: none; stroke-linecap: round; }
    .text { fill: #cdd6f4; font-size: 15px; text-anchor: middle; }
    .label { fill: #89b4fa; font-size: 16px; font-weight: bold; text-anchor: middle; }
    .component { stroke: #f38ba8; stroke-width: 2.5; fill: #1e1e2e; }
    .node { fill: #f9e2af; }
    .opamp { stroke: #cba6f7; stroke-width: 2.5; fill: #181825; }
    .opamp-text { fill: #cba6f7; font-size: 20px; font-weight: bold; }
  </style>

  <!-- Input Pin -->
  <text x="40" y="205" class="text" text-anchor="end">In</text>
  <line x1="45" y1="200" x2="80" y2="200" class="line" />

  <!-- R1 (Input Resistor) -->
  <path d="M 80 200 L 90 200 L 95 190 L 105 210 L 115 190 L 125 210 L 135 190 L 145 210 L 150 200 L 160 200" class="component" />
  <text x="120" y="175" class="label">R1</text>

  <!-- Node 1 (Summing Node) -->
  <circle cx="210" cy="200" r="4" class="node" />

  <line x1="160" y1="200" x2="210" y2="200" class="line" />

  <!-- C2 to GND -->
  <line x1="210" y1="200" x2="210" y2="270" class="line" />
  <line x1="195" y1="270" x2="225" y2="270" class="component" />
  <line x1="195" y1="278" x2="225" y2="278" class="component" />
  <line x1="210" y1="278" x2="210" y2="295" class="line" />
  <!-- GND C2 -->
  <line x1="195" y1="295" x2="225" y2="295" class="line" />
  <line x1="202" y1="301" x2="218" y2="301" class="line" />
  <line x1="207" y1="307" x2="213" y2="307" class="line" />
  <text x="245" y="279" class="label">C2</text>

  <!-- Up to R2 / C1 Branching -->
  <line x1="210" y1="200" x2="210" y2="70" class="line" />
  <circle cx="210" cy="120" r="4" class="node" />

  <!-- R2 (Top Loop: Resistor Feedback) -->
  <line x1="210" y1="120" x2="250" y2="120" class="line" />
  <path d="M 250 120 L 260 120 L 265 110 L 275 130 L 285 110 L 295 130 L 305 110 L 315 130 L 320 120 L 330 120" class="component" />
  <line x1="330" y1="120" x2="610" y2="120" class="wire-green" />
  <text x="290" y="95" class="label">R2 (DC Feedback)</text>

  <!-- C1 (Top Loop: AC Feedback) -->
  <line x1="210" y1="70" x2="380" y2="70" class="line" />
  <line x1="380" y1="55" x2="380" y2="85" class="component" />
  <line x1="388" y1="55" x2="388" y2="85" class="component" />
  <line x1="388" y1="70" x2="610" y2="70" class="wire-green" />
  <text x="384" y="45" class="label">C1 (AC Feedback)</text>

  <!-- R3 (Series into Inverting Pin) -->
  <line x1="210" y1="200" x2="270" y2="200" class="line" />
  <path d="M 270 200 L 280 200 L 285 190 L 295 210 L 305 190 L 315 210 L 325 190 L 335 210 L 340 200 L 350 200" class="component" />
  <text x="305" y="175" class="label">R3</text>

  <!-- Op-Amp Triangle -->
  <polygon points="430,160 430,280 530,220" class="opamp" />
  <text x="445" y="195" class="opamp-text">-</text>
  <text x="445" y="255" class="opamp-text">+</text>

  <!-- Connections to Op-Amp -->
  <line x1="350" y1="200" x2="430" y2="200" class="line" /> <!-- Inverting input -->
  <line x1="380" y1="250" x2="430" y2="250" class="line" /> <!-- Non-inverting input -->

  <!-- Non-inverting GND -->
  <line x1="380" y1="250" x2="380" y2="295" class="line" />
  <line x1="365" y1="295" x2="395" y2="295" class="line" />
  <line x1="372" y1="301" x2="388" y2="301" class="line" />
  <line x1="377" y1="307" x2="383" y2="307" class="line" />

  <!-- Output Pin & Feedback Tie Point -->
  <line x1="530" y1="220" x2="610" y2="220" class="line" />
  <circle cx="610" cy="220" r="4" class="node" />
  <line x1="610" y1="220" x2="660" y2="220" class="line" />
  <text x="670" y="225" class="text" text-anchor="start">Out</text>

  <!-- Feedback Line Closing down to Output -->
  <line x1="610" y1="70" x2="610" y2="220" class="wire-green" />
</svg>

# MFB Low-Pass Filter Topology & Synthesis Guide

## Theoretical Background

The **Multiple Feedback (MFB)** low-pass filter is an active second-order, inverting topology. Unlike Sallen-Key designs—where non-inverting passband gain directly impacts loop damping and risks instability at higher gains—the MFB topology uses a dedicated inverting configuration. This isolates the feedback loops, allowing independent selection of passband gain ($A_0$), quality factor ($Q$), and cutoff frequency ($f_c$).

---

## Component Functional Roles

* **$R_1$ (Input Resistor):** Controls input impedance and sets passband gain magnitude in conjunction with $R_2$.
* **$R_2$ (DC Feedback Resistor):** Connects the op-amp output back to the central summing node, establishing DC stability and setting passband gain ($A_0 = R_2 / R_1$).
* **$C_1$ (AC Feedback Capacitor):** Connects the op-amp output back to the central summing node, providing high-frequency feedback for the 2nd-order roll-off.
* **$C_2$ (Shunt Capacitor):** Connects the central summing node to ground, filtering high-frequency noise entering the stage.
* **$R_3$ (Inverting Input Resistor):** Feeds the combined node voltage into the op-amp's inverting input ($-$) and acts as a secondary lever for $Q$ and $f_c$.

---

## Capacitor Ratio Constraint ($C_1 / C_2$)

When solving the physical network equations for real resistor values, the quadratic equation for $R_2$ yields a non-negative discriminant only when the ratio between $C_1$ and $C_2$ satisfies the following fundamental inequality:

$$\frac{C_1}{C_2} \ge 4 \cdot Q^2 \cdot (1 + A_0)$$

If $C_1 / C_2$ falls below this threshold, the mathematical solver results in imaginary resistor values, meaning no physical circuit can realize the target parameters.

### Practical Guidelines
1. **Rule of Thumb:** $C_1$ must always be significantly larger than $C_2$.
2. **Impact of Gain ($A_0$):** Higher passband gain requires a larger capacitor ratio.
3. **Impact of Resonance ($Q$):** Because $Q$ is squared, targeted resonant peaks ($Q > 1$) rapidly expand the required capacitor ratio.

### Quick Reference Selection Table

| Target $Q$ | Target Gain ($A_0$) | Minimum Ratio ($\frac{C_1}{C_2}$) | Practical Standard Pair Example |
| :--- | :--- | :--- | :--- |
| **0.707** (Butterworth) | 1.0 (0 dB) | $4 \times (0.707)^2 \times 2 = \mathbf{4.0}$ | $C_1 = 47\text{ nF}$, $C_2 = 10\text{ nF}$ |
| **0.707** (Butterworth) | 3.0 (9.5 dB) | $4 \times (0.707)^2 \times 4 = \mathbf{8.0}$ | $C_1 = 100\text{ nF}$, $C_2 = 10\text{ nF}$ |
| **1.200** (Mild Peak) | 2.0 (6.0 dB) | $4 \times (1.2)^2 \times 3 = \mathbf{17.28}$ | $C_1 = 100\text{ nF}$, $C_2 = 4.7\text{ nF}$ |
| **2.000** (High Peak) | 2.0 (6.0 dB) | $4 \times (2.0)^2 \times 3 = \mathbf{48.0}$ | $C_1 = 220\text{ nF}$, $C_2 = 4.7\text{ nF}$ |

---

## Synthesis Procedure

1. Pick a standard off-the-shelf value for $C_2$ (typically between $1\text{ nF}$ and $10\text{ nF}$).
2. Determine the minimum required value for $C_1$:
   $$C_{1,\text{min}} = C_2 \cdot 4 Q^2 (1 + A_0)$$
3. Select an off-the-shelf standard value for $C_1$ that exceeds $C_{1,\text{min}}$ by 15–30%.
4. Solve for exact resistor values:
   $$k = 2 \pi f_c C_2$$
   $$R_2 = \frac{\left(\frac{C_1}{C_2}\right) - \sqrt{\left(\frac{C_1}{C_2}\right)^2 - 4 Q^2 (1 + A_0) \left(\frac{C_1}{C_2}\right)}}{2 Q k (1 + A_0)}$$
   $$R_1 = \frac{R_2}{A_0}$$
   $$R_3 = \frac{1}{k^2 C_1 R_2}$$
5. Snap calculated $R_1$, $R_2$, and $R_3$ values to standard 1% E96 resistors.

