"""
Example: Generate and run audio graph from specification file.

This demonstrates loading a .graph spec file and automatically generating
the equivalent Python code to create and run the graph.
"""
import sys
import os
import re
import numpy as np
import matplotlib.pyplot as plt

# Add modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'build'))

from python import CppProcessor, FaustProcessor, AudioGraph


def parse_graph_spec(spec_path):
    """
    Parse a .graph specification file.

    Returns:
        dict with keys: 'processors', 'routing', 'parameters'
    """
    with open(spec_path, 'r') as f:
        content = f.read()

    result = {
        'processors': {},
        'routing': [],
        'parameters': {}
    }

    current_section = None

    for line in content.split('\n'):
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith('#'):
            # Check for section headers
            if line.startswith('## '):
                section_name = line[3:].strip().lower()
                current_section = section_name
            continue

        # Parse based on current section
        if current_section == 'processors':
            # Format: name: type
            match = re.match(r'(\w+):\s*(.+)', line)
            if match:
                name, proc_type = match.groups()
                result['processors'][name] = proc_type.strip()

        elif current_section == 'routing':
            # Format: source -> dest
            match = re.match(r'(\w+)\s*->\s*(\w+)', line)
            if match:
                source, dest = match.groups()
                result['routing'].append((source, dest))

        elif current_section == 'parameters':
            # Format: processor.param = value
            match = re.match(r'(\w+)\.(\w+)\s*=\s*(.+)', line)
            if match:
                processor, param, value = match.groups()
                if processor not in result['parameters']:
                    result['parameters'][processor] = {}
                result['parameters'][processor][param] = float(value)

    return result


def generate_graph_from_spec(spec, sample_rate=44100):
    """
    Generate an AudioGraph from parsed specification.

    Args:
        spec: Parsed graph specification dict
        sample_rate: Sample rate for the graph

    Returns:
        Configured AudioGraph instance
    """
    graph = AudioGraph(sample_rate, capture_intermediates=True)

    # Keep track of created processors for reference
    processors = {}

    # Determine processor order from routing
    # For now, simple serial chain assumed
    # Extract processors in routing order
    processor_order = []
    for source, dest in spec['routing']:
        if source != 'input' and source not in processor_order:
            processor_order.append(source)
        if dest != 'output' and dest not in processor_order:
            processor_order.append(dest)

    print(f"\nCreating processors in order: {processor_order}")

    # Create and add processors
    for proc_name in processor_order:
        proc_type = spec['processors'][proc_name]

        print(f"  Creating {proc_name}: {proc_type}")

        # Determine processor type and create instance
        if proc_type.endswith('.dsp'):
            # Faust processor
            dsp_path = os.path.join(os.path.dirname(__file__), '..',
                                    'faust-python-interop', 'faust', proc_type)
            if not os.path.exists(dsp_path):
                raise FileNotFoundError(f"Faust DSP not found: {dsp_path}")
            processor = FaustProcessor(dsp_path, name=proc_name)

        elif proc_type.endswith('()'):
            # C++ processor (class instantiation)
            class_name = proc_type[:-2]  # Remove ()

            # Import the C++ module dynamically
            try:
                from pybind_example_processor import ExampleProcessor
                if class_name == 'ExampleProcessor':
                    cpp_instance = ExampleProcessor()
                    processor = CppProcessor(cpp_instance)
                else:
                    raise ValueError(f"Unknown C++ class: {class_name}")
            except ImportError:
                raise ImportError("C++ module not built. Run: cd build && make -f audio.make TARGET=example_processor")

        else:
            raise ValueError(f"Unknown processor type: {proc_type}")

        # Add to graph
        graph.add_processor(proc_name, processor)
        processors[proc_name] = processor

    # Set parameters
    print(f"\nSetting parameters:")
    for proc_name, params in spec['parameters'].items():
        for param_name, value in params.items():
            print(f"  {proc_name}.{param_name} = {value}")
            # Use property interface
            setattr(graph.processors[proc_name], param_name, value)

    return graph, processor_order


