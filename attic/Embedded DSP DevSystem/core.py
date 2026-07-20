"""
Core DSP Framework Classes
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any


class Module(ABC):
	"""Abstract base class for all DSP processing modules."""

	input_ports: List[str] = ["input"]
	output_ports: List[str] = ["output"]
	_instance_count: int = 0

	def __init__(s, name: str = None) -> None:
		"""Initialize module with optional name."""
		s.__class__._instance_count += 1
		if name is None:
			class_name = s.__class__.__name__.lower()
			s.name = f"{class_name}_{s.__class__._instance_count}"
		else:
			s.name = name
		s.parent_graph = None

	@classmethod
	def reset_instance_count(cls) -> None:
		"""Reset instance counter for this class. Useful for testing."""
		cls._instance_count = 0

	def pathname(s) -> str:
		"""Return full pathname showing hierarchy from top-level graph."""
		if s.parent_graph is None:
			return s.name
		return f"{s.parent_graph.pathname()}.{s.name}"

	def init(s) -> None:
		"""Initialize the module for processing. Override in subclasses."""
		pass

	@abstractmethod
	def proc(s, inputs: Dict[str, Any]) -> Dict[str, Any]:
		"""Process input signals and return output signals."""
		raise NotImplementedError("proc method must be implemented by subclasses")


class Graph(Module):
	"""Graph class for containing and connecting DSP modules."""

	def __init__(s, name: str = None) -> None:
		super().__init__(name)
		s.modules: Dict[str, Module] = {}  # name -> module mapping
		s.connections: List[Tuple[str, str, str, str]] = []  # list of (src_mod, src_port, dst_mod, dst_port) tuples
		s.passthrough_inputs: Dict[str, Tuple[str, str]] = {}  # external_port -> (module_name, port_name)
		s.passthrough_outputs: Dict[str, Tuple[str, str]] = {}  # external_port -> (module_name, port_name)

	def add_module(s, name: str, module: Module) -> None:
		"""Add a module to the graph with given name."""
		s.modules[name] = module
		module.parent_graph = s

	def connect(s, src_module: str, dst_module: str, src_port: str = "output", dst_port: str = "input") -> None:
		"""Connect output port of source module to input port of destination module."""
		# Validate modules exist
		if src_module not in s.modules:
			raise ValueError(f"Source module '{src_module}' not found in graph")
		if dst_module not in s.modules:
			raise ValueError(f"Destination module '{dst_module}' not found in graph")

		# Validate ports exist
		src_mod = s.modules[src_module]
		dst_mod = s.modules[dst_module]
		if src_port not in src_mod.output_ports:
			raise ValueError(f"Output port '{src_port}' not found on module '{src_module}'")
		if dst_port not in dst_mod.input_ports:
			raise ValueError(f"Input port '{dst_port}' not found on module '{dst_module}'")

		# Add connection
		connection = (src_module, src_port, dst_module, dst_port)
		if connection not in s.connections:
			s.connections.append(connection)

	def disconnect(s, src_module: str, src_port: str, dst_module: str, dst_port: str) -> None:
		"""Remove connection between specified ports."""
		connection = (src_module, src_port, dst_module, dst_port)
		if connection in s.connections:
			s.connections.remove(connection)
		else:
			raise ValueError(f"Connection not found: {connection}")

	def map_input(s, external_port: str, module_name: str, module_port: str) -> None:
		"""Map external input port to internal module port."""
		s.passthrough_inputs[external_port] = (module_name, module_port)

	def map_output(s, external_port: str, module_name: str, module_port: str) -> None:
		"""Map external output port to internal module port."""
		s.passthrough_outputs[external_port] = (module_name, module_port)

	def determine_proc_order(s) -> List[str]:
		"""Determine processing order based on dependency graph, descending through hierarchy."""
		# Build dependency map: module -> set of modules that must run before it
		dependencies = {name: set() for name in s.modules}

		# Add dependencies from internal connections
		for src_mod, src_port, dst_mod, dst_port in s.connections:
			dependencies[dst_mod].add(src_mod)

		# Topological sort using Kahn's algorithm
		result = []
		processed = set()  # Track which top-level modules we've processed
		ready = [name for name, deps in dependencies.items() if len(deps) == 0]

		while ready:
			current = ready.pop(0)
			processed.add(current)

			# If current module is a Graph, get its internal processing order
			if isinstance(s.modules[current], Graph):
				internal_order = s.modules[current].determine_proc_order()
				# Add internal modules with qualified names
				for internal_mod in internal_order:
					result.append(f"{current}.{internal_mod}")
			else:
				result.append(current)

			# Remove this module from all dependency sets
			for name, deps in dependencies.items():
				if current in deps:
					deps.remove(current)
					if len(deps) == 0 and name not in processed:
						ready.append(name)

		# Check for cycles - all top-level modules should be processed
		if len(processed) != len(s.modules):
			remaining = set(s.modules.keys()) - processed
			raise ValueError(f"Circular dependencies detected among modules: {remaining}")

		return result

	def pretty_print(s, indent: int = 0) -> str:
		"""Return a formatted string showing the graph hierarchy."""
		lines = []
		prefix = "  " * indent

		# Show this graph
		lines.append(f"{prefix}{s.name} (Graph)")

		# Show all modules in this graph
		for module_name, module in s.modules.items():
			if isinstance(module, Graph):
				# Recursively show sub-graphs
				lines.append(module.pretty_print(indent + 1))
			else:
				# Show regular module with its instance name
				lines.append(f"{prefix}  {module.name} ({module.__class__.__name__})")

		return "\n".join(lines)

	def pretty_print_with_connections(s, indent: int = 0) -> str:
		"""Return a formatted string showing hierarchy with inline connections."""
		lines = []
		prefix = "  " * indent

		# Show this graph
		lines.append(f"{prefix}{s.name} (Graph)")

		# Show all modules in this graph
		for module_name, module in s.modules.items():
			if isinstance(module, Graph):
				# Recursively show sub-graphs
				lines.append(module.pretty_print_with_connections(indent + 1))
			else:
				# Show regular module
				lines.append(f"{prefix}  {module.name} ({module.__class__.__name__})")

				# Show outgoing connections from this module
				for src_mod, src_port, dst_mod, dst_port in s.connections:
					if src_mod == module_name:
						# Find destination module to get its name
						dst_module = s.modules[dst_mod]
						if isinstance(dst_module, Graph):
							dst_display = f"{dst_module.name}"
						else:
							dst_display = f"{dst_module.name}"

						# Show connection
						port_info = f".{src_port}" if src_port != "output" else ""
						dst_port_info = f".{dst_port}" if dst_port != "input" else ""
						lines.append(f"{prefix}    → {src_port} connects to: {dst_display}{dst_port_info}")

		return "\n".join(lines)

	def pretty_print_proc_order(s) -> str:
		"""Return a formatted string showing processing order with full pathnames."""
		proc_order = s.determine_proc_order()
		lines = ["PROCESSING ORDER:"]

		for i, qualified_name in enumerate(proc_order, 1):
			# Find the actual module to get its pathname and class
			parts = qualified_name.split('.')
			current_graph = s

			# Navigate to the module through the hierarchy
			for part in parts[:-1]:  # All but the last part are graph names
				current_graph = current_graph.modules[part]

			# Get the final module
			final_module_key = parts[-1]
			final_module = current_graph.modules[final_module_key]

			# Use the module's pathname() method to get proper instance names
			full_pathname = final_module.pathname()
			lines.append(f"{i:2d}. {full_pathname} ({final_module.__class__.__name__})")

		return "\n".join(lines)

	def proc(s, inputs: Dict[str, Any]) -> Dict[str, Any]:
		"""Process graph by executing all modules in dependency order."""
		# TODO: Implement graph processing logic
		raise NotImplementedError("Graph processing not yet implemented")