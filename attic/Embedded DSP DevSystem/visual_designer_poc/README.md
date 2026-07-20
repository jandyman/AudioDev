# DSP Visual Designer - Proof of Concept

A simple proof-of-concept schematic editor for DSP blocks using PySide6.

## Features Demonstrated

- **Drag-and-drop DSP blocks** - Move blocks around the canvas
- **Connection ports** - Input (green) and output (red) ports on blocks
- **Wire connections** - Click and drag from output to input ports to create connections
- **Zoom/pan** - Mouse wheel to zoom, drag to pan (when not on a block)
- **Block selection** - Click to select blocks (highlighted in yellow)
- **Toolbar** - Add different DSP block types dynamically

## Usage

### Installation

```bash
pip install PySide6
```

### Running

```bash
python dsp_visual_editor.py
```

### Controls

- **Left-click on output port (red)** - Start creating a connection
- **Left-click on input port (green)** - Complete the connection
- **Right-click** - Cancel connection in progress
- **Left-click and drag block** - Move block
- **Mouse wheel** - Zoom in/out
- **Toolbar buttons** - Add new blocks of different types

## What This Demonstrates

### Qt's QGraphicsView Framework

This POC shows how Qt's graphics framework provides:

1. **Scene graph management** - All items managed in a scene
2. **Built-in transformations** - Zoom, pan, rotate
3. **Item interactions** - Selection, movement, hover effects
4. **Custom graphics items** - Easy to create custom DSP blocks
5. **Connection management** - Wires automatically update when blocks move

### Key Classes

- `DspBlock` - Represents a DSP processing block with configurable inputs/outputs
- `ConnectionPort` - Input/output ports on blocks
- `ConnectionWire` - Visual connection between ports
- `DspSchematicView` - Main view with interaction handling
- `MainWindow` - Application window with toolbar

## Next Steps for Full Implementation

1. **Block library** - Map to your actual DSP block types
2. **Properties panel** - Edit block parameters (filter coefficients, gain values, etc.)
3. **Serialization** - Save/load diagrams (JSON or XML)
4. **Code generation** - Generate Python DSP graph from visual diagram
5. **Validation** - Check for cycles, type compatibility, etc.
6. **Enhanced routing** - Orthogonal wire routing, better aesthetics
7. **Undo/redo** - QUndoStack for operation history
8. **Copy/paste** - Block duplication
9. **Grid snapping** - Align blocks to grid

## Architecture Benefits

The separation between visual representation (Qt graphics items) and underlying DSP logic makes it easy to:

- Generate DSP execution graphs from the visual representation
- Load existing DSP configurations into the visual editor
- Validate connections based on signal types (mono/stereo, sample rate, etc.)
- Export to your Python DSP framework or embedded C++ code