def main():
    print("Cascading from Graph Specification")
    print("=" * 60)

    # Load and parse graph spec
    spec_path = "cascade.graph"
    print(f"\nLoading graph spec: {spec_path}")
    spec = parse_graph_spec(spec_path)

    print(f"\nParsed specification:")
    print(f"  Processors: {list(spec['processors'].keys())}")
    print(f"  Routing: {spec['routing']}")
    print(f"  Parameters: {spec['parameters']}")

    # Generate graph from spec
    sample_rate = 44100
    graph, processor_order = generate_graph_from_spec(spec, sample_rate)

    print(f"\n✅ Graph created from specification!")

    # Verify configuration matches spec
    print(f"\nVerifying configuration:")
    for proc_name, params in spec['parameters'].items():
        for param_name, expected_value in params.items():
            actual_value = getattr(graph.processors[proc_name], param_name)
            match = "✓" if abs(actual_value - expected_value) < 0.01 else "✗"
            print(f"  {match} {proc_name}.{param_name} = {actual_value:.4f} (expected {expected_value})")

    # Generate test signal
    duration = 0.1
    t = np.linspace(0, duration, int(sample_rate * duration))
    test_signal = np.sin(2 * np.pi * 440 * t)

    print(f"\nProcessing test signal...")
    output = graph.process_serial(test_signal)

    # Calculate expected gain
    expected_gain = 1.0
    for proc_name, params in spec['parameters'].items():
        if 'gain' in params:
            expected_gain *= params['gain']

    expected_output = test_signal * expected_gain
    max_error = np.max(np.abs(output - expected_output))

    print(f"\nResults:")
    print(f"  Expected total gain: {expected_gain}")
    print(f"  Output max: {np.max(np.abs(output)):.4f}")
    print(f"  Expected max: {np.max(np.abs(expected_output)):.4f}")
    print(f"  Max error: {max_error:.2e}")

    if max_error < 1e-5:
        print(f"  ✅ Generated graph working correctly!")
    else:
        print(f"  ❌ Unexpected error!")

    # Get intermediate signals
    print(f"\nIntermediate signals:")
    for proc_name in processor_order:
        signal = graph.get_captured_signal(proc_name, channel=0)
        print(f"  {proc_name} output max: {np.max(np.abs(signal)):.4f}")

    # Visualize
    plot_samples = 200
    num_plots = 2 + len(processor_order)  # input + processors + output
    fig, axes = plt.subplots(num_plots, 1, figsize=(12, 2*num_plots))
    fig.suptitle("Graph Generated from Specification: cascade.graph")

    # Input
    axes[0].plot(t[:plot_samples] * 1000, test_signal[:plot_samples], 'b-', linewidth=1.5)
    axes[0].set_ylabel('Input\nAmplitude')
    axes[0].grid(True, alpha=0.3)
    axes[0].set_ylim(-1.1, 1.1)
    axes[0].axhline(y=0, color='k', linewidth=0.5, alpha=0.3)

    # Intermediate signals
    colors = ['green', 'orange', 'purple', 'brown']
    for i, proc_name in enumerate(processor_order):
        signal = graph.get_captured_signal(proc_name, channel=0)
        proc_type = spec['processors'][proc_name]
        params = spec['parameters'].get(proc_name, {})

        label = f"{proc_name} ({proc_type})"
        if params:
            param_str = ", ".join([f"{k}={v}" for k, v in params.items()])
            label += f"\n{param_str}"

        axes[i+1].plot(t[:plot_samples] * 1000, signal[:plot_samples],
                      color=colors[i % len(colors)], linewidth=1.5)
        axes[i+1].set_ylabel(f'{proc_name}\nAmplitude')
        axes[i+1].grid(True, alpha=0.3)
        axes[i+1].set_ylim(-1.1, 1.1)
        axes[i+1].axhline(y=0, color='k', linewidth=0.5, alpha=0.3)
        axes[i+1].text(0.02, 0.95, label, transform=axes[i+1].transAxes,
                      verticalalignment='top', fontsize=9,
                      bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # Final output
    axes[-1].plot(t[:plot_samples] * 1000, output[:plot_samples], 'r-', linewidth=1.5)
    axes[-1].set_ylabel('Final Output\nAmplitude')
    axes[-1].set_xlabel('Time (ms)')
    axes[-1].grid(True, alpha=0.3)
    axes[-1].set_ylim(-1.1, 1.1)
    axes[-1].axhline(y=0, color='k', linewidth=0.5, alpha=0.3)
    axes[-1].text(0.02, 0.95, f'total gain = {expected_gain}', transform=axes[-1].transAxes,
                 verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.5))

    plt.tight_layout()
    output_path = 'cascade_from_spec.png'
    plt.savefig(output_path, dpi=150)
    print(f"\n✅ Visualization saved to {output_path}")


if __name__ == "__main__":
    main()
    print("\n" + "=" * 60)
    print("Example complete!")
