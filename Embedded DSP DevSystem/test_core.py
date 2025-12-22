"""
Unit tests for core DSP framework classes
"""

import pytest
from core import Module, Graph


class TestModule(Module):
	"""Simple test module for unit testing."""

	def proc(s, inputs):
		return {"output": inputs.get("input", "test_signal")}


class MultiPortModule(Module):
	"""Test module with multiple ports."""

	input_ports = ["left", "right"]
	output_ports = ["left_out", "right_out"]

	def proc(s, inputs):
		return {
			"left_out": inputs.get("left", "left_signal"),
			"right_out": inputs.get("right", "right_signal")
		}


class SourceModule(Module):
	"""Module with no inputs (generates signals)."""

	input_ports = []
	output_ports = ["sine", "square"]

	def proc(s, inputs):
		return {"sine": "sine_wave", "square": "square_wave"}


class MixerModule(Module):
	"""Module that mixes multiple inputs to single output."""

	input_ports = ["input1", "input2", "input3"]
	output_ports = ["mix_out"]

	def proc(s, inputs):
		return {"mix_out": "mixed_signal"}


class SplitterModule(Module):
	"""Module that splits one input to multiple outputs."""

	input_ports = ["main_in"]
	output_ports = ["out1", "out2", "out3", "out4"]

	def proc(s, inputs):
		return {
			"out1": inputs.get("main_in", "split1"),
			"out2": inputs.get("main_in", "split2"),
			"out3": inputs.get("main_in", "split3"),
			"out4": inputs.get("main_in", "split4")
		}


def test_module_defaults():
	"""Test Module class has correct default ports."""
	mod = TestModule()
	assert mod.input_ports == ["input"]
	assert mod.output_ports == ["output"]


def test_module_custom_ports():
	"""Test Module with custom port definitions."""
	mod = MultiPortModule()
	assert mod.input_ports == ["left", "right"]
	assert mod.output_ports == ["left_out", "right_out"]


def test_module_init():
	"""Test Module init method."""
	mod = TestModule()
	mod.init()  # Should not raise exception


def test_module_naming():
	"""Test Module naming functionality."""
	# Reset counter for clean test
	TestModule.reset_instance_count()

	# Test auto-generated names
	mod1 = TestModule()
	mod2 = TestModule()
	assert mod1.name == "testmodule_1"
	assert mod2.name == "testmodule_2"

	# Test custom names
	mod3 = TestModule("CustomName")
	assert mod3.name == "CustomName"

	# Auto-generated should continue counting
	mod4 = TestModule()
	assert mod4.name == "testmodule_4"


def test_graph_naming():
	"""Test Graph naming functionality."""
	# Reset counter for clean test
	Graph.reset_instance_count()

	graph1 = Graph()
	graph2 = Graph()
	assert graph1.name == "graph_1"
	assert graph2.name == "graph_2"

	graph3 = Graph("MyGraph")
	assert graph3.name == "MyGraph"


def test_pathname_simple():
	"""Test pathname for modules in top-level graph."""
	TestModule.reset_instance_count()
	Graph.reset_instance_count()

	top_graph = Graph("TopLevel")
	module1 = TestModule("Module1")
	module2 = TestModule("Module2")

	# Before adding to graph, pathname should just be the name
	assert module1.pathname() == "Module1"

	# Add to graph
	top_graph.add_module("mod1", module1)
	top_graph.add_module("mod2", module2)

	# Now pathname should include graph
	assert module1.pathname() == "TopLevel.Module1"
	assert module2.pathname() == "TopLevel.Module2"


def test_pathname_nested():
	"""Test pathname for nested graphs."""
	TestModule.reset_instance_count()
	Graph.reset_instance_count()

	# Create hierarchy: top -> sub -> module
	top_graph = Graph("TopGraph")
	sub_graph = Graph("SubGraph")
	module = TestModule("DeepModule")

	# Build hierarchy
	top_graph.add_module("sub", sub_graph)
	sub_graph.add_module("mod", module)

	# Test pathnames
	assert top_graph.pathname() == "TopGraph"
	assert sub_graph.pathname() == "TopGraph.SubGraph"
	assert module.pathname() == "TopGraph.SubGraph.DeepModule"


def test_pathname_complex_hierarchy():
	"""Test pathname with complex nested structure."""
	TestModule.reset_instance_count()
	Graph.reset_instance_count()

	# Create 3-level hierarchy
	level0 = Graph("Level0")
	level1 = Graph("Level1")
	level2 = Graph("Level2")
	module = TestModule("FinalModule")

	# Build hierarchy
	level0.add_module("l1", level1)
	level1.add_module("l2", level2)
	level2.add_module("final", module)

	# Test deep pathname
	assert module.pathname() == "Level0.Level1.Level2.FinalModule"


