# kicad-tools

Two tools for the KiCad → JLCPCB workflow, usable on any KiCad project.

- **Check project** — read-only. Schematic vs board (values, footprints, BOM and
  position flags; any LCSC number left in the schematic is an error, and one that
  disagrees with the board is called out by part), the JLCPCB plugin's BOM and placement files
  (fresh, every row has a part number, BOM and CPL agree, both match the board's
  exclusion flags, through-hole parts listed), orphan sheets, reused sheets.
- **Sync schematic from board** — writes the JLCPCB tool's exclude-from-BOM and
  exclude-from-position flags into the schematic symbols, so "Update PCB from
  Schematic" carries them instead of resetting them. LCSC numbers stay out of the
  schematic: the JLCPCB tool keeps them in its own database and its output is the
  record (set `SYNC_LCSC = True` in `sync.py` to include them).

## Order checklist

`jlcpcb-order-checklist.md` — the generic to-do list for submitting a board: design-rule
check, file generation, parts-list check at upload, DFM report, placement preview.

## Why sync exists

The JLCPCB tool sets the exclusion flags on **footprints**. In KiCad 10 the symbol
owns both (`in_bom`, `in_pos_files`), and Update PCB from Schematic copies them from
the symbol onto the footprint — so every update undoes the tool's work. The tool's
own "Export to schematic" writes only LCSC numbers, by regular-expression edits on
the file text.

## How sync stays safe

- Walks the hierarchy from the root sheet, so orphan `.kicad_sch` files in the
  folder are never touched.
- Matches parts by the UUID path KiCad stores on each footprint, never by
  reference designator.
- A sheet placed more than once shares one symbol across its copies; if the copies
  disagree, that field is reported and skipped.
- Changes values in place — a sync shows up in git as exactly the lines it meant
  to change.
- Direction is board → schematic only.
- Refuses while KiCad holds a schematic lock file (the schematic editor is open),
  and the toolbar button refuses while the board has unsaved changes to the fields
  it reads. After writing, it re-reads everything and restores the originals if the
  result is not exactly what was planned.

Commit before syncing if you want an undo.

## Workflow

1. Make the board right in the JLCPCB tool (assignments, exclusions). Save.
2. Close the schematic editor. **Sync schematic** in the PCB editor toolbar.
3. Reopen the schematic, make any schematic changes, Update PCB from Schematic.
4. Assign and exclude anything new in the JLCPCB tool, regenerate, save.
5. **Check project.**

## Installing the toolbar buttons

Symlink `kicad_plugin/` into KiCad's user plugin folder, then in the PCB editor:
Tools → External Plugins → Refresh Plugins.

    ln -s ~/Documents/Developer/AudioDev/kicad-tools/kicad_plugin \
          ~/Documents/KiCad/10.0/scripting/plugins/kicad_tools_plugin

The plugin reloads `kicad_tools` on every click, so edits take effect without
restarting KiCad. The package uses only the Python standard library.

## Running outside KiCad

`run_check.py` and `run_sync.py` — set `PROJECT_DIR` (and `WRITE` for sync) at the
bottom and run from PyCharm.

## JLCPCB tool behaviours worth knowing (bouni/kicad-jlcpcb-tools, 2026.04.x)

- Its **part search never filters by footprint**. It pre-fills only an existing LCSC
  number; type the number (or put a package string like `CASE-A` in the Package box).
- **Changing a footprint clears that part's assignment** in its database.
- Its database is synced from the board each time it opens; with "LCSC priority"
  off, the database's number wins over the footprint's (the DEBUG "value supplied
  from the board will be ignored" lines).
- "Export to schematic" writes only LCSC numbers, by regex edits on the file text.
- It doesn't check package height: an A-case part on an I-case land pattern is
  accepted silently.

## KiCad 10 facts this relies on (verified on 10.0.5, macOS)

- Symbols carry `in_bom` and `in_pos_files`; Update PCB from Schematic copies both
  onto the footprint.
- KiCad writes `~<file>.lck` beside each document it has open, modified or not, and
  removes it on close. The lock holds the user and host name.
- Hand-installed plugins load from `~/Documents/KiCad/10.0/scripting/plugins` and do
  not appear in the Plugin and Content Manager. On this install there is no Tools →
  External Plugins menu; the buttons appear at the end of the top toolbar.
  `kicad_plugin/load.log` records each load (or the error).
