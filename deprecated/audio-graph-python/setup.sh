#!/bin/bash
# Setup script for audio-graph-python

set -e  # Exit on error

echo "========================================="
echo "Audio Graph Python - Setup"
echo "========================================="
echo ""

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found. Please install Python 3."
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"
echo ""

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Build example C++ module
echo "Building example C++ module..."
cd build
make -f audio.make TARGET=example_processor
cd ..
echo "✓ Example module built"
echo ""

# Run tests
echo "Running tests..."
python tests/test_example.py
echo ""

echo "========================================="
echo "Setup complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  - Read QUICKSTART.md for usage examples"
echo "  - Look at tests/test_example.py for code samples"
echo "  - Start building your audio processors!"
echo ""
