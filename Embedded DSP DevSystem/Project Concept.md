# Project Concept: Audio DSP Development Ecosystem

## Top Level Project Goals

### Primary Goal
Create an ecosystem to remove the pain from developing realtime audio DSP algorithms where the target system is a small embedded processor such as a Cortex M7. Algorithm development would start in a non-realtime fashion using SciPy. Once an initial version of the algorithm is working, automated tools will minimize the coding and debugging that must be done in the target environment, which will be C++.

### Secondary Goal
Maximize the potential to reuse DSP functionality through the use of DSP Modules and DSP Graphs. In the long run, support the creation of a visual editor to create algorithm from existing blocks.

## Core Technical Approach

Unlike non-realtime development using Matlab or SciPy, realtime algorithms need to use a streaming model where small buffers of data are processed, in order to reduce latency. By mirroring this streaming/buffer model in SciPy, we create a situation where implementations can map directly from Python into C++.

## Design Constraints & Requirements

### Performance Requirements
- Low latency processing suitable for real-time audio
- Memory-efficient operation on resource-constrained embedded systems
- Deterministic execution times

### Target Platforms
- Primary: ARM Cortex M7 class processors
- Development: x86/x64 for prototyping and testing

### Development Environment
- Python/SciPy for algorithm development and testing
- C++ for embedded implementation
- Automated toolchain for code generation and validation

## Success Criteria
- Seamless transition from SciPy prototype to embedded C++ implementation
- Significant reduction in embedded development and debugging time
- High degree of code reuse through modular DSP components
- Maintainable and testable DSP processing chains

## Key Concepts

In this project vision, several entities are involved in stream based processing. Signals flow between DSP Modules which are contained in a hierarchical arrangment of DSP Graphs. After an algorithm has been proven in non real time in Python, the entire structure of the algorithm is recreated in C++ code for the embedded environment, where only the core processing function of each module needs to be created. All C++ versions of DSP Modules can be tested against the Python versions on the development system using Python interop, currently the choice for this interop laver is pybind11.

### DSP Signal
A DSP Signal is an encapsulation of audio data buffers that can be multichannel, with one buffer per channel. This provides a clean abstraction for passing audio data between DSP Modules while maintaining channel organization and data integrity.

### Signal Spec
A Signal Spec specifies the format characteristics of a DSP Signal, including the number of channels and sample rate. This allows DSP Modules to validate compatibility and configure themselves appropriately for different signal formats.

### DSP Module
A DSP Module is the fundamental building block that processes one or more DSP Signals as input and produces one or more DSP Signals as output, exactly as would occur in a streaming system. Each module encapsulates a specific DSP algorithm or processing function and operates on the buffer-based data within DSP Signals. This flexibility allows for modules that handle complex routing scenarios such as mixers, splitters, crossovers, and multi-input effects.

### DSP Graph
A DSP Graph is a network of interconnected DSP Modules that together implement complex signal processing chains. Modules are connected using either programmatic commands or potentially through automated graphical tools (though the system must not rely on graphical tools for core functionality).

**Key Benefits of DSP Graphs:**
- **Intuitive Development**: Visual/conceptual representation of signal flow matches how engineers think about processing chains
- **Maximum Reusability**: Enables fine-grained DSP Modules that can be recombined in multiple contexts
- **Modular Design**: Complex algorithms can be broken down into smaller, testable, and maintainable components
- **Flexible Topology**: Supports linear chains, parallel processing, feedback loops, and complex routing

**Hierarchical Composition**: DSP Graphs are themselves DSP Modules, enabling powerful hierarchical system design. This composition can be performed either at algorithm design time by connecting pre-built graphs as modules, or programmatically by encapsulating graph structures into reusable module interfaces. This hierarchy supports building complex, sophisticated algorithms from simpler components while maintaining the same module interface patterns throughout the system.

**Graph Construction Methods:**
- **Programmatic**: Connect modules using API calls (primary method for reliability)
- **Graphical Tools**: Future automated tools for visual graph construction (supplementary)

## Lifecycles

### Algorithm Development Lifecycle
1. Choose Modules to use
2. Organize in a Graph Hierarchy
3. Set Design Time Parameters for Models
4. Prepare Graph for Execution (detailed in Graph Preparation Design.md)
   1. Determine Processing Order
   2. Signal Spec Propagation (deferred for future implementation)
   3. Assign and allocate buffers
   4. Run init functions on all modules
