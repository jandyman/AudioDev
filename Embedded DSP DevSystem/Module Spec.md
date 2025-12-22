# Module Specification

## Overview
This document provides detailed specifications for classes in the DSP module framework, intended to guide code generation and implementation.

For architectural context and design rationale, see:
- **Project Concept.md**: High-level goals and concepts
- **Graph Preparation Design.md**: Design details for processing order, signal specs, and buffer allocation

## Module Class

### Purpose
The Module class serves as the base class for all DSP processing modules in the system. It defines the standard interface for signal processing, port management, and execution lifecycle.

### Class Definition
- **Namespace**: `module`
- **Class Name**: `Module`
- **Type**: Abstract base class

### Ports
- **Input Ports**: Class variable list of strings naming input connection points
- **Output Ports**: Class variable list of strings naming output connection points
- **Default Ports**: ["input"] for inputs, ["output"] for outputs

### Core Methods

**__init__(name=None)**
- Initialize module with optional custom name
- Auto-generates name in format "classname_N" if none provided (e.g., "testmodule_1")
- Increments class-level instance counter for unique naming
- Sets parent_graph pointer to None initially

**init()**
- Prepare module for processing
- Default implementation does nothing
- Override in subclasses for module-specific initialization
- Called once before processing begins

**proc(inputs)**
- Process input signals and generate output signals
- Called repeatedly for each processing cycle
- Must handle the streaming buffer model
- Default implementation raises NotImplementedError
- Returns output signals based on current inputs

**pathname()**
- Returns full hierarchical pathname from top-level graph
- Recursively walks up parent_graph chain
- Format: "top_graph.sub_graph.module_name"
- Uses actual instance names, not internal graph keys

**reset_instance_count()** (class method)
- Resets instance counter for the class (useful for testing)

### State Management
- **Configuration State**: Set during module creation, immutable during processing
- **Processing State**: Internal variables that evolve during proc() calls
- **Hierarchy State**: Parent graph reference for pathname generation

### Naming and Identity
- **Instance Names**: Auto-generated or custom names for debugging/identification
- **Instance Counting**: Per-class counters for unique auto-generated names
- **Hierarchical Pathnames**: Full paths showing containment hierarchy

### Introspection Support
- Port names accessible as class variables for easy discovery
- Support for Python's inspection capabilities to query module interface

## Graph Class

### Purpose
The Graph class serves as a container for DSP modules and manages the connections between their ports. It coordinates the execution of multiple modules in a processing network.

### Class Definition
- **Namespace**: `module`
- **Class Name**: `Graph`
- **Type**: Concrete class (also inherits from Module for hierarchical composition)

### Graph Port Model
- **External Ports**: Standard input/output ports for connections to other modules (inherited from Module)
- **Internal Passthrough Ports**: Corresponding internal connection points that route external signals to/from contained modules
- **Passthrough Mapping**: Each external port has a corresponding internal connection to a contained module or graph
- **Connection Records**: Graph maintains records of both external and internal passthrough connections for maintenance operations

### Container Functionality
- **Module Storage**: Contains zero or more Module instances
- **Connection Tracking**: Maintains information about port connections between contained modules
- **Module Management**: Methods for adding and accessing contained modules

### Connection Management
- **Add Connections**: Method to connect an output port of one module to an input port of another module
- **Remove Connections**: Method to disconnect ports (for design tool support)
- **Connection Validation**: Ensure connections are between valid ports of contained modules
- **Connection Queries**: Methods to inspect current connections

### Core Methods

**add_module(name, module)**
- Add a module to the graph with given internal name
- Module becomes part of the processing network
- Sets module's parent_graph pointer to this graph

**connect(source_module, dest_module, source_port="output", dest_port="input")**
- Create connection from source module's output port to destination module's input port
- Validate that both modules exist in graph and ports are valid
- Default ports are "output" and "input" for convenience

**disconnect(source_module, source_port, dest_module, dest_port)**
- Remove connection between specified ports
- Support for design tool modification workflows

**map_input(external_port, module_name, module_port)**
- Map external graph input port to internal module port

**map_output(external_port, module_name, module_port)**
- Map external graph output port to internal module port

**determine_proc_order()**
- Analyze connection dependencies to determine module execution order
- Returns list of qualified module names in dependency order
- Handles hierarchical graphs by flattening to qualified names (e.g., "subgraph.module")
- Modules can only run after all modules feeding their inputs have completed
- Uses topological sort algorithm to handle complex dependency graphs
- Detects and reports circular dependencies

### Debug and Inspection Methods

**pretty_print()**
- Returns formatted string showing hierarchical structure
- Shows module names and types in tree format
- Clean view without connection information

**pretty_print_with_connections()**
- Returns formatted string showing hierarchy with inline connection display
- Shows signal flow with "→ port connects to: destination" format
- Useful for understanding signal routing

**pretty_print_proc_order()**
- Returns formatted string showing processing order with full pathnames
- Uses module pathname() method to show hierarchical locations
- Format: "N. full.pathname (ModuleClass)"

### Graph Execution
- **Processing Order**: Determine execution sequence of contained modules
- **Data Flow**: Coordinate signal passing between connected modules
- **Initialization**: Initialize all contained modules before processing begins
- **Hierarchical Processing**: Support for nested graphs with qualified naming