"""
Simple proof-of-concept DSP visual designer using PySide6.
Demonstrates a KiCAD-style schematic editor for DSP block connections.
"""

from PySide6.QtWidgets import (QApplication, QMainWindow, QGraphicsView,
                               QGraphicsScene, QGraphicsItem, QGraphicsEllipseItem,
                               QGraphicsTextItem, QToolBar, QGraphicsLineItem)
from PySide6.QtCore import Qt, QPointF, QRectF, QLineF
from PySide6.QtGui import QPen, QBrush, QColor, QPainter, QFont
import sys


class ConnectionPort(QGraphicsEllipseItem):
    """Represents an input or output port on a DSP block."""

    def __init__(self, x, y, radius, is_input, parent=None):
        super().__init__(x - radius, y - radius, radius * 2, radius * 2, parent)
        self.is_input = is_input
        self.connections = []  # List of ConnectionWire objects

        # Visual styling
        self.setBrush(QBrush(QColor(100, 200, 100) if is_input else QColor(200, 100, 100)))
        self.setPen(QPen(Qt.black, 2))
        self.setAcceptHoverEvents(True)

    def hoverEnterEvent(self, event):
        """Highlight port on hover."""
        self.setBrush(QBrush(QColor(150, 255, 150) if self.is_input else QColor(255, 150, 150)))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """Remove highlight."""
        self.setBrush(QBrush(QColor(100, 200, 100) if self.is_input else QColor(200, 100, 100)))
        super().hoverLeaveEvent(event)

    def get_center_pos(self):
        """Get the center position in scene coordinates."""
        rect = self.sceneBoundingRect()
        return QPointF(rect.center())


class ConnectionWire(QGraphicsLineItem):
    """Represents a wire connecting two ports."""

    def __init__(self, start_port, end_port=None):
        super().__init__()
        self.start_port = start_port
        self.end_port = end_port

        self.setPen(QPen(QColor(50, 50, 200), 3))
        self.setZValue(-1)  # Draw behind blocks

        self.update_position()

    def update_position(self):
        """Update wire position based on connected ports."""
        start_pos = self.start_port.get_center_pos()

        if self.end_port:
            end_pos = self.end_port.get_center_pos()
        else:
            # Temporary end position (for dragging)
            end_pos = self.line().p2()

        self.setLine(QLineF(start_pos, end_pos))

    def set_temp_end(self, pos):
        """Set temporary end position while dragging."""
        start_pos = self.start_port.get_center_pos()
        self.setLine(QLineF(start_pos, pos))


class DspBlock(QGraphicsItem):
    """Represents a DSP processing block (e.g., Filter, Gain, Mixer)."""

    def __init__(self, x, y, name, num_inputs=1, num_outputs=1):
        super().__init__()
        self.block_name = name
        self.width = 120
        self.height = 80
        self.num_inputs = num_inputs
        self.num_outputs = num_outputs

        # Make block movable
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

        self.setPos(x, y)

        # Create text label
        self.text = QGraphicsTextItem(name, self)
        self.text.setDefaultTextColor(Qt.white)
        font = QFont("Arial", 12, QFont.Bold)
        self.text.setFont(font)

        # Center text
        text_rect = self.text.boundingRect()
        self.text.setPos((self.width - text_rect.width()) / 2,
                        (self.height - text_rect.height()) / 2)

        # Create input ports
        self.input_ports = []
        port_spacing = self.height / (num_inputs + 1)
        for i in range(num_inputs):
            port = ConnectionPort(0, port_spacing * (i + 1), 6, is_input=True, parent=self)
            self.input_ports.append(port)

        # Create output ports
        self.output_ports = []
        port_spacing = self.height / (num_outputs + 1)
        for i in range(num_outputs):
            port = ConnectionPort(self.width, port_spacing * (i + 1), 6, is_input=False, parent=self)
            self.output_ports.append(port)

    def boundingRect(self):
        """Define the bounding rectangle."""
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter, option, widget):
        """Draw the block."""
        # Draw main rectangle
        painter.setBrush(QBrush(QColor(70, 70, 150)))

        # Highlight if selected
        if self.isSelected():
            painter.setPen(QPen(QColor(255, 200, 0), 3))
        else:
            painter.setPen(QPen(Qt.black, 2))

        painter.drawRoundedRect(self.boundingRect(), 5, 5)

    def itemChange(self, change, value):
        """Handle item changes (e.g., position changes)."""
        if change == QGraphicsItem.ItemPositionHasChanged:
            # Update all connected wires (only if ports are initialized)
            if hasattr(self, 'input_ports') and hasattr(self, 'output_ports'):
                for port in self.input_ports + self.output_ports:
                    for wire in port.connections:
                        wire.update_position()

        return super().itemChange(change, value)