def test_pretty_print_complex():
	"""Test pretty printing with a complex hierarchical structure."""
	# Reset counters for clean output
	TestModule.reset_instance_count()
	MultiPortModule.reset_instance_count()
	SourceModule.reset_instance_count()
	MixerModule.reset_instance_count()
	SplitterModule.reset_instance_count()
	Graph.reset_instance_count()

	# Create a complex audio processing graph with meaningful names only where needed
	main_graph = Graph("AudioProcessor")

	# Input section
	input_graph = Graph()  # Will be "graph_1"
	stereo_input = MultiPortModule()  # Will be "multiportmodule_1"
	input_splitter = SplitterModule()  # Will be "splittermodule_1"
	input_graph.add_module("stereo", stereo_input)
	input_graph.add_module("splitter", input_splitter)

	# Effects section with nested processing
	effects_graph = Graph()  # Will be "graph_2"

	# Reverb sub-section
	reverb_graph = Graph()  # Will be "graph_3"
	early_reflections = TestModule()  # Will be "testmodule_1"
	late_reverb = TestModule()  # Will be "testmodule_2"
	reverb_mix = MixerModule()  # Will be "mixermodule_1"
	reverb_graph.add_module("early", early_reflections)
	reverb_graph.add_module("late", late_reverb)
	reverb_graph.add_module("mix", reverb_mix)

	# EQ sub-section
	eq_graph = Graph()  # Will be "graph_4"
	low_eq = TestModule()  # Will be "testmodule_3"
	mid_eq = TestModule()  # Will be "testmodule_4"
	high_eq = TestModule()  # Will be "testmodule_5"
	eq_graph.add_module("low", low_eq)
	eq_graph.add_module("mid", mid_eq)
	eq_graph.add_module("high", high_eq)

	effects_graph.add_module("reverb", reverb_graph)
	effects_graph.add_module("eq", eq_graph)

	# Output section
	output_graph = Graph()  # Will be "graph_5"
	limiter = TestModule()  # Will be "testmodule_6"
	stereo_out = MultiPortModule()  # Will be "multiportmodule_2"
	output_graph.add_module("limiter", limiter)
	output_graph.add_module("stereo_out", stereo_out)

	# Assemble main graph
	main_graph.add_module("input", input_graph)
	main_graph.add_module("effects", effects_graph)
	main_graph.add_module("output", output_graph)

	# Add some connections within subgraphs to demonstrate
	input_graph.connect("stereo", "splitter", "left_out", "main_in")  # stereo -> splitter
	reverb_graph.connect("early", "mix", "output", "input1")  # early -> mix
	reverb_graph.connect("late", "mix", "output", "input2")   # late -> mix
	eq_graph.connect("low", "mid")   # low -> mid -> high
	eq_graph.connect("mid", "high")
	output_graph.connect("limiter", "stereo_out", "output", "left")  # limiter -> stereo_out

	# Generate and print the hierarchy
	output = main_graph.pretty_print()
	print("\n" + "="*50)
	print("COMPLEX AUDIO PROCESSOR HIERARCHY:")
	print("="*50)
	print(output)
	print("="*50)

	# Generate and print with connections
	output_with_conn = main_graph.pretty_print_with_connections()
	print("\n" + "="*50)
	print("COMPLEX AUDIO PROCESSOR WITH CONNECTIONS:")
	print("="*50)
	print(output_with_conn)
	print("="*50)

	# Determine and print processing order with instance names
	print("\n" + "="*50)
	print(main_graph.pretty_print_proc_order())
	print("="*50)

	# Test that some key elements are in the output
	assert "AudioProcessor (Graph)" in output
	assert "Graph" in output  # Should have multiple Graph instances
	assert "TestModule" in output  # Should have multiple TestModule instances
	assert "MultiPortModule" in output

	# Test connections are shown in the connections version
	assert "→" in output_with_conn
	assert "connects to:" in output_with_conn



def test_module_proc_not_implemented():
	"""Test abstract Module raises NotImplementedError."""
	with pytest.raises(TypeError):  # Can't instantiate abstract class
		Module()


def test_graph_creation():
	"""Test Graph creation and basic properties."""
	graph = Graph()
	assert len(graph.modules) == 0
	assert len(graph.connections) == 0
	assert len(graph.passthrough_inputs) == 0
	assert len(graph.passthrough_outputs) == 0


