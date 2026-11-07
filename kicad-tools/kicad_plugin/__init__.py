"""
PCB-editor toolbar buttons for kicad_tools: "Check project" and "Sync schematic".

Installed by symlinking this folder into KiCad's plugin folder. The real location
is resolved so the kicad_tools package next to it is importable.

Each load appends one line to load.log beside this file, so it is possible to tell
whether KiCad imported the plugin at all, and why registration failed if it did.
"""

import datetime
import os
import sys
import traceback

_here = os.path.dirname(os.path.realpath(__file__))
_repo = os.path.dirname(_here)
if _repo not in sys.path: sys.path.insert(0, _repo)


def _log(msg):
  try:
    with open(os.path.join(_here, "load.log"), "a", encoding="utf-8") as f:
      f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}  {msg}\n")
  except OSError:
    pass


try:
  import pcbnew  # noqa: F401  pylint: disable=import-error
except ImportError:
  pcbnew = None    # not running inside KiCad (tests, PyCharm)

if pcbnew is not None:
  try:
    from .plugin import CheckPlugin, SyncPlugin
    CheckPlugin().register()
    SyncPlugin().register()
    _log(f"registered (python {sys.version.split()[0]}, imported as {__name__})")
  except Exception:
    _log("FAILED\n" + traceback.format_exc())
    raise
