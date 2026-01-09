"""
Debug script to check DawDreamer + Faust setup
"""

import dawdreamer as daw
import numpy as np

try:
    print("DawDreamer version:", daw.__version__)
except AttributeError:
    print("DawDreamer version: (version attribute not available)")

# Create engine
SAMPLE_RATE = 44100
BUFFER_SIZE = 512

print("\nCreating RenderEngine...")
engine = daw.RenderEngine(SAMPLE_RATE, BUFFER_SIZE)

# Load Faust code
print("\nLoading Faust DSP file...")
with open("faust/simple_gain.dsp", "r") as f:
    dsp_code = f.read()

print("Faust code:")
print("-" * 40)
print(dsp_code)
print("-" * 40)

# Create Faust processor
print("\nCreating Faust processor...")
faust_processor = engine.make_faust_processor("test")

print("\nSetting DSP string...")
try:
    faust_processor.set_dsp_string(dsp_code)
    print("✓ DSP string set successfully")
except Exception as e:
    print(f"✗ Error setting DSP string: {e}")
    exit(1)

# Check parameters
print("\nGetting parameter descriptions...")
try:
    params = faust_processor.get_parameters_description()
    print(f"Found {len(params)} parameters:")
    for i, param in enumerate(params):
        print(f"  [{i}] {param}")
except Exception as e:
    print(f"✗ Error getting parameters: {e}")

# Try to get parameter names differently
print("\nTrying to list parameter names...")
try:
    # Try getting the number of parameters
    n_params = faust_processor.n_parameters
    print(f"Number of parameters: {n_params}")

    # Try getting parameter info
    for i in range(n_params):
        name = faust_processor.get_parameter_name(i)
        value = faust_processor.get_parameter(i)
        print(f"  Parameter {i}: '{name}' = {value}")

except Exception as e:
    print(f"Error: {e}")

# Try setting parameter by index instead of name
print("\nTrying to set parameter by index...")
try:
    faust_processor.set_parameter(0, 0.75)
    print(f"✓ Set parameter 0 to 0.75")
    print(f"  New value: {faust_processor.get_parameter(0)}")
except Exception as e:
    print(f"✗ Error setting parameter: {e}")

# Try setting by name
print("\nTrying to set parameter by name 'gain'...")
try:
    faust_processor.set_parameter("gain", 0.5)
    print("✓ Set 'gain' to 0.5")
except Exception as e:
    print(f"✗ Error setting parameter by name: {e}")

print("\n" + "="*60)
print("Debug complete!")
