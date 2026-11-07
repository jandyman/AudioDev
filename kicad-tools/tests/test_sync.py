"""Synthetic-project tests for check and sync. Run with pytest from the repo root."""

import difflib
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kicad_tools.check import check
from kicad_tools.project import Project
from kicad_tools.sync import SyncPlan, apply

ROOT, SHEET_A, SHEET_B, SYM, ORPHAN = ("11111111-0000-0000-0000-000000000000", "aaaaaaaa-0000-0000-0000-000000000000",
                                       "bbbbbbbb-0000-0000-0000-000000000000", "cccccccc-0000-0000-0000-000000000000",
                                       "dddddddd-0000-0000-0000-000000000000")


def _prop(name, value):
  return (f'\t\t(property "{name}" "{value}"\n\t\t\t(at 0 0 0)\n\t\t\t(hide yes)\n'
          f'\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n')


def _sheet(uuid, page):
  return (f'\t(sheet\n\t\t(at 0 0)\n\t\t(size 10 10)\n\t\t(uuid "{uuid}")\n' + _prop("Sheetname", f"S{page}")
          + _prop("Sheetfile", "child.kicad_sch") + "\t)\n")


def _project(tmp: Path, refs=("R1", "R2"), excl=(True, False), lcsc=("C1", "C1"), reused=True):
  (tmp / "t.kicad_pro").write_text("{}")
  sheets = _sheet(SHEET_A, 2) + (_sheet(SHEET_B, 3) if reused else "")
  (tmp / "t.kicad_sch").write_text(f'(kicad_sch\n\t(version 20260306)\n\t(uuid "{ROOT}")\n{sheets})\n')
  paths = [SHEET_A, SHEET_B] if reused else [SHEET_A]
  inst = "".join(f'\t\t\t\t(path "/{ROOT}/{p}"\n\t\t\t\t\t(reference "{r}")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n'
                 for p, r in zip(paths, refs))
  sym = (f'\t(symbol\n\t\t(lib_id "Device:R")\n\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(in_pos_files yes)\n'
         f'\t\t(dnp no)\n\t\t(uuid "{SYM}")\n' + _prop("Reference", "R?") + _prop("Value", "10k")
         + _prop("Footprint", "R:R_0402") + f'\t\t(instances\n\t\t\t(project "t"\n{inst}\t\t\t)\n\t\t)\n\t)\n')
  (tmp / "child.kicad_sch").write_text(f'(kicad_sch\n\t(version 20260306)\n\t(uuid "{ORPHAN}")\n{sym})\n')
  fps = ""
  for p, r, e, c in list(zip(paths, refs, excl, lcsc)):
    attr = "smd exclude_from_bom exclude_from_pos_files" if e else "smd"
    fps += (f'\t(footprint "R:R_0402"\n\t\t(property "Reference" "{r}")\n\t\t(property "Value" "10k")\n'
            + (f'\t\t(property "LCSC" "{c}")\n' if c else "") + f'\t\t(path "/{p}/{SYM}")\n\t\t(attr {attr})\n\t)\n')
  (tmp / "t.kicad_pcb").write_text(f"(kicad_pcb\n\t(version 20260206)\n{fps})\n")


def test_reused_sheet_conflict_is_skipped(tmp_path):
  _project(tmp_path)
  plan = SyncPlan(Project(tmp_path))
  assert any("disagree on in_bom" in c for c in plan.conflicts)
  assert not [c for c in plan.changes if c.what in ("in_bom", "in_pos_files")]


def test_flags_and_lcsc_written_in_place(tmp_path):
  _project(tmp_path, refs=("R1",), excl=(True,), lcsc=("C25744",), reused=False)
  before = (tmp_path / "child.kicad_sch").read_text()
  ok, msg = apply(Project(tmp_path), lcsc=True)
  assert ok, msg
  after = (tmp_path / "child.kicad_sch").read_text()
  diff = [l for l in difflib.ndiff(before.splitlines(), after.splitlines()) if l[:2] in ("+ ", "- ")]
  assert [l for l in diff if l[0] == "-"] == ["- \t\t(in_bom yes)", "- \t\t(in_pos_files yes)"]
  assert "+ \t\t(in_bom no)" in diff and "+ \t\t(in_pos_files no)" in diff
  assert '(property "LCSC" "C25744"' in after                     # inserted, cloned from Footprint
  assert not SyncPlan(Project(tmp_path), lcsc=True).changes


def test_lcsc_left_alone_by_default(tmp_path):
  _project(tmp_path, refs=("R1",), excl=(False,), lcsc=("C25744",), reused=False)
  assert not SyncPlan(Project(tmp_path)).changes


def test_lock_refuses(tmp_path):
  _project(tmp_path, refs=("R1",), excl=(True,), reused=False)
  (tmp_path / "~t.kicad_sch.lck").write_text('{"hostname":"h","username":"u"}')
  ok, msg = apply(Project(tmp_path))
  assert not ok and "close the schematic editor" in msg


def test_board_without_lcsc_never_erases(tmp_path):
  _project(tmp_path, refs=("R1",), excl=(False,), lcsc=("",), reused=False)
  p = tmp_path / "child.kicad_sch"
  p.write_text(p.read_text().replace(_prop("Footprint", "R:R_0402"),
                                     _prop("Footprint", "R:R_0402") + _prop("LCSC", "C9")))
  plan = SyncPlan(Project(tmp_path), lcsc=True)
  assert not plan.changes and any("board has no LCSC" in n for n in plan.notes)


def test_orphan_sheet_reported(tmp_path):
  _project(tmp_path, refs=("R1",), excl=(False,), reused=False)
  (tmp_path / "old.kicad_sch").write_text(f'(kicad_sch\n\t(uuid "{ORPHAN}")\n)\n')
  assert any("old.kicad_sch" in i for i in check(tmp_path).info)