class DspSchematicView(QGraphicsView):
    """Main view for the DSP schematic editor."""

    def __init__(self):
        super().__init__()

        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        # Set view properties
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)

        # Connection state
        self.connection_in_progress = False
        self.temp_wire = None
        self.connection_start_port = None

        # Scene background
        self.scene.setBackgroundBrush(QBrush(QColor(240, 240, 240)))

    def mousePressEvent(self, event):
        """Handle mouse press for creating connections."""
        if event.button() == Qt.LeftButton:
            item = self.itemAt(event.pos())

            # Check if clicked on a port
            if isinstance(item, ConnectionPort):
                if not self.connection_in_progress:
                    # Start a new connection from output port
                    if not item.is_input:
                        self.start_connection(item)
                        return
                else:
                    # Complete connection to input port
                    if item.is_input and item != self.connection_start_port:
                        self.complete_connection(item)
                        return

        elif event.button() == Qt.RightButton:
            # Cancel connection in progress
            if self.connection_in_progress:
                self.cancel_connection()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging connection wire."""
        if self.connection_in_progress and self.temp_wire:
            # Update temporary wire end position
            scene_pos = self.mapToScene(event.pos())
            self.temp_wire.set_temp_end(scene_pos)

        super().mouseMoveEvent(event)

    def start_connection(self, port):
        """Start creating a connection from a port."""
        self.connection_in_progress = True
        self.connection_start_port = port

        # Create temporary wire
        self.temp_wire = ConnectionWire(port)
        self.scene.addItem(self.temp_wire)

    def complete_connection(self, end_port):
        """Complete a connection to an end port."""
        if self.temp_wire:
            # Replace temporary wire with permanent connection
            self.scene.removeItem(self.temp_wire)

            wire = ConnectionWire(self.connection_start_port, end_port)
            self.scene.addItem(wire)

            # Register wire with ports
            self.connection_start_port.connections.append(wire)
            end_port.connections.append(wire)

        self.cancel_connection()

    def cancel_connection(self):
        """Cancel connection in progress."""
        if self.temp_wire:
            self.scene.removeItem(self.temp_wire)
            self.temp_wire = None

        self.connection_in_progress = False
        self.connection_start_port = None

    def wheelEvent(self, event):
        """Handle mouse wheel for zooming."""
        zoom_factor = 1.15

        if event.angleDelta().y() > 0:
            # Zoom in
            self.scale(zoom_factor, zoom_factor)
        else:
            # Zoom out
            self.scale(1 / zoom_factor, 1 / zoom_factor)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("DSP Visual Designer - Proof of Concept")
        self.setGeometry(100, 100, 1200, 800)

        # Create schematic view
        self.view = DspSchematicView()
        self.setCentralWidget(self.view)

        # Create toolbar
        self.create_toolbar()

        # Add some example blocks
        self.create_example_blocks()

    def create_toolbar(self):
        """Create toolbar with block creation buttons."""
        toolbar = QToolBar("Blocks")
        self.addToolBar(toolbar)

        # Add block creation actions
        toolbar.addAction("Add Input", lambda: self.add_block("Input", 0, 1))
        toolbar.addAction("Add Filter", lambda: self.add_block("Filter", 1, 1))
        toolbar.addAction("Add Gain", lambda: self.add_block("Gain", 1, 1))
        toolbar.addAction("Add Mixer", lambda: self.add_block("Mixer", 2, 1))
        toolbar.addAction("Add Output", lambda: self.add_block("Output", 1, 0))
        toolbar.addSeparator()
        toolbar.addAction("Clear", self.clear_scene)

    def add_block(self, block_type, num_inputs, num_outputs):
        """Add a new DSP block to the scene."""
        # Add at center of view
        center = self.view.mapToScene(self.view.viewport().rect().center())
        block = DspBlock(center.x() - 60, center.y() - 40, block_type, num_inputs, num_outputs)
        self.view.scene.addItem(block)

    def clear_scene(self):
        """Clear all items from scene."""
        self.view.scene.clear()

    def create_example_blocks(self):
        """Create some example blocks to demonstrate functionality."""
        # Create a simple signal chain
        input_block = DspBlock(50, 200, "Input", 0, 1)
        filter_block = DspBlock(250, 200, "Filter", 1, 1)
        gain_block = DspBlock(450, 200, "Gain", 1, 1)
        output_block = DspBlock(650, 200, "Output", 1, 0)

        self.view.scene.addItem(input_block)
        self.view.scene.addItem(filter_block)
        self.view.scene.addItem(gain_block)
        self.view.scene.addItem(output_block)

        # Create connections
        wire1 = ConnectionWire(input_block.output_ports[0], filter_block.input_ports[0])
        wire2 = ConnectionWire(filter_block.output_ports[0], gain_block.input_ports[0])
        wire3 = ConnectionWire(gain_block.output_ports[0], output_block.input_ports[0])

        self.view.scene.addItem(wire1)
        self.view.scene.addItem(wire2)
        self.view.scene.addItem(wire3)

        # Register connections
        input_block.output_ports[0].connections.append(wire1)
        filter_block.input_ports[0].connections.append(wire1)
        filter_block.output_ports[0].connections.append(wire2)
        gain_block.input_ports[0].connections.append(wire2)
        gain_block.output_ports[0].connections.append(wire3)
        output_block.input_ports[0].connections.append(wire3)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
