"""
Read a KiCad project: the board, the schematic hierarchy, and the link between them.

Parts are matched by the UUID path KiCad records on every footprint, never by
reference designator, so re-annotation cannot confuse the match. The schematic is
walked from the root sheet down through the sheets it actually instantiates, so
orphan .kicad_sch files sitting in the folder are never touched.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path
from .sexpr import Node, parse

LCSC_NAME = re.compile(r"lcsc|jlc", re.I)   # same rule as the JLCPCB plugin
LCSC_VALUE = re.compile(r"^C\d+$")


def _prop(node: Node, name: str) -> Node | None:
  for p in node.children("property"):
    if p.value(1) == name: return p
  return None


def lcsc_property(node: Node) -> Node | None:
  """First property whose name looks like an LCSC field (value may be empty)."""
  for p in node.children("property"):
    n = p.value(1) or ""
    if LCSC_NAME.match(n) and (LCSC_VALUE.match(p.value(2) or "") or not p.value(2)): return p
  return None


@dataclass
class Footprint:
  ref: str
  value: str
  lib_id: str
  path: str
  attrs: set
  lcsc: str

  @property
  def bom_excluded(s): return "exclude_from_bom" in s.attrs
  @property
  def pos_excluded(s): return "exclude_from_pos_files" in s.attrs
  @property
  def through_hole(s): return "through_hole" in s.attrs
  @property
  def dnp(s): return "dnp" in s.attrs


@dataclass
class SchFile:
  path: Path
  text: str
  root: Node
  instances: list = field(default_factory=list)   # sheet chains this file is placed at


@dataclass
class Placed:
  """One symbol as it appears at one place in the hierarchy."""
  sch: SchFile
  node: Node
  ref: str
  board_path: str

  @property
  def uuid(s): return s.node.child("uuid").value()
  @property
  def value(s):
    p = _prop(s.node, "Value"); v = p.value(2) if p else ""
    return "" if v == "~" else v
  @property
  def footprint(s): p = _prop(s.node, "Footprint"); return p.value(2) if p else ""
  def flag(s, key):
    n = s.node.child(key)
    return None if n is None else n.value() == "yes"
  @property
  def lcsc(s):
    p = lcsc_property(s.node); v = p.value(2) if p else ""
    return v if LCSC_VALUE.match(v or "") else ""


class Project:
  def __init__(s, folder):
    s.folder = Path(folder).expanduser().resolve()
    pros = sorted(s.folder.glob("*.kicad_pro"))
    if len(pros) != 1:
      raise RuntimeError(f"expected one .kicad_pro in {s.folder}, found {len(pros)}")
    s.name = pros[0].stem
    s.board_path = s.folder / f"{s.name}.kicad_pcb"
    s.root_sch_path = s.folder / f"{s.name}.kicad_sch"
    s.jlc_dir = s.folder / "jlcpcb" / "production_files"
    s.footprints = s._read_board()
    s.files: dict[Path, SchFile] = {}
    s.placed: list[Placed] = []
    s.problems: list[str] = []
    s._walk(s.root_sch_path, [], None)

  # ---------------------------------------------------------------- board
  def _read_board(s) -> list[Footprint]:
    root = parse(s.board_path.read_text(encoding="utf-8"))
    out = []
    for fp in root.children("footprint"):
      ref = _prop(fp, "Reference"); val = _prop(fp, "Value"); path = fp.child("path")
      if not ref or not path: continue
      attr = fp.child("attr")
      lp = lcsc_property(fp); lcsc = lp.value(2) if lp else ""
      v = val.value(2) if val else ""
      out.append(Footprint(ref.value(2), "" if v == "~" else v, fp.value(1), path.value(),
                           {a.text for a in attr.items[1:]} if attr else set(),
                           lcsc if LCSC_VALUE.match(lcsc or "") else ""))
    return out

  # ----------------------------------------------------------- schematic
  def _load(s, path: Path) -> SchFile:
    path = path.resolve()
    if path not in s.files:
      text = path.read_text(encoding="utf-8")
      s.files[path] = SchFile(path, text, parse(text))
    return s.files[path]

  def _walk(s, path: Path, chain: list[str], root_uuid: str | None):
    sch = s._load(path); sch.instances.append(list(chain))
    if root_uuid is None: root_uuid = sch.root.child("uuid").value()
    inst_path = "/" + "/".join([root_uuid] + chain)
    for sym in sch.root.children("symbol"):
      u = sym.child("uuid")
      if u is None: continue
      ref = ""
      inst = sym.child("instances")
      if inst:
        for pr in inst.children("project"):
          for p in pr.children("path"):
            if p.value() == inst_path and p.child("reference"): ref = p.child("reference").value()
      if not ref:
        rp = _prop(sym, "Reference"); ref = rp.value(2) if rp else ""
      if ref.startswith("#"): continue                        # power symbols, flags
      s.placed.append(Placed(sch, sym, ref, "/" + "/".join(chain + [u.value()])))
    for sh in sch.root.children("sheet"):
      f = _prop(sh, "Sheetfile"); u = sh.child("uuid")
      if not f or not u: continue
      child = (path.parent / f.value(2))
      if not child.exists():
        s.problems.append(f"sheet file missing: {child.name}"); continue
      s._walk(child, chain + [u.value()], root_uuid)

  # ------------------------------------------------------------- helpers
  def reused_files(s) -> list[SchFile]:
    return [f for f in s.files.values() if len(f.instances) > 1]

  def locks(s) -> list[tuple[Path, str]]:
    """Lock files KiCad holds on any schematic in the hierarchy."""
    out = []
    for f in s.files.values():
      lck = f.path.parent / f"~{f.path.name}.lck"
      if lck.exists():
        try: who = lck.read_text(encoding="utf-8").strip()
        except OSError: who = ""
        out.append((lck, who))
    return out

  def pairs(s):
    """(Footprint | None, Placed | None) for every part on either side."""
    by_path = {p.board_path: p for p in s.placed}
    base = lambda p: (p.sch.path, p.board_path.rsplit("/", 1)[0], p.ref)
    matched = set()
    for fp in s.footprints:
      p = by_path.get(fp.path)
      if p: matched.add(base(p))
      yield fp, p
    for p in s.placed:                 # other units of a matched part are not "missing"
      if base(p) not in matched and p.flag("on_board") is not False: yield None, p
