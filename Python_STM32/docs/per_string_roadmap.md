# Per-String Bass — Program Roadmap

Decision (2026-07-05): take the mono pitch-shifter work as proof of concept
and go for the full per-string onboard instrument — divided pickup, in-body
STM32 DSP, eventually wireless control. Bass-first deliberately: the hard
knowledge in this repo (low-E ripple-vs-damp, 2H-dominant notes, residue
bracket) is bass-specific and is the comparative advantage; guitar (Nu
capsules, 12 ch) generalizes later in principle. This is not a business —
"all the marbles" means the finished instrument, with market gear (C4) as
the baseline to beat. A working bass solution is also the strongest possible
opening for a Cycfi conversation, if that ever happens.

Architecture decisions carried in from design discussions (see
`projects/pitch_shifter/attack_detector_lab.md` and memory notes):

- No analog panning — digitize every coil (2 pickups × 4 strings = 8 ch)
  via low-power TDM ADCs; pickup pan = per-string multiply in DSP.
- Front end lives in the pickup rout, not the control cavity: a sliver
  board per pickup ("the pickup outputs TDM"); only TDM + power cross the
  body. Open bench question: low-Z coils driving ADC PGA inputs directly,
  with no op-amp buffers at all (qualify noise + loading first).
- Everything level-relative; no absolute thresholds (hard design rule).

## Phases — ordered by risk retirement

Each phase has an exit criterion; later phases assume earlier evidence.

### P0 — Leverage proof (no new hardware)

Divided pickup with buffered outputs (Roland GK-3B class, used market) into
the existing native pipeline, one string at a time. Record a per-string test
corpus (the per-string equivalents of the troublesome bass files).
**Exit:** measured answer to "how much of the trigger/gate/residue problem
list evaporates with per-string input?" — this evidence sizes everything
downstream.

### P1 — DSP budget ground truth

The mono STM32 port (already Python_STM32's declared next step) + the DWT
cycle profiler: per-voice cost at ship -O level, ×4 extrapolation, measured
not estimated. **Exit:** a real headroom number for the H750.
**Contingency:** per-string voices share nothing but control — sharding
across 2+ MCUs is an architecture-compatible fallback (cost/area, not
feasibility). A newer part may also emerge; decide on measurements only.

### P2 — Front-end qualification (parallel with P1)

Bench: one low-Z coil → TDM ADC eval board (TLV320ADC5140 class — verify
part choice against current availability/power). Measure EIN at required
PGA gain vs coil thermal noise, and loading/frequency-response interaction.
**Exit:** go/no-go on bufferless direct drive; rout-board schematic concept
(with op-amp fallback sized if no-go).

### P3 — Playable prototype (the intermediate rewarding result)

Donor bass (adapt existing or build — open decision) with divided pickup +
rout ADC boards; DSP on a dev board in a **tethered belt box**; hardware
knobs + RTT for control and tuning. No custom PCB, no battery, no cavity
fit, no BT — full musical payoff with the three highest-effort items
deferred. **Exit:** playing per-string pitch shift + expander live; per-
string DSP tuned against the P0 corpus on the real instrument.

### P4 — Onboard integration

Custom PCB: H750 (or P1's verdict), ADCs, power/charging, lithium battery,
control-cavity fit. Integrates a *proven* system — every circuit block has
already worked in P2/P3 form. **Exit:** self-contained instrument, knob
control only.

### P5 — Control surface

BT module + app, reusing the Stage-1a blueprint (spec-driven UI, UUID
schema IDs, RTT→BT transport swap). **Exit:** the finished package.

## Open decisions

- Donor bass: adapt a current instrument vs. build one for the purpose.
- Pickup path: GK-class for P0 only; custom low-Z coils vs. Nu capsules for
  P3+ (user will NOT manufacture pickups — open-source coil spec or
  partnership are the endgames).
- P1 part verdict may reshape P4 (single H750 / dual MCU / newer part).

## Relationship to current work

Mono work continues and is load-bearing: the STM32 port IS P1; the
attack-detector rev-3 port and residue-anchor work carry straight into the
per-string voices (each string still needs trigger/gate/residue, on cleaner
input). Nothing already built is off the critical path.
