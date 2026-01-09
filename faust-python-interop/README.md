# Faust-Python Interop

Experimental project for evaluating Faust code generation and interoperability with Python tools.

## Project Structure

```
faust-python-interop/
├── faust/              # Faust DSP code (.dsp files)
├── python/             # Python tools and wrappers
├── tests/              # Test code
└── README.md           # This file
```

## Goals

- Evaluate Faust code generation capabilities
- Test interoperability between Faust-generated code and Python
- Explore Python-based DSP design and analysis tools
- Document patterns for Faust/Python workflows

## Setup

### Prerequisites

- Python 3.8+ with pip
- Faust compiler installed (`brew install faust`)
- Virtual environment with dependencies installed

### Install Dependencies

```bash
# Activate your virtual environment first, then:
pip install -r requirements.txt
```

### Quick Start

1. **Open in PyCharm:**
   - Open the `faust-python-interop/` folder
   - Make sure your virtual environment (with dawdreamer) is selected

2. **Run the example:**
   ```bash
   python example_dawdreamer.py
   ```

   This will:
   - Load `faust/simple_gain.dsp`
   - Process audio with different gain values
   - Generate a plot showing the results
   - Save the plot to `faust_gain_test.png`

## Example Files

- **`faust/simple_gain.dsp`** - Simple Faust gain processor
- **`example_dawdreamer.py`** - DawDreamer example showing Faust integration

## Status

✅ Initial setup complete
✅ Example Faust DSP file created
✅ DawDreamer integration example ready
