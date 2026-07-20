import types
import typing
from io import StringIO
from textwrap import indent
from typing import List, Tuple, get_args, get_origin
import builtins
import regex as re
from dataclasses import dataclass, Field, is_dataclass
import numpy as np
import importlib
import inspect

output_path = 'cpp_blocks'

def c_param_list(python_list: List[str]):
  for i in (("[", "("), ("]", ")")):
    python_list = python_list.replace(i[0], i[1])
    return python_list

def struct_entry_names_and_types(data_class):
  items = [(name, f.type) for name, f in data_class.__dataclass_fields__.items()]
  return entry_names_and_types(items)

def get_numpy_inner_type(ntype):
  d = {'float32': 'float', 'float64': 'double'}
  if type(ntype) == types.GenericAlias:
    t = get_args(get_args(ntype)[1])[0]
    return d[t.__name__]
  else:
    assert ntype.__name__ == "ndarray"
    return d['float32']

def is_numpy_type(dtype):
  if dtype.__name__ == 'ndarray': return True
  if type(dtype) == types.GenericAlias:
    pass

def is_list_type(type_hint):
  try:
    return get_origin(type_hint) is list
  except (TypeError, AttributeError):
    return False


def entry_names_and_types(items: List[Tuple]):
  results = []
  for name_str, dtype in items:
    if dtype.__module__ == 'typing':
      outer = dtype.__origin__
      inner = dtype.__args__[0]
      match outer:
        case builtins.list:
          if inner == np.ndarray or type(inner) == types.GenericAlias:
            type_str = f'vector<vector<{get_numpy_inner_type(inner)}>>'
          elif inner == int:
            type_str = 'vector<int>'
          else:
            raise Exception("unknown List entry type for struct def")
        case _:
          raise Exception("unknown type for struct def")
    elif dtype.__module__ == 'numpy':
      type_str = f'vector<{get_numpy_inner_type(dtype)}>'
    else:
      type_str = dtype.__name__
    results.append((name_str, type_str))
  return results

def struct_entries(data_class):
  return [f'{dtype} {name}' for name, dtype in struct_entry_names_and_types(data_class)]

def pybind_struct_entries(data_class):
  items = struct_entry_names_and_types(data_class)
  return [f'.def_readwrite("{name}", &{data_class.__name__}::{name})' for name, _ in items]

def cls_items_for_module(module_name):
  mod_info = ModuleInfo(module_name)
  return mod_info.cls_info

def c_dependencies_for_module(module_name) -> str:
  module = importlib.import_module(module_name)
  items = [val for key, val in inspect.getmembers(module) if key == 'c_dependencies']
  dependencies = items[0] if len(items) > 0 else []
  for name in dependencies:
    dependencies.extend(c_dependencies_for_module(name))
  return dependencies


class ModuleInfo:
  def __init__(s, module_name):
    s.module_name = module_name
    s.module = importlib.import_module(module_name)
    classes = inspect.getmembers(s.module, predicate=inspect.isclass)
    s.cls_info = [(name, cls) for name, cls in classes if cls.__module__ == module_name]
    s.c_dependency_names = list(set(c_dependencies_for_module(s.module_name)))


