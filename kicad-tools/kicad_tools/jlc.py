"""Read the BOM and placement (CPL) files written by the JLCPCB tools plugin."""

from __future__ import annotations
import csv
from pathlib import Path


def _rows(path: Path) -> list[dict]:
  with open(path, newline="", encoding="utf-8-sig") as f:
    return [{k.strip(): (v or "").strip() for k, v in r.items()} for r in csv.DictReader(f)]


class JlcOutput:
  def __init__(s, folder: Path, project_name: str):
    s.bom_path = folder / f"BOM-{project_name}.csv"
    s.cpl_path = folder / f"CPL-{project_name}.csv"
    s.present = s.bom_path.exists() and s.cpl_path.exists()
    s.bom: dict[str, dict] = {}   # ref -> row
    s.cpl: dict[str, dict] = {}
    if not s.present: return
    for r in _rows(s.bom_path):
      for ref in r.get("Designator", "").split(","):
        if ref.strip(): s.bom[ref.strip()] = r
    for r in _rows(s.cpl_path):
      if r.get("Designator"): s.cpl[r["Designator"]] = r

  @property
  def mtime(s) -> float:
    return min(s.bom_path.stat().st_mtime, s.cpl_path.stat().st_mtime)
