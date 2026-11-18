# JLCPCB order checklist

A generic to-do list for submitting any KiCad board to JLCPCB for fabrication and
assembly. Copy it, or work through it in place and reset the boxes afterwards.
Background on what the checks mean (rotation conventions, reading the DFM report,
silkscreen over pads) is in `jlcpcb-submission-notes.md` in the project docs.

Board-specific decisions that affect the order (what is populated, parts with a known
concern) belong in that board's own risk list, not here.

---

## 1. Before generating the files

- [ ] **Every polarised capacitor (tantalum, electrolytic) uses a polarised symbol and a
      polarised land pattern,** with the positive pad on the intended net.
- [ ] **Every do-not-populate decision is made** and flagged on the board. Each one
      changes the BOM.
- [ ] **Design-rule check: zero errors on Violations and zero on Unconnected Items;**
      schematic parity clean. Parity checks net assignments, not copper — a broken
      trace shows only under Unconnected Items. Rerun after every layout edit.
- [ ] **JLCPCB plugin: every surface-mount part has an LCSC number,** and every part
      JLCPCB should not fit (hand-soldered through-hole parts, unpopulated footprints)
      is excluded from both BOM and placement.
- [ ] **Commit to git** so the ordered state is recorded.

## 2. Generate and check the files

- [ ] **Regenerate gerbers, BOM and placement file** from the saved board, after the
      last layout change.
- [ ] **Check project shows no errors and no "older than the saved board" warning;**
      BOM and placement file list the same parts.
- [ ] **Vias tented** (if intended): the top mask gerber's aperture count equals the
      surface-mount plus through-hole pad count, with nothing left over for vias.
- [ ] **Silkscreen clipped from pads** (subtract soldermask from silkscreen at plot).

## 3. Upload — parts list reality check

- [ ] **Read every BOM line's description on the JLCPCB site** against value, package,
      dielectric and voltage rating — the LCSC number is what gets fitted, whatever the
      value field says.
  - [ ] Capacitors on a supply input that can be hot-plugged (charger, external power):
        voltage rating about twice the supply, since a ceramic input can ring toward
        double when a live source is connected.
  - [ ] Timing, filter and audio-path capacitors: C0G where the design calls for it.
  - [ ] Any capacitor whose value was changed recently: the LCSC number changed with it.
- [ ] **Stock for every line,** especially extended parts and any part reserved or
      consigned ahead of time — confirm it is available to this order.
- [ ] **No silent substitutions** — any part JLCPCB swapped or flagged.
- [ ] **Board options match the design:** layer count, thickness, copper weight,
      surface finish, mask colour, via treatment.

## 4. DFM report

- [ ] **Read each alert for the process it protects** before changing the layout.
      Via-to-pad alerts do not apply to tented vias; through-hole-to-SMD spacing
      applies only to through-hole parts JLCPCB actually solders.

## 5. Placement preview — rotation and polarity

Rotation depends on how LCSC stored each part, so the 3D preview is the only
authority. Judge by the pin-1 or polarity mark, not the outline. Fix rotations in the
plugin's rotation manager (not the placement file by hand), regenerate, re-upload and
re-check, as many passes as it takes.

- [ ] **List every asymmetric part from the BOM** before opening the preview: ICs,
      polarised capacitors, diodes and LEDs, connectors, crystals, modules.
- [ ] **Check each one's pin-1 or polarity mark** against the footprint. A rotated
      14-pin SOIC looks almost identical and puts the supply on the ground pin.
- [ ] **Modules with an antenna** face the intended board edge.

## 6. After ordering

- [ ] **Record what was ordered** in `jlcpcb-submission-notes.md`: the commit, any
      rotation corrections that differed from the plugin's database, any
      substitutions, and anything this checklist should carry next time.
- [ ] **Reset the boxes** in this file.
