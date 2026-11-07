"""
Minimal KiCad s-expression reader that remembers where everything came from.

Every node and atom keeps its character span in the source text, so a writer can
change one value in place and leave every other byte of the file untouched. That
keeps git diffs to the lines that actually changed, and means nothing is ever
re-serialised in a layout KiCad did not write.
"""

from __future__ import annotations
import re

_TOKEN = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+')


class Atom:
  __slots__ = ("text", "start", "end", "quoted")

  def __init__(s, text: str, start: int, end: int, quoted: bool):
    s.text = text; s.start = start; s.end = end; s.quoted = quoted

  def __repr__(s):
    return f"Atom({s.text!r})"


class Node:
  """A parenthesised list. items[0] is normally the keyword atom."""
  __slots__ = ("items", "start", "end")

  def __init__(s, start: int):
    s.items: list = []; s.start = start; s.end = -1

  @property
  def key(s) -> str:
    return s.items[0].text if s.items and isinstance(s.items[0], Atom) else ""

  def children(s, key: str | None = None) -> list[Node]:
    return [c for c in s.items if isinstance(c, Node) and (key is None or c.key == key)]

  def child(s, key: str) -> Node | None:
    for c in s.items:
      if isinstance(c, Node) and c.key == key: return c
    return None

  def atom(s, i: int) -> Atom | None:
    return s.items[i] if len(s.items) > i and isinstance(s.items[i], Atom) else None

  def value(s, i: int = 1) -> str | None:
    a = s.atom(i)
    return a.text if a else None

  def walk(s, key: str):
    if s.key == key: yield s
    for c in s.children(): yield from c.walk(key)

  def __repr__(s):
    return f"Node({s.key!r}, {len(s.items)} items)"


def _unquote(t: str) -> str:
  return t[1:-1].replace('\\"', '"').replace("\\\\", "\\")


def quote(v: str) -> str:
  return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'


def parse(text: str) -> Node:
  stack: list[Node] = [Node(0)]
  for m in _TOKEN.finditer(text):
    t = m.group(0)
    if t == "(":
      stack.append(Node(m.start()))
    elif t == ")":
      n = stack.pop(); n.end = m.end(); stack[-1].items.append(n)
    elif t[0] == '"':
      stack[-1].items.append(Atom(_unquote(t), m.start(), m.end(), True))
    else:
      stack[-1].items.append(Atom(t, m.start(), m.end(), False))
  if len(stack) != 1: raise ValueError("unbalanced parentheses")
  top = stack[0].children()
  if len(top) != 1: raise ValueError("expected exactly one top-level expression")
  return top[0]


def apply_edits(text: str, edits: list[tuple[int, int, str]]) -> str:
  """Apply (start, end, replacement) edits; spans must not overlap."""
  edits = sorted(edits, key=lambda e: e[0])
  for a, b in zip(edits, edits[1:]):
    if a[1] > b[0]: raise ValueError("overlapping edits")
  out, pos = [], 0
  for start, end, rep in edits:
    out.append(text[pos:start]); out.append(rep); pos = end
  out.append(text[pos:])
  return "".join(out)