def test_graph_add_module():
	"""Test adding modules to graph."""
	graph = Graph()
	mod1 = TestModule()
	mod2 = TestModule()

	graph.add_module("mod1", mod1)
	graph.add_module("mod2", mod2)

	assert len(graph.modules) == 2
	assert graph.modules["mod1"] is mod1
	assert graph.modules["mod2"] is mod2


def test_graph_connect_valid():
	"""Test valid module connections."""
	graph = Graph()
	mod1 = TestModule()
	mod2 = TestModule()

	graph.add_module("mod1", mod1)
	graph.add_module("mod2", mod2)
	graph.connect("mod1", "mod2")

	assert len(graph.connections) == 1
	assert graph.connections[0] == ("mod1", "output", "mod2", "input")


def test_graph_connect_custom_ports():
	"""Test connections with custom port names."""
	graph = Graph()
	mod1 = MultiPortModule()
	mod2 = MultiPortModule()

	graph.add_module("mod1", mod1)
	graph.add_module("mod2", mod2)
	graph.connect("mod1", "mod2", "left_out", "left")

	assert len(graph.connections) == 1
	assert graph.connections[0] == ("mod1", "left_out", "mod2", "left")


def test_graph_connect_invalid_module():
	"""Test connection with non-existent module."""
	graph = Graph()
	mod1 = TestModule()
	graph.add_module("mod1", mod1)

	with pytest.raises(ValueError, match="Source module 'invalid' not found"):
		graph.connect("invalid", "mod1")

	with pytest.raises(ValueError, match="Destination module 'invalid' not found"):
		graph.connect("mod1", "invalid")


def test_graph_connect_invalid_port():
	"""Test connection with invalid port names."""
	graph = Graph()
	mod1 = TestModule()
	mod2 = TestModule()

	graph.add_module("mod1", mod1)
	graph.add_module("mod2", mod2)

	with pytest.raises(ValueError, match="Output port 'invalid' not found"):
		graph.connect("mod1", "mod2", "invalid", "input")

	with pytest.raises(ValueError, match="Input port 'invalid' not found"):
		graph.connect("mod1", "mod2", "output", "invalid")


def test_graph_disconnect():
	"""Test disconnecting modules."""
	graph = Graph()
	mod1 = TestModule()
	mod2 = TestModule()

	graph.add_module("mod1", mod1)
	graph.add_module("mod2", mod2)
	graph.connect("mod1", "mod2")

	assert len(graph.connections) == 1

	graph.disconnect("mod1", "output", "mod2", "input")
	assert len(graph.connections) == 0


def test_graph_disconnect_invalid():
	"""Test disconnecting non-existent connection."""
	graph = Graph()

	with pytest.raises(ValueError, match="Connection not found"):
		graph.disconnect("mod1", "output", "mod2", "input")


def test_graph_map_ports():
	"""Test mapping external ports to internal modules."""
	graph = Graph()
	mod1 = TestModule()

	graph.add_module("mod1", mod1)
	graph.map_input("external_in", "mod1", "input")
	graph.map_output("external_out", "mod1", "output")

	assert graph.passthrough_inputs["external_in"] == ("mod1", "input")
	assert graph.passthrough_outputs["external_out"] == ("mod1", "output")


def test_graph_determine_proc_order_simple():
	"""Test processing order determination for simple chain."""
	graph = Graph()
	mod1 = TestModule()
	mod2 = TestModule()
	mod3 = TestModule()

	graph.add_module("mod1", mod1)
	graph.add_module("mod2", mod2)
	graph.add_module("mod3", mod3)

	graph.connect("mod1", "mod2")
	graph.connect("mod2", "mod3")

	order = graph.determine_proc_order()
	assert order == ["mod1", "mod2", "mod3"]


def test_graph_determine_proc_order_parallel():
	"""Test processing order with parallel branches."""
	graph = Graph()
	mod1 = TestModule()
	mod2 = TestModule()
	mod3 = TestModule()
	mod4 = TestModule()

	graph.add_module("mod1", mod1)
	graph.add_module("mod2", mod2)
	graph.add_module("mod3", mod3)
	graph.add_module("mod4", mod4)

	# mod1 feeds both mod2 and mod3, both feed mod4
	graph.connect("mod1", "mod2")
	graph.connect("mod1", "mod3")
	graph.connect("mod2", "mod4")
	graph.connect("mod3", "mod4")

	order = graph.determine_proc_order()
	assert order[0] == "mod1"  # mod1 must be first
	assert order[3] == "mod4"  # mod4 must be last
	assert set(order[1:3]) == {"mod2", "mod3"}  # mod2 and mod3 can be in either order


