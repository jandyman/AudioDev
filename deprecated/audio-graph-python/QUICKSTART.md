# Quick Start Guide

Get up and running with the audio graph system in 5 minutes.

## 1. Install Dependencies

```bash
cd audio-graph-python
pip install -r requirements.txt
```

## 2. Build the Example C++ Module

```bash
cd build
make -f audio.make TARGET=example_processor
cd ..
```

You should see:
```
Built pybind_example_processor.cpython-312-darwin.so
Import with: from build.pybind_example_processor import *
```

## 3. Run Tests

```bash
python tests/test_example.py
```

Expected output:
```
=== Testing Faust Processor ===
Faust processor initialized
  Inputs: 1
  Outputs: 1
  Gain set to: 0.5
  ✓ Output matches expected (gain applied correctly)

=== Testing C++ Processor ===
C++ processor initialized
  Inputs: 1
  Outputs: 1
  Parameters: ['gain']
  Gain set to: 0.75
  ✓ Output matches expected (gain applied correctly)

=== Testing Serial Graph ===
Graph created with 2 processors
  Processor 1 gain: 0.5
  Processor 2 gain: 0.8
  Expected total gain: 0.4
  ✓ Serial processing correct (0.5 × 0.8 = 0.4)

=== Visualization Example ===
  ✓ Visualization saved to test_output.png

All tests completed!
```

## 4. Try It Yourself

Create a simple script `my_test.py`:

```python
import sys
import numpy as np

sys.path.insert(0, 'python')
sys.path.insert(0, 'build')

from python import AudioGraph, CppProcessor
from pybind_example_processor import ExampleProcessor

# Create graph
graph = AudioGraph(sample_rate=44100)

# Add processor
proc = CppProcessor(ExampleProcessor())
graph.add_processor(proc)

# Set parameter
proc.set_param("gain", 0.5)

# Generate test signal
t = np.linspace(0, 0.1, 4410)
signal = np.sin(2 * np.pi * 440 * t)

# Process
output = graph.process_serial(signal)

print(f"Input peak: {np.max(np.abs(signal)):.3f}")
print(f"Output peak: {np.max(np.abs(output)):.3f}")
print(f"Gain applied: {np.max(np.abs(output)) / np.max(np.abs(signal)):.3f}")
```

Run it:
```bash
python my_test.py
```

## 5. Create Your Own C++ Module

1. Copy the example files:
```bash
cd cpp_modules
cp example_processor.h my_processor.h
cp example_processor.cpp my_processor.cpp
cp pybind_example_processor.cpp pybind_my_processor.cpp
```

2. Edit the files to implement your DSP

3. Build:
```bash
cd ../build
make -f audio.make TARGET=my_processor
```

4. Use in Python:
```python
from build.pybind_my_processor import MyProcessor
from python import CppProcessor

proc = CppProcessor(MyProcessor())
```

## 6. Use Faust Modules

No build step needed - just create a `.dsp` file:

```faust
// my_filter.dsp
import("stdfaust.lib");

freq = hslider("frequency", 1000, 20, 20000, 1);
q = hslider("q", 1.0, 0.1, 10.0, 0.1);

process = fi.resonlp(freq, q, 1);
```

Use it:

```python
from python import FaustProcessor

filter = FaustProcessor("faust_modules/my_filter.dsp")
filter.init(44100)
filter.set_param("frequency", 2000)
filter.set_param("q", 2.0)

output = filter.process([input_signal])
```

## Next Steps

- Read the main [README.md](README.md) for architecture details
- Look at the example processor code to understand the pattern
- Start building your algorithm incrementally!
