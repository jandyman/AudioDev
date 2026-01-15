"""
Processor wrappers that provide a uniform interface for both Faust and C++ modules.
"""
import numpy as np
from abc import ABC, abstractmethod
from typing import List
import dawdreamer as daw


class AudioProcessor(ABC):
    """Base class defining the standard processor interface."""

    @abstractmethod
    def init(self, sample_rate: int) -> None:
        """Initialize processor with sample rate."""
        pass

    @abstractmethod
    def process(self, inputs: List[np.ndarray]) -> List[np.ndarray]:
        """
        Process audio buffers.

        Args:
            inputs: List of numpy arrays, one per input channel

        Returns:
            List of numpy arrays, one per output channel
        """
        pass

    @abstractmethod
    def set_param(self, name: str, value: float) -> None:
        """Set parameter value by name."""
        pass

    @abstractmethod
    def get_param(self, name: str) -> float:
        """Get parameter value by name."""
        pass

    @abstractmethod
    def get_num_inputs(self) -> int:
        """Get number of input channels."""
        pass

    @abstractmethod
    def get_num_outputs(self) -> int:
        """Get number of output channels."""
        pass


class FaustProcessor(AudioProcessor):
    """Wrapper for Faust processors using DawDreamer."""

    def __init__(self, dsp_file_path: str, name: str = "faust_proc"):
        """
        Create a Faust processor from a .dsp file.

        Args:
            dsp_file_path: Path to .dsp file
            name: Processor name (for debugging)
        """
        object.__setattr__(self, 'dsp_file_path', dsp_file_path)
        object.__setattr__(self, 'name', name)
        object.__setattr__(self, 'sample_rate', 0)
        object.__setattr__(self, 'engine', None)
        object.__setattr__(self, 'proc', None)
        object.__setattr__(self, '_num_inputs', 0)
        object.__setattr__(self, '_num_outputs', 0)
        object.__setattr__(self, '_param_names', set())
        object.__setattr__(self, '_param_values', {})  # Cache for get_param
        object.__setattr__(self, '_param_paths', {})  # Map short name to full path

    def init(self, sample_rate: int) -> None:
        """Initialize Faust processor with sample rate."""
        object.__setattr__(self, 'sample_rate', sample_rate)

        # Create DawDreamer engine for this processor
        engine = daw.RenderEngine(sample_rate, 512)
        object.__setattr__(self, 'engine', engine)

        proc = self.engine.make_faust_processor(self.name)
        object.__setattr__(self, 'proc', proc)

        # Load and compile DSP code
        with open(self.dsp_file_path, 'r') as f:
            dsp_code = f.read()
        self.proc.set_dsp_string(dsp_code)

        # Cache channel counts
        object.__setattr__(self, '_num_inputs', self.proc.get_num_input_channels())
        object.__setattr__(self, '_num_outputs', self.proc.get_num_output_channels())

        # Cache parameter names and values from DawDreamer
        param_descs = self.proc.get_parameters_description()
        param_names = set()
        param_values = {}
        param_paths = {}

        for desc in param_descs:
            # DawDreamer returns list of dicts with parameter info
            # Format: {'name': '/path/name', 'label': 'name', 'value': default_value, ...}
            if isinstance(desc, dict):
                # Use 'label' for parameter name (short name without path)
                param_name = desc.get('label', '')
                param_path = desc.get('name', '')  # Full path for set_parameter
                if param_name:
                    param_names.add(param_name)
                    # Store mapping from short name to full path
                    if param_path:
                        param_paths[param_name] = param_path
                    # Get current/default value
                    if 'value' in desc:
                        param_values[param_name] = desc['value']

        object.__setattr__(self, '_param_names', param_names)
        object.__setattr__(self, '_param_paths', param_paths)
        # Update param_values dict with initial values
        object.__getattribute__(self, '_param_values').update(param_values)

    def process(self, inputs: List[np.ndarray]) -> List[np.ndarray]:
        """Process audio using DawDreamer."""
        if self.proc is None:
            raise RuntimeError("Processor not initialized. Call init() first.")

        # DawDreamer expects shape (channels, samples)
        # Stack inputs to create multichannel array
        input_array = np.stack(inputs, axis=0)

        # Create playback processor for input
        playback = self.engine.make_playback_processor("input", input_array)

        # Set up graph and render
        graph = [(playback, []), (self.proc, ["input"])]
        self.engine.load_graph(graph)
        self.engine.render(len(inputs[0]) / self.sample_rate)

        # Get output
        output = self.proc.get_audio()

        # Convert back to list of mono arrays
        if output.ndim == 1:
            return [output]
        else:
            return [output[ch] for ch in range(output.shape[0])]

    def set_param(self, name: str, value: float) -> None:
        """Set Faust parameter by name."""
        if self.proc is None:
            raise RuntimeError("Processor not initialized. Call init() first.")
        # Use full path if available, otherwise use name directly
        param_path = self._param_paths.get(name, name)
        self.proc.set_parameter(param_path, value)
        # Cache the value for get_param
        self._param_values[name] = value

    def get_param(self, name: str) -> float:
        """Get Faust parameter value by name."""
        if self.proc is None:
            raise RuntimeError("Processor not initialized. Call init() first.")
        # Return cached value (DawDreamer doesn't provide direct get)
        if name in self._param_values:
            return self._param_values[name]
        else:
            raise ValueError(f"Parameter '{name}' not found or not yet set")

    def get_num_inputs(self) -> int:
        """Get number of input channels."""
        return self._num_inputs

    def get_num_outputs(self) -> int:
        """Get number of output channels."""
        return self._num_outputs

    def __setattr__(self, name: str, value) -> None:
        """Route parameter assignments to set_param."""
        # Check if this is a known parameter name
        if hasattr(self, '_param_names') and name in self._param_names:
            self.set_param(name, value)
        else:
            # Use object.__setattr__ to avoid infinite recursion
            object.__setattr__(self, name, value)

    def __getattr__(self, name: str):
        """Route parameter access to get_param."""
        # Check if this is a known parameter name
        if hasattr(self, '_param_names') and name in object.__getattribute__(self, '_param_names'):
            return self.get_param(name)
        # Default behavior for unknown attributes
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")


