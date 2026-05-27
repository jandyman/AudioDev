"""
Graph compiler: reads @block markers and a .graph S-expression description,
emits a single header file with the generated pipeline class.

Usage:
  python3 graph_compiler.py graphs/pitch_shifter.graph build/generated/pitch_shifter.h

Naming convention: all names are snake_case throughout — graph type names,
filenames, and C++ class names are identical. No conversion is needed.

Block discovery (per block type referenced in the graph):
  - Search for <type>.cpp in the graph file's own directory, then in any
    (include-dir ...) directories declared in the graph file.
  - If a sibling <type>.dsp exists alongside the .cpp, the block is Faust;
    otherwise it is a plain C++ block.
  - No hardcoded search paths; the graph is self-describing.
"""
import os
import re
import sys

# ============================================================
# S-expression tokenizer + parser
# ============================================================

def tokenize(text):
  out = []
  i = 0; n = len(text)
  while i < n:
    c = text[i]
    if c.isspace():
      i += 1; continue
    if c == ';':
      while i < n and text[i] != '\n': i += 1
      continue
    if c in '()':
      out.append(c); i += 1; continue
    j = i
    while j < n and not text[j].isspace() and text[j] not in '()':
      j += 1
    out.append(text[i:j]); i = j
  return out

def parse_sexpr(text):
  toks = tokenize(text)
  pos = [0]
  def read():
    if pos[0] >= len(toks): raise ValueError("unexpected EOF")
    t = toks[pos[0]]; pos[0] += 1
    if t == '(':
      items = []
      while pos[0] < len(toks) and toks[pos[0]] != ')':
        items.append(read())
      if pos[0] >= len(toks): raise ValueError("unbalanced parens")
      pos[0] += 1
      return items
    if t == ')': raise ValueError("unexpected ')'")
    return t
  forms = []
  while pos[0] < len(toks): forms.append(read())
  return forms

def to_num(s):
  try:
    if isinstance(s, str) and ('.' in s or 'e' in s.lower()): return float(s)
    return int(s)
  except (ValueError, TypeError):
    return s

def parse_kwargs(items):
  out = {}; i = 0
  while i + 1 < len(items):
    k = items[i]
    if isinstance(k, str) and k.startswith(':'):
      out[k.lstrip(':')] = to_num(items[i+1])
      i += 2
    else:
      i += 1
  return out

# ============================================================
# Block discovery — type name == filename == C++ class name
# ============================================================

BLOCK_RE = re.compile(r'/\*\s*@block\b(.*?)\*/', re.DOTALL)

def port_name(p):
  return p[0] if isinstance(p, list) else p

def read_block_marker(cpp_path):
  """Parse the @block marker from cpp_path. Returns defn dict (without is_faust)."""
  with open(cpp_path) as f:
    text = f.read()
  matches = list(BLOCK_RE.finditer(text))
  if not matches:
    raise ValueError(f"{cpp_path}: no @block marker found")
  forms = parse_sexpr(matches[0].group(1))
  if not forms:
    raise ValueError(f"{cpp_path}: empty @block marker")
  form = forms[0]
  if not (isinstance(form, list) and len(form) >= 2 and form[0] == 'define-block'):
    raise ValueError(f"{cpp_path}: malformed @block — expected (define-block NAME ...)")
  name = form[1]
  defn = {'name': name, 'source_file': cpp_path, 'inputs': [], 'outputs': [], 'params': {}}
  for clause in form[2:]:
    if not (isinstance(clause, list) and clause): continue
    head = clause[0]
    if head == 'inputs':
      defn['inputs'] = [port_name(p) for p in clause[1:]]
    elif head == 'outputs':
      defn['outputs'] = [port_name(p) for p in clause[1:]]
    elif head == 'params':
      for p in clause[1:]:
        if isinstance(p, list):
          pname = p[0]
          defn['params'][pname] = float(parse_kwargs(p[1:]).get('default', 0.0))
        else:
          defn['params'][p] = 0.0
  return defn

def find_block(type_name, search_dirs):
  """
  Find the block source in search_dirs.
  Faust block: type_name.dsp (marker lives in the .dsp file).
  C++ block:   type_name.cpp (marker lives in the .cpp file).
  Type name == filename == C++ class name (all snake_case).
  """
  for d in search_dirs:
    dsp_path = os.path.join(d, type_name + '.dsp')
    cpp_path = os.path.join(d, type_name + '.cpp')
    if os.path.exists(dsp_path):
      defn = read_block_marker(dsp_path)
      defn['is_faust'] = True
      return defn
    if os.path.exists(cpp_path):
      defn = read_block_marker(cpp_path)
      defn['is_faust'] = False
      return defn
  raise ValueError(
    f"block type '{type_name}': '{type_name}.dsp/.cpp' not found in {search_dirs}"
  )

