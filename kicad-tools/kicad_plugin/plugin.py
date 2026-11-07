"""The two action plugins. All real work happens in kicad_tools, which needs no KiCad."""

import importlib
import os
import traceback

import pcbnew  # pylint: disable=import-error
import wx      # pylint: disable=import-error

import kicad_tools.check, kicad_tools.project, kicad_tools.sync, kicad_tools.jlc, kicad_tools.sexpr

_HERE = os.path.dirname(os.path.realpath(__file__))
EXCLUDE_FROM_POS, EXCLUDE_FROM_BOM = 1 << 2, 1 << 3     # FOOTPRINT attribute bits


def _reload():
  """Pick up edits to kicad_tools without restarting KiCad."""
  for m in ("sexpr", "project", "jlc", "sync", "check"):
    importlib.reload(getattr(kicad_tools, m))


def _show(title: str, text: str, ask: str = None) -> bool:
  dlg = wx.Dialog(None, title=title, size=(820, 560), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
  box = wx.BoxSizer(wx.VERTICAL)
  tc = wx.TextCtrl(dlg, value=text, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
  tc.SetFont(wx.Font(11, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
  box.Add(tc, 1, wx.EXPAND | wx.ALL, 8)
  if ask: box.Add(wx.StaticText(dlg, label=ask), 0, wx.LEFT | wx.RIGHT, 8)
  box.Add(dlg.CreateButtonSizer(wx.OK | wx.CANCEL if ask else wx.OK), 0, wx.EXPAND | wx.ALL, 8)
  dlg.SetSizer(box)
  ok = dlg.ShowModal() == wx.ID_OK
  dlg.Destroy()
  return ok


def _project_dir():
  return os.path.dirname(pcbnew.GetBoard().GetFileName())


def _unsaved_board_changes(prj) -> list:
  """Compare the board in memory with the saved file on the fields sync reads."""
  saved = {f.ref: f for f in prj.footprints}
  diffs = []
  for fp in pcbnew.GetBoard().GetFootprints():
    ref = fp.GetReference()
    if ref not in saved: diffs.append(f"{ref}: not in the saved board"); continue
    f = saved[ref]; a = fp.GetAttributes()
    if bool(a & EXCLUDE_FROM_BOM) != f.bom_excluded: diffs.append(f"{ref}: exclude-from-BOM")
    if bool(a & EXCLUDE_FROM_POS) != f.pos_excluded: diffs.append(f"{ref}: exclude-from-position")
    lcsc = ""
    for fld in fp.GetFields():
      if kicad_tools.project.LCSC_NAME.match(fld.GetName()) and kicad_tools.project.LCSC_VALUE.match(fld.GetText()):
        lcsc = fld.GetText(); break
    if lcsc != f.lcsc: diffs.append(f"{ref}: LCSC")
  return diffs


class CheckPlugin(pcbnew.ActionPlugin):
  def defaults(s):
    s.name = "Check project (schematic, board, JLCPCB output)"
    s.category = "kicad_tools"
    s.description = "Read-only: schematic vs board, and the JLCPCB BOM and placement files"
    s.show_toolbar_button = True
    s.icon_file_name = os.path.join(_HERE, "check.png")

  def Run(s):
    try:
      _reload()
      prj = kicad_tools.project.Project(_project_dir())
      text = kicad_tools.check.check(prj.folder).text()
      unsaved = _unsaved_board_changes(prj)
      if unsaved: text = "Note: the board has unsaved changes; this checks the saved file.\n\n" + text
      _show("Project check", text)
    except Exception:
      _show("Project check failed", traceback.format_exc())


class SyncPlugin(pcbnew.ActionPlugin):
  def defaults(s):
    s.name = "Sync schematic from board (BOM, position, LCSC)"
    s.category = "kicad_tools"
    s.description = "Writes the JLCPCB tool's flags and part numbers into the schematic symbols"
    s.show_toolbar_button = True
    s.icon_file_name = os.path.join(_HERE, "sync.png")

  def Run(s):
    try:
      _reload()
      prj = kicad_tools.project.Project(_project_dir())
      unsaved = _unsaved_board_changes(prj)
      if unsaved:
        _show("Save the board first", "These differ between the board in the editor and the saved file:\n\n"
              + "\n".join(unsaved)); return
      locks = prj.locks()
      if locks:
        _show("Close the schematic editor", kicad_tools.sync.apply(prj)[1]); return
      plan = kicad_tools.sync.SyncPlan(prj)
      if not plan.changes:
        _show("Sync schematic", "Schematic already matches the board.\n" + kicad_tools.sync._extras(plan)); return
      if not _show("Sync schematic", "Planned changes:\n" + plan.describe() + "\n" + kicad_tools.sync._extras(plan),
                   ask="Write these into the schematic? (Commit first if you want an undo.)"): return
      ok, msg = kicad_tools.sync.apply(kicad_tools.project.Project(prj.folder))
      _show("Sync schematic" if ok else "Sync failed",
            msg + ("\n\nNext: open the schematic, then Update PCB from Schematic." if ok else ""))
    except Exception:
      _show("Sync failed", traceback.format_exc())
