"""
Copy the board's BOM / position flags and LCSC numbers into the schematic, for
running from PyCharm. Same as the "Sync schematic" button in the PCB editor.

Refuses while the schematic is open in KiCad. Save the board first — this reads
the saved file. With WRITE = False it only prints what it would change.
"""

from pathlib import Path
from kicad_tools.project import Project
from kicad_tools.sync import SyncPlan, apply, _extras


def main(project_dir, write):
  prj = Project(project_dir)
  plan = SyncPlan(prj)
  print(f"Project: {prj.name}\n\nPlanned changes:\n{plan.describe()}\n{_extras(plan)}")
  if not write or not plan.changes: return
  ok, msg = apply(Project(project_dir))
  print("\n" + msg)


if __name__ == "__main__":
  PROJECT_DIR = Path(__file__).parent.parent / "Onboard DSP Board HW" / "Main Board"
  WRITE = False
  main(PROJECT_DIR, WRITE)