# ============================================================
# Graph file parsing
# ============================================================

def parse_graph(text):
  forms = parse_sexpr(text)
  if not (forms and isinstance(forms[0], list) and forms[0][0] == 'graph'):
    raise ValueError("graph file must start with (graph NAME ...)")
  g = forms[0]
  graph = {
    'name': g[1],
    'inputs': [], 'outputs': [],
    'blocks': [], 'connects': [],
    'include_dirs': [],
  }
  for clause in g[2:]:
    if not (isinstance(clause, list) and clause): continue
    head = clause[0]
    if head == 'include-dir':
      graph['include_dirs'].append(clause[1])
    elif head == 'port':
      kind = clause[1]
      if kind == 'input':
        graph['inputs'].append((clause[2], list(clause[3:])))
      elif kind == 'output':
        graph['outputs'].append((clause[2], clause[3]))
    elif head == 'block':
      graph['blocks'].append({
        'instance': clause[1],
        'type': clause[2],
        'params': parse_kwargs(clause[3:]),
      })
    elif head == 'connect':
      graph['connects'].append((clause[1], list(clause[2:])))
  return graph

# ============================================================
# Validate + topological sort
# ============================================================

def split_ref(ref):
  if '.' in ref:
    inst, port = ref.split('.', 1)
    return inst, port
  return None, ref

def validate_and_sort(graph, registry):
  for b in graph['blocks']:
    if b['type'] not in registry:
      raise ValueError(f"unknown block type '{b['type']}' for instance '{b['instance']}'")
  instances = {b['instance']: registry[b['type']] for b in graph['blocks']}

  inputs_of = {}
  graph_input_names = set()
  for name, targets in graph['inputs']:
    graph_input_names.add(name)
    for t in targets:
      inst, port = split_ref(t)
      if (inst, port) in inputs_of:
        raise ValueError(f"{inst}.{port} connected twice")
      inputs_of[(inst, port)] = name
  for src, targets in graph['connects']:
    for t in targets:
      inst, port = split_ref(t)
      if (inst, port) in inputs_of:
        raise ValueError(f"{inst}.{port} connected twice")
      inputs_of[(inst, port)] = src

  for inst, defn in instances.items():
    for ip in defn['inputs']:
      if (inst, ip) not in inputs_of:
        raise ValueError(f"input {inst}.{ip} not connected")

  all_sources = set(graph_input_names)
  for inst, defn in instances.items():
    for op in defn['outputs']:
      all_sources.add(f"{inst}.{op}")
  for (_, _), src in inputs_of.items():
    if src not in all_sources:
      raise ValueError(f"unknown source signal '{src}'")

  deps = {i: set() for i in instances}
  for (inst, _), src in inputs_of.items():
    src_inst, _ = split_ref(src)
    if src_inst is not None:
      deps[inst].add(src_inst)
  order = []
  pending = set(instances)
  while pending:
    ready = sorted([p for p in pending if not deps[p] & pending])
    if not ready:
      raise ValueError("graph has a cycle")
    order.extend(ready)
    pending.difference_update(ready)
  return order, inputs_of, instances

# ============================================================
# Code emission
# ============================================================

def buf_name(source):
  return 'buf_' + source.replace('.', '_')

def include_directive(defn):
  base = os.path.basename(defn['source_file'])
  if defn['is_faust']:
    return f'#include "faust_{base.replace(".dsp", ".cpp")}"'   # build/faust_<type>.cpp
  return f'#include "{base.replace(".cpp", ".h")}"'

