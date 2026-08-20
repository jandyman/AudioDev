# Resonance emulator — LTspice package

Simulation files for the gyrator-based resonant peak on the cavity preamp
board. Design document: `resonance-emulator.md`.

## Files

| File | Purpose |
|---|---|
| `gyrator_z.cir` | **Run this first.** Port impedance of the gyrator alone |
| `resonance.cir` | Full stage — netlist form |
| `resonance.asc` | Full stage — schematic form, identical circuit |
| `gyrator.lib` | Parametrised opamp macromodel, TLV9001 / TLV9004 / OPA376 wrappers |
| `z*.asy` | Local symbols, so the schematic resolves without depending on your LTspice install |

Keep everything in one folder. Open the `.cir` files with **File > Open**
(set the filter to "All Files" if they don't appear) and run them directly —
LTspice runs a plain netlist without needing a schematic.

## Run order

**1. `gyrator_z.cir` — does the port behave as an inductor?**

Plot `V(PA)`. It is numerically the port impedance in ohms, because the probe
is a 1 A current source.

- Magnitude should rise at +6 dB/octave through the audio band, flattening to
  R1‖R2 above.
- Phase should sit at 70–80° near 2 kHz. It will not reach 90°, and the
  shortfall is exactly the Q: **Q = tan(phase)**. 74° means Q = 3.5.
- Add a trace with `Im(V(PA))/(2*pi*frequency)` to read the equivalent
  inductance directly. It should sit flat at R1·R2·Cg and droop where the
  amplifier runs out of loop gain — that droop is the real upper limit.

If the phase never gets above about 45°, the loss resistance is swamping the
inductance and no amount of tuning downstream will help. That failure mode is
described in `resonance-emulator.md` §2.3.

**2. `resonance.cir` or `resonance.asc` — the stage.**

Plot `V(OUT)/V(IN)` in dB. Uncomment one `.step` at a time; LTspice runs the
cross product of multiple stepped parameters and the plot becomes unreadable.

## Expected results

| Setting | Result |
|---|---|
| R2 = 47k (frequency trimmer, one end) | f₀ ≈ 3.11 kHz |
| R2 = 147k (mid) | f₀ ≈ 1.76 kHz, L = 1.21 H, Q ≈ 3.9 |
| R2 = 247k (other end) | f₀ ≈ 1.36 kHz |
| Rb = 2.2k (boost trimmer, max) | peak ≈ +8.9 dB |
| Rb = 22.2k (min) | peak ≈ +2.9 dB |
| Passband | +0.09 dB — unity for practical purposes |
| Tone fully down | f₀ falls by √(Cs/(Cs+Ct)) = 0.486, about an octave |

Q should barely move as the frequency trimmer sweeps — that independence is the
reason for choosing this topology over a two-pole active filter, and it is worth
confirming rather than assuming.

## What the simulation is actually for

Not risk: nothing here is marginal. The point is **trimmer taper**. Peak height
goes as the reciprocal of the branch resistance, so the boost control's law is
compressed at the top of its range. Sweep it, see where the useful territory
lands, and adjust the fixed series resistors so both controls spend most of
their travel somewhere you would actually set them. That is quicker to see than
to calculate.

Also worth checking: `V(GO)`, the gyrator amplifier's output. It carries the
largest internal swing on the board — larger than the port voltage by the
integrator's gain — and it is the node most likely to clip before anything in
the main signal path does.

## Swapping in the vendor model

The macromodel is a behavioural stand-in with the right GBW, open-loop gain,
second pole, output clamp and noise. For this circuit only GBW, AOL and the
clamp matter.

To use TI's own model instead: download the OPA376 or TLV900x SPICE model from
ti.com, put the `.lib` alongside these files, add `.inc <filename>` and change
the `X` device's value to whatever TI names the subcircuit. Check the pin order
— TI models are usually `(IN+ IN− V+ V− OUT)`, which matches the symbol here,
but confirm rather than assume.
