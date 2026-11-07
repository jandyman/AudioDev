"""
Read-only checks on a KiCad project and its JLCPCB output.

Three groups:
  schematic vs board   values, footprints, LCSC numbers and the BOM / position
                       flags agree — anything that differs is what the next
                       "Update PCB from Schematic" would overwrite
  JLCPCB output        fresh, every BOM row has a part number, BOM and CPL list the
                       same parts, and both match the board's exclusion flags
  housekeeping         orphan sheets in the folder, sheets placed more than once
"""

from __future__ import annotations
from .jlc import JlcOutput
from .project import Project
from .sync import SyncPlan


class Report:
  def __init__(s): s.errors, s.warnings, s.info = [], [], []

  def text(s) -> str:
    out = []
    for title, items, mark in (("Errors", s.errors, "x"), ("Warnings", s.warnings, "!"), ("Info", s.info, "-")):
      if items: out.append(f"{title} ({len(items)})"); out += [f"  {mark} {i}" for i in items]
    return "\n".join(out) if out else "All checks pass."

  @property
  def ok(s): return not s.errors


def check(folder) -> Report:
  r = Report(); prj = Project(folder)
  r.errors += prj.problems
  _sch_vs_board(prj, r)
  _jlc(prj, r)
  _housekeeping(prj, r)
  return r


def _sch_vs_board(prj: Project, r: Report):
  for fp, p in prj.pairs():
    if p is None: r.errors.append(f"{fp.ref}: on the board but not in the schematic"); continue
    if fp is None:
      if not p.footprint:
        r.errors.append(f"{p.ref}: no footprint assigned in the schematic, so it cannot reach the board")
      else:
        r.warnings.append(f"{p.ref}: in the schematic but not on the board yet (Update PCB from Schematic)")
      continue
    if (p.value or "") != (fp.value or ""):
      r.errors.append(f"{fp.ref}: value differs — schematic {p.value!r}, board {fp.value!r}")
    if p.footprint and p.footprint != fp.lib_id:
      r.errors.append(f"{fp.ref}: footprint differs — schematic {p.footprint}, board {fp.lib_id}")
  plan = SyncPlan(prj)
  if plan.changes:
    r.warnings.append("schematic is behind the board on fields the JLCPCB tool manages — "
                      "run sync before the next Update PCB from Schematic:\n" + plan.describe())
  r.warnings += plan.conflicts
  r.info += plan.notes


def _jlc(prj: Project, r: Report):
  out = JlcOutput(prj.jlc_dir, prj.name)
  if not out.present: r.info.append("no JLCPCB output found — skipped those checks"); return
  if out.mtime < prj.board_path.stat().st_mtime:
    r.warnings.append("JLCPCB output is older than the saved board — regenerate before ordering")
  fps = {f.ref: f for f in prj.footprints}
  for ref, row in sorted(out.bom.items()):
    if not row.get("LCSC"): r.errors.append(f"{ref}: in the BOM with no LCSC number")
    fp = fps.get(ref)
    if fp is None: r.errors.append(f"{ref}: in the BOM but not on the board"); continue
    if fp.lcsc and row.get("LCSC") and fp.lcsc != row["LCSC"]:
      r.errors.append(f"{ref}: BOM says {row['LCSC']}, board says {fp.lcsc}")
  bom, cpl = set(out.bom), set(out.cpl)
  if bom - cpl: r.errors.append("in the BOM but not the placement file: " + ", ".join(sorted(bom - cpl)))
  if cpl - bom: r.errors.append("in the placement file but not the BOM: " + ", ".join(sorted(cpl - bom)))
  want_bom = {f.ref for f in prj.footprints if not (f.bom_excluded or f.dnp)}
  want_cpl = {f.ref for f in prj.footprints if not (f.pos_excluded or f.dnp)}
  if bom != want_bom:
    r.warnings.append("BOM does not match the board's exclude-from-BOM flags (stale output?) — "
                      + _diff(bom, want_bom))
  if cpl != want_cpl:
    r.warnings.append("placement file does not match the board's exclude-from-position flags — "
                      + _diff(cpl, want_cpl))
  tht = sorted(ref for ref in bom if ref in fps and fps[ref].through_hole)
  if tht: r.info.append("through-hole parts in the BOM (confirm intended): " + ", ".join(tht))
  r.info.append(f"JLCPCB output: {len(bom)} parts in the BOM, {len(cpl)} in the placement file")


def _diff(have: set, want: set) -> str:
  parts = []
  if have - want: parts.append("extra: " + ", ".join(sorted(have - want)))
  if want - have: parts.append("missing: " + ", ".join(sorted(want - have)))
  return "; ".join(parts)


def _housekeeping(prj: Project, r: Report):
  used = set(prj.files)
  orphans = sorted(p.name for p in prj.folder.glob("*.kicad_sch") if p.resolve() not in used)
  if orphans: r.info.append("schematic files not in the hierarchy (ignored): " + ", ".join(orphans))
  for f in prj.reused_files():
    r.info.append(f"{f.path.name} is placed {len(f.instances)} times; BOM flags and LCSC are shared by all copies")
