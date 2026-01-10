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
        self.dsp_file_path = dsp_file_path
        self.name = name
        self.sample_rate = 0
        self.engine = None
        self.proc = None
        self._num_inputs = 0
        self._num_outputs = 0

    def init(self, sample_rate: int) -> None:
        """Initialize Faust processor with sample rate."""
        self.sample_rate = sample_rate

        # Create DawDreamer engine for this processor
        self.engine = daw.RenderEngine(sample_rate, 512)
        self.proc = self.engine.make_faust_processor(self.name)

        # Load and compile DSP code
        with open(self.dsp_file_path, 'r') as f:
            dsp_code = f.read()
        self.proc.set_dsp_string(dsp_code)

        # Cache channel counts
        self._num_inputs = self.proc.get_num_input_channels()
        self._num_outputs = self.proc.get_num_output_channels()

    def process(self, inputs: List[np.ndarray]) -> List[np.ndarray]:
        """Process audio using DawDreamer."""
        if self.proc is None:
            raise RuntimeError("Processor not initialized. Call init() first.")

        # DawDreamer expects interleaved multichannel arrays
        # Convert list of mono arrays to multichannel array
        if len(inputs) == 1:
            input_array = inputs[0]
        else:
            input_array = np.stack(inputs, axis=1)

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
        self.proc.set_parameter(name, value)

    def get_param(self, name: str) -> float:
        """Get Faust parameter value by name."""
        if self.proc is None:
            raise RuntimeError("Processor not initialized. Call init() first.")
        # DawDreamer doesn't have direct get by name, so we'd need to track this
        # For now, raise NotImplementedError
        raise NotImplementedError("get_param not yet implemented for Faust processors")

    def get_num_inputs(self) -> int:
        """Get number of input channels."""
        return self._num_inputs

    def get_num_outputs(self) -> int:
        """Get number of output channels."""
        return self._num_outputs


class CppProcessor(AudioProcessor):
    """Wrapper for C++ processors compiled with pybind11."""

    def __init__(self, cpp_module_instance):
        """
        Create a C++ processor wrapper.

        Args:
            cpp_module_instance: Instance of pybind11-wrapped C++ class
        """
        self.cpp = cpp_module_instance

    def init(self, sample_rate: int) -> None:
        """Initialize C++ processor with sample rate."""
        self.cpp.init(sample_rate)

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
