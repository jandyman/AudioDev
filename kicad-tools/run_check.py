"""
Read-only project check, for running from PyCharm. Writes nothing.

Same checks as the "Check project" button in the PCB editor. Set PROJECT_DIR at the
bottom to the folder holding the .kicad_pro.
"""

from pathlib import Path
from kicad_tools.check import check


def main(project_dir):
  r = check(project_dir)
  print(f"Project: {Path(project_dir).name}\n")
  print(r.text())


if __name__ == "__main__":
  PROJECT_DIR = Path(__file__).parent.parent / "Onboard DSP Board HW" / "Main Board"
  main(PROJECT_DIR)
