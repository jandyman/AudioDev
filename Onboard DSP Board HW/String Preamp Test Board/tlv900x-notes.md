# TLV900x simulation models — notes

Companion documentation for `tlv9004_sim.lib`. Nothing here is read by ngspice.

## Why this file exists separately

`tlv9004_sim.lib` is fed to ngspice through KiCad, which runs it in `ps lt a`
compatibility mode. Compatibility-mode preprocessing does not reliably ignore
punctuation inside comment lines — an unpaired apostrophe appears to open an
HSPICE-style expression that swallows everything after it, including `.subckt`
and `.include` lines. Keep the `.lib` free of `'`, `"`, `{`, `}`, `$`, `;` and
`#` even in comments. All prose belongs here instead.

## What the library provides

TI ships one macromodel per **amplifier**, not per package. `tlv9002.lib`
defines a single 5-port amplifier:

```spice
.subckt TLV9002 IN+ IN- VCC VEE OUT
```

plus sixteen internal helper subcircuits (`VOS_SRC_0`, `VCCS_LIM_ZO_0`,
`VNSE_0`, `OL_SENSE_0`, and so on). TLV9001 / TLV9002 / TLV9004 are that same
1-MHz amplifier in one-, two- and four-channel packages — they share a
datasheet — so every variant here is built from it rather than from a separate
vendor file.

| Subcircuit | Ports | Source |
|---|---|---|
| `TLV9002` | 5 | TI, via `.include tlv9002.lib` |
| `TLV9001` | 5 | wrapper, one instance of TLV9002 |
| `TLV9004` | 14 | wrapper, four instances of TLV9002 |

`TLV9001` is cosmetic — it makes the netlist read `TLV9001` where the board has
one. Selecting `TLV9002` for a TLV9001 symbol is electrically identical.

`TLV9004` is not optional. KiCad emits **one SPICE element per symbol
reference, not one per unit**, so a multi-unit symbol needs a model whose port
list covers every package pin. Fourteen symbol pins cannot map onto a 5-port
model. That is why the quad needs a wrapper and the single does not.

## Symbol field values

Set these in **Symbol Properties**, not the Simulation Model Editor (see the
warning below).

### U1 — quad, `Amplifier_Operational:Opamp_Quad`

```
Sim.Device   SUBCKT
Sim.Library  tlv9004_sim.lib
Sim.Name     TLV9004
Sim.Pins     1=OUT1 2=IN1- 3=IN1+ 4=VCC 5=IN2+ 6=IN2- 7=OUT2 8=OUT3 9=IN3- 10=IN3+ 11=VEE 12=IN4+ 13=IN4- 14=OUT4
```

`Sim.Pins` is one line, single spaces. Package pinout:

| pin | | pin | |
|---|---|---|---|
| 1 | OUT1 | 8 | OUT3 |
| 2 | IN1- | 9 | IN3- |
| 3 | IN1+ | 10 | IN3+ |
| 4 | VCC | 11 | VEE |
| 5 | IN2+ | 12 | IN4+ |
| 6 | IN2- | 13 | IN4- |
| 7 | OUT2 | 14 | OUT4 |

Symbol units A B C D correspond to channels 1 2 3 4.

### U2 — single, `Amplifier_Operational:TLV9001IDCK`

```
Sim.Device   SUBCKT
Sim.Library  tlv9004_sim.lib
Sim.Name     TLV9001
Sim.Pins     1=IN+ 2=VEE 3=IN- 4=OUT 5=VCC
```

## Three traps, all of which cost a night

**1. The Simulation Model Editor cannot configure a multi-unit symbol.**
Its Pin Assignments tab only ever lists the pins of the unit you opened it
from, and `Sim.Pins` is a single symbol-level property — so pressing OK
rewrites the whole field with just that unit's three pins, silently discarding
the other eleven. Cancel is safe; OK is not. Set `Sim.Pins` by hand in Symbol
Properties and do not reopen the model dialog on U1.
Upstream: [kicad#12372](https://gitlab.com/kicad/code/kicad/-/issues/12372),
[kicad#19253](https://gitlab.com/kicad/code/kicad/-/issues/19253).

**2. Never add TI's own TLV9001 or TLV9004 library alongside this one.**
Those files redefine the same sixteen helper subcircuits already in
`tlv9002.lib`. Two copies in one netlist corrupts ngspice's numparam tables:

```
Warning: redefinition of .subckt vos_src_0, ignored
Numparam warning: overwriting P,S or X line (linenum == 51)
Mismatch: 3 formal but 0 actual params.
Undefined parameter [ineg]
```

The redefinition warnings are harmless on their own — ngspice keeps the first
definition. The fatal part is numparam, which does *not* skip duplicates and
overwrites instead, leaving the surviving subcircuit bodies pointing at
clobbered parameter slots. One file per vendor family, with a wrapper per
package variant inside it.

**3. Point every symbol that needs this amplifier at this file.**
If one symbol references `tlv9002.lib` directly while another reaches it
through the `.include` here, `tlv9002.lib` is read twice and you get trap 2.
Each distinct `Sim.Library` path becomes one `.include` in the netlist.

## Diagnosing

`listing` in the ngspice console dumps the netlist as ngspice actually
assembled it, includes expanded. Scanning that for repeated `.subckt` lines
finds duplicate-definition problems in seconds, and it beats reading the
console log.

Noise you cannot fix and should ignore: `can't find the initialization file
spinit`, and the `ivlng.so` / `ivlng.vpi` dlopen failures. Those are KiCad's
macOS build shipping a broken Icarus Verilog bridge that this design does not
use. They appear on every run, including successful ones.