def test_graph_determine_proc_order_hierarchy():
	"""Test processing order with nested graphs."""
	# Create inner graph
	inner_graph = Graph()
	inner_mod1 = TestModule()
	inner_mod2 = TestModule()
	inner_graph.add_module("inner1", inner_mod1)
	inner_graph.add_module("inner2", inner_mod2)
	inner_graph.connect("inner1", "inner2")

	# Create outer graph
	outer_graph = Graph()
	outer_mod = TestModule()
	outer_graph.add_module("outer", outer_mod)
	outer_graph.add_module("subgraph", inner_graph)
	outer_graph.connect("outer", "subgraph")

	order = outer_graph.determine_proc_order()
	assert order == ["outer", "subgraph.inner1", "subgraph.inner2"]


def test_complex_hierarchical_proc_order():
	"""Test complex processing order with multiple hierarchy levels and various module types."""

	# Create deepest level graph (Level 2)
	deep_graph = Graph()
	source = SourceModule()
	splitter = SplitterModule()
	proc1 = TestModule()
	proc2 = TestModule()

	deep_graph.add_module("source", source)
	deep_graph.add_module("splitter", splitter)
	deep_graph.add_module("proc1", proc1)
	deep_graph.add_module("proc2", proc2)

	# Connect: source.sine -> splitter.main_in -> splits to proc1 and proc2
	deep_graph.connect("source", "splitter", "sine", "main_in")
	deep_graph.connect("splitter", "proc1", "out1", "input")
	deep_graph.connect("splitter", "proc2", "out2", "input")

	# Create middle level graph (Level 1)
	mid_graph = Graph()
	mixer = MixerModule()
	stereo_proc = MultiPortModule()

	mid_graph.add_module("deep_section", deep_graph)
	mid_graph.add_module("mixer", mixer)
	mid_graph.add_module("stereo", stereo_proc)

	# Connect deep_section outputs to mixer, then to stereo processor
	mid_graph.connect("deep_section", "mixer", "output", "input1")  # Assuming deep_graph has default output
	mid_graph.connect("mixer", "stereo", "mix_out", "left")

	# Create top level graph (Level 0)
	top_graph = Graph()
	main_source = SourceModule()
	final_mixer = MixerModule()

	top_graph.add_module("main_source", main_source)
	top_graph.add_module("mid_section", mid_graph)
	top_graph.add_module("final_mix", final_mixer)

	# Connect main_source to mid_section, then to final_mix
	top_graph.connect("main_source", "mid_section", "square", "input")
	top_graph.connect("mid_section", "final_mix", "output", "input2")

	# Get processing order
	order = top_graph.determine_proc_order()

	# Verify order constraints
	def get_position(module_name):
		return order.index(module_name)

	# Main source must be first (no dependencies)
	assert "main_source" == order[0]

	# Deep graph modules must come after main_source but before final_mix
	assert get_position("main_source") < get_position("mid_section.deep_section.source")
	assert get_position("mid_section.deep_section.source") < get_position("mid_section.deep_section.splitter")

	# Within deep graph: source -> splitter -> (proc1, proc2 in either order)
	assert get_position("mid_section.deep_section.source") < get_position("mid_section.deep_section.splitter")
	assert get_position("mid_section.deep_section.splitter") < get_position("mid_section.deep_section.proc1")
	assert get_position("mid_section.deep_section.splitter") < get_position("mid_section.deep_section.proc2")

	# Within mid graph: deep_section -> mixer -> stereo
	deep_section_max = max(get_position("mid_section.deep_section.source"),
	                      get_position("mid_section.deep_section.splitter"),
	                      get_position("mid_section.deep_section.proc1"),
	                      get_position("mid_section.deep_section.proc2"))
	assert deep_section_max < get_position("mid_section.mixer")
	assert get_position("mid_section.mixer") < get_position("mid_section.stereo")

	# Final mixer must be last
	assert "final_mix" == order[-1]

	# Check total count (should have all modules flattened)
	expected_count = 1 + 1 + 8  # main_source + final_mix + mid_section modules (4 deep + 2 mid + 2 qualified names)
	# Actually: main_source, final_mix, plus 6 qualified names from mid_section
	assert len(order) == 8  # main_source + final_mix + 6 from mid_section


if __name__ == "__main__":
	pytest.main([__file__])