class CppCodeGen:
  def __init__(s):
    s.io = StringIO()
    s.indent = 0
    s.last_line_blank = True

  def reset(s): s.__init__()

  def write(s, str):
    s.io.write(indent(str, s.indent * ' '))

  def write_ln(s, str = ""):
    s.io.write(indent(str+'\n', s.indent * ' '))
    s.last_line_blank = str == ''

  def ensure_blank_line(s):
    if not s.last_line_blank: s.write_ln()

  def statement(s, str):
    s.write_ln(str + ";")

  def open_block(s, str = ''):
    s.write_ln(str + " {")
    s.indent += 2

  def close_block(s, semicolon: bool = False):
    s.indent -= 2
    term = ";" if semicolon else ""
    s.write(f'}}{term}\n')

  def close_blocks(s):
    while s.indent > 0: s.close_block()

  def write_block(s, intro: str, body: str):
    s.open_block(intro)
    s.write(body)
    s.close_block()

  def with_function_args(s, func_str, arg_lines: List[str]):
    func_str += '('
    prev_indent = s.indent
    s.write(func_str + arg_lines[0])
    s.indent += len(func_str)
    for arg_line in arg_lines[1:]:
      s.io.write(',\n')
      s.write(arg_line)
    s.io.write(')\n')
    s.indent = prev_indent

  def struct_def(s, data_class, name: str):
    s.open_block(f'struct {name}')
    strs = struct_entries(data_class)
    for str in strs: s.statement(str)
    if hasattr(data_class, 'c_lines'):
      s.emit_c_lines(getattr(data_class, 'c_lines'))
    s.close_block(semicolon=True)

  def pybind_np_def(s, cls_name, name, dtype: str):
    args = [f'"{name}"']
    args.append(f'[](const {cls_name}& o) {{ return vec_to_np(o.{name}); }}')
    args.append(f'[]({cls_name}& o, py::array_t<{dtype}> v) {{ o.{name} = np_to_vec<{dtype}>(v); }}')
    s.with_function_args('.def_property', args)

  def pybind_listof_np_def(s, cls_name, name, dtype: str):
    args = [f'"{name}"']
    args.append(f'[](const {cls_name}& o) {{ return vect_of_vect_to_list_of_np(o.{name}); }}')
    args.append(f'[]({cls_name}& o, py::list v) {{ o.{name} = np_list_to_vect_of_vect<{dtype}>(v); }}')
    s.with_function_args('.def_property', args)

  def pybind_dataclass_struct_def(s, data_class, cls_name: str):
    s.ensure_blank_line()
    s.write_ln(f'py::class_<{cls_name}>(m, "{cls_name}")')
    s.indent += 2
    s.write_ln('.def(py::init<>())')
    pattern = r'([A-Za-z\s]+)'
    for name, type in struct_entry_names_and_types(data_class):
      if len(m := re.findall(rf'vector<{pattern}>', type)) > 0:
        s.pybind_np_def(cls_name, name, m[0])
      elif len(m := re.findall(rf'vector<vector<{pattern}>>', type)) > 0:
        s.pybind_listof_np_def(cls_name, name, m[0])
      else:
        s.write_ln(f'.def_readwrite("{name}", &{cls_name}::{name})')
    s.statement('')
    s.indent -= 2

  def func_def(s, cls, func_name):
    def check_ref(dtype):
      # only pass ints and floats by value, everything else by reference
      return f'{dtype}' if dtype in ['int', 'float'] else f'{dtype}&'
    arg_hints = typing.get_type_hints(getattr(cls, func_name))
    names_types = entry_names_and_types(arg_hints.items())
    return_types = [dtype for name, dtype in names_types if name == 'return']
    return_type = return_types[0] if len(return_types) > 0 else 'void'
    arg_strs = [f'{check_ref(dtype)} {name}' for name, dtype in names_types if name != 'return']
    args_str = ', '.join(arg_strs)
    s.statement(f'{return_type} {func_name}({args_str})')

  def struct_defs_for_module(s, module_name, subtype_names = ["State", "Params"]):
    s.reset()
    mod_info = ModuleInfo(module_name)
    cls_items = mod_info.cls_info
    s.write_ln('#pragma once')
    for i in ['vector', 'cstdint']: s.write_ln(f'#include <{i}>')
    s.write_ln('#include "platform.h"')
    for i in mod_info.c_dependency_names:
      s.write_ln(f'#include "{i}.h"')
    s.statement('using std::vector')
    for name, cls in cls_items:
      member_suffixes = []
      for subtype_name in subtype_names:
        if hasattr(cls, subtype_name):
          s.ensure_blank_line()
          subtype = getattr(cls, f'{subtype_name}')
          s.struct_def(subtype, f'{name}{subtype_name}')
          member_suffixes.append(subtype_name)
      if hasattr(cls, 'c_funcs'):
        s.ensure_blank_line()
        s.open_block(f'struct {name}')
        for suffix in member_suffixes:
          s.statement(f'{name}{suffix} {suffix.lower()}')
        for func_name in cls.c_funcs:
          s.func_def(cls, func_name)
        s.close_block(semicolon=True)

  def pybind_class_func_def(s, cls, func_name):
    arg_hints = typing.get_type_hints(getattr(cls, func_name)).items()
    has_np_array_args = False
    arg_list = [f'{cls.__name__}& o']
    call_list = []
    to_vec_statements = []
    from_vec_statements = []
    py_arg_statements = []
    for name, dtype in arg_hints:
      if is_numpy_type(dtype):
        ntype = get_numpy_inner_type(dtype)
        has_np_array_args = True
        arg_list.append(f'py::array_t<{ntype}> {name}')
        call_list.append(f'v_{name}')
        to_vec_statements.append(f'vector<{ntype}> v_{name} = np_to_vec<{ntype}>({name})')
        from_vec_statements.append(f'copy_vec_to_np(v_{name}, {name})')
        py_arg_statements.append(f'py::arg("{name}").noconvert()')
      elif is_list_type(dtype):
        has_np_array_args = True
        ntype = get_numpy_inner_type(get_args(dtype)[0])
        arg_list.append(f'py::list {name}')
        call_list.append(f'v_{name}')
        to_vec_statements.append(f'vector<vector<{ntype}>> v_{name} = np_list_to_vect_of_vect<{ntype}>({name})')
        from_vec_statements.append(f'cp_vec_vec_into_list_of_np(v_{name}, {name})')
        py_arg_statements.append(f'py::arg("{name}").noconvert()')
      else:
        arg_list.append(f'{type.__name__} {name}')
        call_list.append(name)
        py_arg_statements.append(f'py::arg("{name}")')
    if not has_np_array_args:
      s.write_ln(f'.def("{func_name}", &{cls.__name__}::{func_name})')
    else:
      s.write_ln(f'.def("{func_name}", []({", ".join(arg_list)}) {{')
      s.indent += 6
      for st in to_vec_statements: s.statement(st)
      s.statement(f'o.{func_name}({",".join(call_list)})')
      for st in from_vec_statements: s.statement(st)
      s.indent -= 2
      s.write_ln(f'}}, {", ".join(py_arg_statements)} )')
      s.indent -= 4

  def pybind_class_struct_def(s, cls):
    cls_name = cls.__name__
    s.ensure_blank_line()
    s.write_ln(f'py::class_<{cls_name}>(m, "{cls_name}")')
    s.indent += 2
    s.write_ln('.def(py::init<>())')
    for item in ['Params', 'State']:
      if hasattr(cls, item):
        s.write_ln(f'.def_readwrite("{item.lower()}", &{cls_name}::{item.lower()})')
    if hasattr(cls, 'c_funcs'):
      for func_name in cls.c_funcs:
        s.pybind_class_func_def(cls, func_name)
    s.statement('')
    s.indent -= 2

  def pybind_defs_for_module(s, module_name, subtype_names = ["State", "Params"]):
    s.reset()
    mod_info = ModuleInfo(module_name)
    cls_items = mod_info.cls_info
    includes = []
    for name in mod_info.c_dependency_names:
      includes.append(name)
      submod_info = ModuleInfo(name)
      cls_items.extend(submod_info.cls_info)
    includes.append(module_name)
    includes.append('pybind_support')
    for item in includes: s.write_ln(f'#include "{item}.h"')
    s.ensure_blank_line()
    s.open_block(f'PYBIND11_MODULE(pybind_{module_name}, m)')
    for name, cls in cls_items:
      for subtype_name in subtype_names:
        subtype = getattr(cls, f'{subtype_name}', None)
        if subtype:
          s.pybind_dataclass_struct_def(subtype, f'{name}{subtype_name}')
          s.ensure_blank_line()
      if hasattr(cls, 'c_funcs'):
        s.pybind_class_struct_def(cls)
    s.close_block()

  # emit c code sourced from python multiline comments
  def emit_c_lines(s, c_lines: str):
    lines = re.split("\n", c_lines)
    last_idx = len(lines) - 1
    if lines[last_idx].lstrip() == '': lines.pop()
    if lines[0] == '': lines.pop(0)
    leading = len(lines[0]) - len(lines[0].lstrip())
    for l in lines: s.write_ln(l[leading:])

  def emit_lines(s, lines: str):
    lines = re.split("\n", lines)
    for l in lines:
      s.write_ln(l.rstrip())

  def print(s):
    s.io.flush()
    print(s.io.getvalue())

  def write_file(s, filename):
    fp = open(filename, "w")
    fp.write(s.io.getvalue())
    fp.flush()

  def write_pybind_file(s, module_name: str):
    s.pybind_defs_for_module(module_name)
    file_name = f'{output_path}/pybind_{module_name}.cpp'
    s.write_file(file_name)

  def write_struct_file(s, module_name: str):
    s.struct_defs_for_module(module_name)
    file_name = f'{output_path}/{module_name}.h'
    s.write_file(file_name)

if __name__ == '__main__':
  import old_block_streaming as bs

  @dataclass
  class ork:
    foo: int
    bar: List[np.ndarray]

  gen = CppCodeGen()
  gen.open_block("foo")
  gen.open_block("bar")
  gen.statement("hello world")
  gen.close_blocks()

  pass
