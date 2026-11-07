# DC-coupling conversion — decisions and status

Opened 2026-08-26, updated 2026-11-07. Cross-thread record for a change that started as a challenge to
one sentence and worked through the whole analog chain. **This file holds the
decisions and the status; the reasoning lives in the board documents it points
to.** Read it before touching any analog section — the change reached different
documents on different dates, one claim that blocked an option was false, and the
direction of the reference was reversed partway through.

---

## 1. Where it came from

The superseded per-string stage returned its lower gain leg to ground through a
22 µF Class II capacitor, waved through as a called-out exception to an otherwise
strict Class I rule because the voltage across it in band is only a few
millivolts.

**Gemini disputed the assertion that it was essentially not a signal-path
capacitor, and the dispute held.** It carries the whole gain-setting current, so
its capacitance *is* the network's low corner, and it sits with about a volt
across it — the condition that collapses a high-K dielectric. And piezoelectric
generation is a source, not a non-linearity, so it does not scale down with
signal; the front-end document had already used exactly that arithmetic to reject
a *larger* Class II part in the same position. Holding both positions at once was
the error.

**The repair was not a better dielectric but no capacitor at all**, and returning
the leg to a buffered reference made the stage flat to DC. A defect in a
justification produced a topology improvement, and the same reasoning has since
propagated to every large capacitor in the system. Full argument:
`analog-front-end.md` §6.1.

---

## 2. Decisions

| # | Decision | Where the reasoning lives |
|---|---|---|
| 1 | Every stage in both instruments is **DC-coupled and rests on a common reference, VG**. The only signal-path capacitor left is at the analog instrument's output jack | `analog-front-end.md` §6 |
| 2 | **Class II ceramic banned board-wide** outside supply bypasses | `preamp-board.md` §9 |
| 3 | Where a stage needs gain it takes the **inverting** form — an inverting stage touches VG only at its plus input, a non-inverting gain stage returns its whole feedback current there | `cavity-preamp-board.md` §3.2 |
| 4 | **The converter inputs go DC-coupled differential**, cold pins on the reference. Deletes 24 parts from the codec section. **Committed on spin 1, 2026-11-06, as an accepted risk** — no retrofit footprints; one bench check open (§3); fallback is grounding the cold pins by rework | `adc-netlist.md` §2.1 |
| 5 | **The reference is generated at the far end** — converter board or cavity board — and re-buffered on each pickup board. The generating divider was later omitted from the pickup boards rather than kept as a DNP footprint; standalone bench work uses the test board | `preamp-board.md` §3.1, §8 |
| 6 | **Converter-instrument reference: 1.336 V as built**, from 100 kΩ / 68 kΩ on `3V3_A`, filtered by 10 µF tantalum (the 71.5 kΩ / 1.375 V pair was never fitted) | `adc-netlist.md` §2.1 |
| 7 | **Not from `VREF`** — the differential connection already rejects the rail path, two converters means two bandgaps, VREF only exists after `CODEC_SHDNZ` is driven (reintroducing the sequencing dependency that retired MICBIAS), and it has no output-drive specification | `adc-netlist.md` §2.1 |
| 8 | **Cavity board: true summing amplifier at unity per input**, trimmers as series rheostats. The gain of eleven and the gain of five both had the passive network's 4:1 attenuation built in | `cavity-preamp-board.md` §2, §4 |
| 9 | **Reference network at the pickup board: 1 kΩ + 100 pF fitted, bulk capacitor DNP.** Flat is the default; filtering swaps exact cancellation of generated-node noise for rejection of conductor pickup, and which is bigger is a bench question | `preamp-board.md` §8 |
| 10 | **100 Ω in series with each cable's reference conductor**, at the converter-board buffer's output, cable branch only — never in the cold-pin feed (2026-11-07) | `adc-netlist.md` §2.1 |
| 11 | **Converter channel gain ≈9–12 dB.** Not needed for level; worth up to ≈2 dB of noise because the converter's 0 dB input noise ≈ the preamp's. Plan headroom against the single-ended full scale; gain costs no headroom below 6 dB (2026-11-07) | `adc-netlist.md` §2.1 |

**The channel-count claim that blocked all of this was false.** The ADC5140 has
four INxP/INxM *pairs* and records four analog channels whether configured
differential or single-ended (SBAS892A §8.3.3); the eight-per-device figure
applies only to digital PDM microphones. Corrected in both project notes and
`reference-architecture.md`.

**Why the direction reversed.** The analog board blends two pickups into one
output, so its chain has exactly one reference node; two independently generated
references differ by divider tolerance and a blend control puts that across a
wiper. The pickup boards are identical in both instruments, so the instrument with
the requirement sets the direction. What reversing costs is inter-string crosstalk
of −108 dB with the local re-buffer, or −93 dB without it — both below the front
end's own noise floor. **That cancellation argument was real but far weaker than I
first presented it, and should not have been weighed against a functional
requirement.**

---

## 3. Open

| What | Note |
|---|---|
| ~~Rework the string preamp schematic and simulate~~ | Done — pickup preamps built and working |
| **Converter DC-coupled common-mode window** | No longer blocking — decision 4 is committed. Bench test on an evaluation module: both pins at 1.34 V, offset and clip level, then THD with signal on the hot pin alone at nominal and attack levels (one-sided drive swings the common-mode by half the signal). Also try single-ended input mode with the cold pin on the reference. What the converter does with DC input is collected in `adc-netlist.md` §2.1 |
| **Cavity board reference ratio** | Mid-rail gives the best swing but the common-mode ceiling binds at end of discharge on the three follower stages — buffer, Sallen-Key, output buffer. Either a ratio of ≈0.45, or convert those to inverting. The filter is a Sallen-Key that simulates; `Filter Doc.md` draws a multiple-feedback circuit and is **stale** |
| **Bulk capacitor on the reference network** | Populate only if bench work shows conductor pickup beating generated-node noise, or if the charger measurement on the analog instrument calls for it |

---

## 4. Why the documents diverged, and the guard

The reference-architecture decision was taken in the simulation thread on
2026-08-22 and recorded next to the schematic. The `documentation/` set — where
`CLAUDE.md` sends a new session — was last touched 18–19 August and was never
told. For four days the authoritative design document specified a capacitor that
had been deliberately removed and contained an instruction not to do the thing
that had been done. Neither new document was listed in any "Where the rest lives"
table, so nothing pointed from the stale set to the current one. Those tables now
list both.

⚠ **The same failure recurred inside this conversion, twice.** `Filter Doc.md`
describes a topology the schematic does not use, and a misread of the trimmer
arrangement produced two confident conclusions that had to be withdrawn — that the
trimmers were the dominant VG load, and that the reference buffer could not be the
low-power part. **Check the schematic, not the prose, before building an argument
on a topology.** And price both sides of a trade before calling one of them a
mistake.
