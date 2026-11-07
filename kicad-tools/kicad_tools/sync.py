"""
Copy the board's exclude-from-BOM and exclude-from-position flags into the schematic.

The JLCPCB tool sets both on footprints, and "Update PCB from Schematic" overwrites
them from the symbols (KiCad 10 keeps both on the symbol). Writing them into the
symbols first makes the update carry them instead.

LCSC numbers are left out by default: the JLCPCB tool keeps its assignments in its
own database and its output is the record of them, so they do not need the
schematic. SYNC_LCSC = True adds them back (board -> schematic only; a board part
with no number never erases one from the schematic).

Edits are made in place, value by value, so nothing else in the file moves.
"""

from __future__ import annotations
from dataclasses import dataclass
from .project import Placed, Project, lcsc_property, _prop
from .sexpr import apply_edits, parse, quote

SYNC_LCSC = False


@dataclass
class Change:
  sch_path: object
  ref: str
  what: str          # "in_bom", "in_pos_files", "LCSC"
  old: str
  new: str
  edit: tuple        # (start, end, replacement)


def _flag_edit(p: Placed, key: str, want: bool):
  n = p.node.child(key)
  if n is None or n.atom(1) is None: return None
  a = n.atom(1); new = "yes" if want else "no"
  return None if a.text == new else (a.text, new, (a.start, a.end, new))


def _lcsc_edit(p: Placed, want: str):
  prop = lcsc_property(p.node)
  if prop is not None:
    a = prop.atom(2)
    if a.text == want: return None
    return (a.text, want, (a.start, a.end, quote(want)))
  # No LCSC field: clone the symbol's own hidden Footprint property, so the new
  # field carries exactly the formatting this KiCad version writes.
  fp = _prop(p.node, "Footprint")
  if fp is None: return None
  src = p.sch.text[fp.start:fp.end]
  name, val = fp.atom(1), fp.atom(2)
  clone = src[:name.start - fp.start] + quote("LCSC") + src[name.end - fp.start:val.start - fp.start] \
          + quote(want) + src[val.end - fp.start:]
  last = p.node.children("property")[-1]
  line_start = p.sch.text.rfind("\n", 0, fp.start) + 1
  indent = p.sch.text[line_start:fp.start]
  return ("", want, (last.end, last.end, "\n" + indent + clone))


class SyncPlan:
  def __init__(s, prj: Project, lcsc: bool = None):
    s.prj = prj; s.lcsc = SYNC_LCSC if lcsc is None else lcsc
    s.changes: list[Change] = []
    s.conflicts: list[str] = []
    s.notes: list[str] = []
    s._build()

  def _units(s, p: Placed) -> list[Placed]:
    """All units of the same part at the same place in the hierarchy."""
    base = p.board_path.rsplit("/", 1)[0]
    return [q for q in s.prj.placed
            if q.sch is p.sch and q.ref == p.ref and q.board_path.rsplit("/", 1)[0] == base]

  def _build(s):
    want: dict[tuple, dict] = {}    # (file, node.start) -> {field: (value, ref)}
    nodes: dict[tuple, Placed] = {}
    no_pos_flag = False
    for fp, p in s.prj.pairs():
      if fp is None or p is None: continue
      targets = {"in_bom": not fp.bom_excluded, "in_pos_files": not fp.pos_excluded}
      if s.lcsc and fp.lcsc: targets["LCSC"] = fp.lcsc
      elif s.lcsc and p.lcsc: s.notes.append(f"{fp.ref}: schematic has {p.lcsc}, board has no LCSC number — left as is")
      for u in s._units(p):
        k = (u.sch.path, u.node.start); nodes[k] = u
        for f, v in targets.items():
          if f == "LCSC" and u is not p: continue          # the field lives on one unit
          prev = want.setdefault(k, {}).get(f)
          if prev is not None and prev[0] != v:
            s.conflicts.append(f"{u.ref} in {u.sch.path.name}: sheet is placed more than once and the "
                               f"copies disagree on {f} ({prev[1]}: {prev[0]}, {fp.ref}: {v}) — skipped")
            want[k][f] = (None, fp.ref)
          elif prev is None:
            want[k][f] = (v, fp.ref)
    for k, fields in want.items():
      u = nodes[k]
      for f, (v, _) in fields.items():
        if v is None: continue
        if f == "LCSC": r = _lcsc_edit(u, v)
        else:
          if u.node.child(f) is None:
            if f == "in_pos_files": no_pos_flag = True
            continue
          r = _flag_edit(u, f, v)
        if r: s.changes.append(Change(u.sch.path, u.ref, f, r[0], r[1], r[2]))
    if no_pos_flag:
      s.notes.append("this KiCad version keeps no position-file flag on symbols; nothing to sync for it")

  def describe(s) -> str:
    out = []
    for c in sorted(s.changes, key=lambda c: (c.sch_path.name, c.ref, c.what)):
      out.append(f"  {c.sch_path.name}: {c.ref} {c.what}: {c.old or '(none)'} -> {c.new}")
    return "\n".join(out) if out else "  nothing to change"


def apply(prj: Project, lcsc: bool = None) -> tuple[bool, str]:
  """Write the plan. Returns (ok, message). Refuses while KiCad holds a schematic open."""
  locks = prj.locks()
  if locks:
    msg = ["The schematic is open in KiCad — close the schematic editor first."]
    for lck, who in locks:
      msg.append(f"  lock: {lck.name}  {who}")
    msg.append("If KiCad is not running, the lock is stale and can be deleted.")
    return False, "\n".join(msg)
  plan = SyncPlan(prj, lcsc)
  if not plan.changes: return True, "Schematic already matches the board.\n" + _extras(plan)
  by_file: dict = {}
  for c in plan.changes: by_file.setdefault(c.sch_path, []).append(c.edit)
  originals = {path: prj.files[path].text for path in by_file}
  for path, edits in by_file.items():
    new = apply_edits(originals[path], edits)
    parse(new)                                           # must still be well-formed
    path.write_text(new, encoding="utf-8")
  # Verify: re-read everything; the plan must now be empty and nothing else changed.
  try:
    again = SyncPlan(Project(prj.folder), lcsc)
    if again.changes:
      raise RuntimeError("after writing, the schematic still differs:\n" + again.describe())
  except Exception as e:
    for path, text in originals.items(): path.write_text(text, encoding="utf-8")
    return False, f"Verification failed, original files restored.\n{e}"
  return True, f"Wrote {len(plan.changes)} change(s):\n{plan.describe()}\n" + _extras(plan)


def _extras(plan: SyncPlan) -> str:
  out = [f"  ! {c}" for c in plan.conflicts] + [f"  - {n}" for n in plan.notes]
  return "\n".join(out)