def emit(graph, registry, order, inputs_of, instances, out_path, graph_src_path):
  class_name = graph['name']   # snake_case pipeline class name
  blocks = {b['instance']: b for b in graph['blocks']}

  signals = set()
  for name, _ in graph['inputs']:
    signals.add(name)
  for b in graph['blocks']:
    for op in registry[b['type']]['outputs']:
      signals.add(f"{b['instance']}.{op}")

  lines = []
  L = lines.append

  L(f'// Generated by graph_compiler.py from {os.path.basename(graph_src_path)}.')
  L(f'// DO NOT EDIT — regenerate from the .graph source.')
  L('')
  L('#pragma once')
  L('')
  L('#include <cstring>')
  L('#include "faust_minimal.h"')
  L('#include "faust_processor_wrapper.h"')

  seen_types = set()
  for b in graph['blocks']:
    if b['type'] in seen_types: continue
    seen_types.add(b['type'])
    L(include_directive(registry[b['type']]))
  L('')
  L('#ifndef CHUNK_SIZE')
  L('#define CHUNK_SIZE 65536')
  L('#endif')
  L('')
  L(f'class {class_name} {{')
  L('public:')
  L('  static constexpr int kChunkSize = CHUNK_SIZE;')
  L('')

  init_list = []
  for b in graph['blocks']:
    if registry[b['type']]['is_faust']:
      init_list.append(f'blk_{b["instance"]}(new {b["type"]}())')
  L(f'  {class_name}()')
  if init_list:
    L('   : ' + ', '.join(init_list))
  L('  {}')
  L('')

  L('  void init(int sample_rate) {')
  for b in graph['blocks']:
    L(f'    blk_{b["instance"]}.init(sample_rate);')
    for pname, pval in b['params'].items():
      L(f'    blk_{b["instance"]}.set_param("{pname}", {float(pval)}f);')
  L('  }')
  L('')

  L('  void process_chunk(const float* in, float* out, int n) {')
  for name, _ in graph['inputs']:
    L(f'    std::memcpy({buf_name(name)}, in, n * sizeof(float));')
  L('')
  for inst in order:
    defn = instances[inst]
    in_bufs = [buf_name(inputs_of[(inst, ip)]) for ip in defn['inputs']]
    out_bufs = [buf_name(f"{inst}.{op}") for op in defn['outputs']]
    L(f'    {{')
    L(f'      const float* ins[] = {{ {", ".join(in_bufs) if in_bufs else "nullptr"} }};')
    L(f'      float* outs[] = {{ {", ".join(out_bufs) if out_bufs else "nullptr"} }};')
    L(f'      blk_{inst}.process(ins, outs, n);')
    L(f'    }}')
  L('')
  for name, src in graph['outputs']:
    L(f'    std::memcpy(out, {buf_name(src)}, n * sizeof(float));')
  L('  }')
  L('')

  L('  const float* get_buffer(const char* name) const {')
  for sig in sorted(signals):
    L(f'    if (!std::strcmp(name, "{sig}")) return {buf_name(sig)};')
  L('    return nullptr;')
  L('  }')
  L('')

  L('  void set_param(const char* path, float value) {')
  L('    const char* dot = std::strchr(path, \'.\');')
  L('    if (!dot) return;')
  L('    int blen = (int)(dot - path);')
  L('    const char* param = dot + 1;')
  for b in graph['blocks']:
    if registry[b['type']]['params']:
      inst = b['instance']
      L(f'    if (blen == {len(inst)} && !std::strncmp(path, "{inst}", {len(inst)})) {{ blk_{inst}.set_param(param, value); return; }}')
  L('  }')
  L('')

  L('private:')
  L('  // Static buffers (one per signal)')
  for sig in sorted(signals):
    L(f'  float {buf_name(sig)}[CHUNK_SIZE];')
  L('')
  L('  // Block instances')
  for b in graph['blocks']:
    if registry[b['type']]['is_faust']:
      L(f'  FaustProcessorWrapper blk_{b["instance"]};')
    else:
      L(f'  {b["type"]} blk_{b["instance"]};')
  L('};')
  L('')

  os.makedirs(os.path.dirname(out_path), exist_ok=True)
  with open(out_path, 'w') as f:
    f.write('\n'.join(lines))
  print(f"Wrote {out_path}")

# ============================================================
# Main
# ============================================================

def main():
  if len(sys.argv) != 3:
    print("Usage: graph_compiler.py <graph.graph> <out.h>", file=sys.stderr)
    sys.exit(1)
  graph_path = sys.argv[1]
  out_path = sys.argv[2]

  with open(graph_path) as f:
    graph = parse_graph(f.read())

  # Search path: graph's own directory + any declared include-dirs.
  # include-dir paths are relative to the graph file's directory.
  graph_dir = os.path.dirname(os.path.abspath(graph_path))
  search_dirs = [graph_dir]
  for d in graph['include_dirs']:
    if os.path.isabs(d):
      search_dirs.append(os.path.normpath(d))
    else:
      search_dirs.append(os.path.normpath(os.path.join(graph_dir, d)))

  # Build registry: targeted lookup per unique type (no scan-all).
  registry = {}
  for b in graph['blocks']:
    t = b['type']
    if t not in registry:
      registry[t] = find_block(t, search_dirs)
  print(f"Found {len(registry)} block type(s): {sorted(registry)}")
  print(f"Graph '{graph['name']}': {len(graph['blocks'])} blocks, {len(graph['connects'])} connects")

  order, inputs_of, instances = validate_and_sort(graph, registry)
  print(f"Topological order: {order}")

  emit(graph, registry, order, inputs_of, instances, out_path, graph_path)

if __name__ == '__main__':
  main()
