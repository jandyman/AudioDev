#!/bin/bash

# Setup script for gain~ Max external project
# This generates the Xcode project from CMake

echo "Setting up gain~ Max external project..."

# Create build directory
mkdir -p build
cd build

# Generate Xcode project
echo "Generating Xcode project..."
cmake -G Xcode ..

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Xcode project generated successfully!"
    echo ""
    echo "Next steps:"
    echo "  1. Open build/gain_tilde.xcodeproj in Xcode"
    echo "  2. Build the project (Cmd+B)"
    echo "  3. The compiled gain~.mxo will be in build/externals/"
    echo "  4. Copy it to ~/Documents/Max 8/Library/ to use in Max"
    echo ""
else
    echo ""
    echo "✗ Error generating Xcode project"
    echo "Please check that the Max SDK path in CMakeLists.txt is correct"
    exit 1
fi