5. Run algorithm on canned input
6. Is it working to expecations? If not, go to 1 or 3 above
7. Generate Graph code for embedded system
8. Build and test on embedded system, using realtime input. Should "just work".
9. Does it work on realtime data? If not, go to 1 or 3 above

### Module Development Lifecycle
1. Define Task for Module
2. Choose Design Time Parameters
3. Identify Needed State
4. Write Init and Proc function
5. Test - If it doesn't work, repeat one of the steps above
6. Generate scaffolding and interop code for C== versions.
7. Write Init and Proc Functions 
8. Test using interop (pybind11), comparing outputs to Python versions
9. Repeat as necesary
10. Build and test embedded versions (should "just work")

### System State Categories
The DSP ecosystem maintains different categories of state information, each serving distinct architectural purposes:

**Module Definition State**: Static characteristics established when DSP Modules are created, such as the number of input and output signals, processing capabilities, and configuration parameters. This state defines what a module is capable of doing.

**Graph Configuration State**: The connectivity and topology information that defines how DSP Modules are interconnected. This state establishes the signal routing and module relationships that form the overall processing network.

**Runtime Processing State**: Dynamic internal variables within DSP Modules that evolve during algorithm execution. This state represents the working memory and temporal characteristics needed for real-time processing.

This state classification enables clear separation of concerns, allows different optimization strategies for each category, and provides predictable behavior during real-time execution.

## Detailed Entity Specifications

### DSP Modules

#### Ports
DSP Modules use "ports" as named connection points to specify the number and names of their inputs and outputs. Ports provide both structural information about how many signals a module expects and semantic information through meaningful names that describe the purpose of each connection point. Each port has associated requirements that define what types of signals can be connected, enabling both design-time validation and runtime compatibility checking.

#### Design Tool Integration
Python's runtime introspection capabilities make it easy for future design tools to dynamically discover module ports and configuration parameters. Design tools can query DSP Modules to understand their capabilities and interface requirements by inspecting class variables, enabling sophisticated graphical design environments while maintaining the flexibility of programmatic graph construction.

#### Processing Model
DSP Modules follow a two-phase execution model that mirrors real-time streaming systems. An "Init" method prepares the module for processing by setting up internal state and validating configuration. A "Proc" method is then called repeatedly for each new set of input buffers, performing the actual signal processing work. This separation allows modules to perform expensive setup operations once during initialization while maintaining efficient processing during the streaming phase.

#### Types of Modules and Signal Specs
Although multichannel and multi-rate processing will eventually be supported, it is ensivsaged that most Modules will only support a single channel and a single sample rate. So it is asssumed that is the case unless otherwise specified. Other capabilities will be signaled with specific flags. Since automatic propagation of Signal Specs through an algorithm will be complex, this complexity will be addressed at a later date. For the time being, all signals are single channel, and there is one single sample rate for an entire algorithm

#### Buffers and Signals
Signals contain data passed from one Module to one or more other Modules. That data is stored in buffers. For the Python implementation, these buffers are implemented using Numpy arrays. For single channel Modules, numpy vectors are used, for multichannel signals, two dimensional arrays are used. Buffer are "owned" and updated by an output of a Module, and are consumed by one or more inputs of other modules. Signal flow is in one direction - any feeback loops are implemented only within modules, 

Before running an algorithhm, buffers must be allocated to store the date flowing in signals. For an embedded application, it may be desireable to reuse buffers during execution of an algorithm, to conserve memory space. Modules later in the processing order can use buffers that are no longer needed by Modules earlier in the procssing order. However, this is seldom needed on a modern computer development system, so in the Python world we'll let each output of each Module own a buffer for each of its outputs.

## Current Focus
Graph Preparation implementation:
1. Processing Order determination is complete
2. Signal Spec propagation is deferred (see Graph Preparation Design.md for details)
3. Buffer assignment and allocation is the current focus

**Note**: Detailed design discussions for graph preparation steps are documented in **Graph Preparation Design.md**


*This document will evolve as we develop the system interactively, capturing design decisions and architectural insights as they emerge.*