class CppProcessor(AudioProcessor):
    """Wrapper for C++ processors compiled with pybind11."""

    def __init__(self, cpp_module_instance):
        """
        Create a C++ processor wrapper.

        Args:
            cpp_module_instance: Instance of pybind11-wrapped C++ class
        """
        object.__setattr__(self, 'cpp', cpp_module_instance)
        object.__setattr__(self, '_param_names', set())

    def init(self, sample_rate: int) -> None:
        """Initialize C++ processor with sample rate."""
        self.cpp.init(sample_rate)
        # Cache parameter names after init
        object.__setattr__(self, '_param_names', set(self.cpp.get_param_names()))

    def process(self, inputs: List[np.ndarray]) -> List[np.ndarray]:
        """Process audio using C++ module."""
        return self.cpp.process(inputs)

    def set_param(self, name: str, value: float) -> None:
        """Set C++ parameter by name."""
        self.cpp.set_param(name, value)

    def get_param(self, name: str) -> float:
        """Get C++ parameter value by name."""
        return self.cpp.get_param(name)

    def get_num_inputs(self) -> int:
        """Get number of input channels."""
        return self.cpp.get_num_inputs()

    def get_num_outputs(self) -> int:
        """Get number of output channels."""
        return self.cpp.get_num_outputs()

    def __setattr__(self, name: str, value) -> None:
        """Route parameter assignments to set_param."""
        # Check if this is a known parameter name
        if hasattr(self, '_param_names') and name in self._param_names:
            self.cpp.set_param(name, value)
        else:
            # Use object.__setattr__ to avoid infinite recursion
            object.__setattr__(self, name, value)

    def __getattr__(self, name: str):
        """Route parameter access to get_param."""
        # Check if this is a known parameter name
        if hasattr(self, '_param_names') and name in object.__getattribute__(self, '_param_names'):
            return self.cpp.get_param(name)
        # Default behavior for unknown attributes
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
