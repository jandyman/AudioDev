"""
Simple audio processing graph system.

Supports connecting processors in series or parallel with validation.
Includes capture mode for inspecting intermediate signals and chunked
processing for testing state management.
"""
import numpy as np
from typing import List, Tuple, Dict, Optional
from .processors import AudioProcessor


class AudioGraph:
    """
    Audio graph that processes buffers through a chain of processors.

    Uses a flat channel model: all signals are mono buffers, multichannel
    is represented as multiple parallel mono signals.

    Features:
    - Named processors for easy access
    - Optional intermediate signal capture for debugging
    - Chunked processing to test state management
    """

    def __init__(self, sample_rate: int, capture_intermediates: bool = False):
        """
        Create an audio graph.

        Args:
            sample_rate: Sample rate for all processors
            capture_intermediates: If True, store all intermediate signals
        """
        self.sample_rate = sample_rate
        self.processors: Dict[str, AudioProcessor] = {}
        self.processor_order: List[str] = []
        self.capture_intermediates = capture_intermediates
        self.captured_signals: Dict[str, List[List[np.ndarray]]] = {}

    def add_processor(self, name: str, processor: AudioProcessor) -> None:
        """
        Add a named processor to the graph.

        Args:
            name: Unique name for this processor
            processor: AudioProcessor instance

        Raises:
            ValueError: If name already exists
        """
        if name in self.processors:
            raise ValueError(f"Processor '{name}' already exists in graph")

        processor.init(self.sample_rate)
        self.processors[name] = processor
        self.processor_order.append(name)

    def process_serial(
        self,
        input_signal: np.ndarray,
        chunk_size: Optional[int] = None
    ) -> np.ndarray:
        """
        Process signal through all processors in series.

        Args:
            input_signal: Input audio buffer (mono or multichannel)
            chunk_size: If set, process in chunks of this size (for testing
                       state management). If None, process entire buffer at once.

        Returns:
            Processed audio buffer

        Example:
            # Process entire file at once
            output = graph.process_serial(input_signal)

            # Process in 512-sample chunks (tests state management)
            output = graph.process_serial(input_signal, chunk_size=512)
        """
        if chunk_size is None:
            # Process entire buffer at once
            return self._process_buffer(input_signal)
        else:
            # Process in chunks, accumulate results
            return self._process_chunked(input_signal, chunk_size)

    def _process_buffer(self, signal: np.ndarray) -> np.ndarray:
        """Process a single buffer through the graph."""
        # Convert to list of channels
        if signal.ndim == 1:
            signals = [signal]
        else:
            signals = [signal[ch] for ch in range(signal.shape[0])]

        # Process through each processor in order
        for name in self.processor_order:
            proc = self.processors[name]

            # Validate channel counts
            if len(signals) != proc.get_num_inputs():
                raise ValueError(
                    f"Channel mismatch at '{name}': processor expects "
                    f"{proc.get_num_inputs()} inputs but got {len(signals)}"
                )

            # Process
            signals = proc.process(signals)

            # Optionally capture intermediate results
            if self.capture_intermediates:
                if name not in self.captured_signals:
                    self.captured_signals[name] = []
                # Store copy of signals (deep copy to avoid aliasing)
                self.captured_signals[name].append(
                    [sig.copy() for sig in signals]
                )

        # Convert back to numpy array
        if len(signals) == 1:
            return signals[0]
        else:
            return np.stack(signals, axis=0)

    def _process_chunked(
        self,
        signal: np.ndarray,
        chunk_size: int
    ) -> np.ndarray:
        """Process signal in chunks, accumulating full results."""
        # Clear captured signals for fresh start
        if self.capture_intermediates:
            self.captured_signals.clear()

        # Process signal in chunks
        total_samples = signal.shape[-1] if signal.ndim > 1 else len(signal)
        outputs = []

        for start in range(0, total_samples, chunk_size):
            end = min(start + chunk_size, total_samples)

            # Extract chunk
            if signal.ndim == 1:
                chunk = signal[start:end]
            else:
                chunk = signal[:, start:end]

            # Process chunk
            output_chunk = self._process_buffer(chunk)
            outputs.append(output_chunk)

        # Concatenate chunks
        if signal.ndim == 1:
            return np.concatenate(outputs)
        else:
            return np.concatenate(outputs, axis=1)

    def get_captured_signal(
        self,
        processor_name: str,
        channel: int = 0
    ) -> np.ndarray:
        """
        Get captured intermediate signal from a processor.

        Args:
            processor_name: Name of processor
            channel: Channel index (default 0)

        Returns:
            Concatenated signal across all chunks

        Raises:
            RuntimeError: If capture mode not enabled
            ValueError: If processor name not found

        Example:
            graph = AudioGraph(44100, capture_intermediates=True)
            graph.add_processor("gain", gain_proc)
            output = graph.process_serial(input_signal, chunk_size=512)
            gain_output = graph.get_captured_signal("gain", channel=0)
        """
        if not self.capture_intermediates:
            raise RuntimeError(
                "Capture mode not enabled. Create graph with "
                "capture_intermediates=True"
            )

        if processor_name not in self.captured_signals:
            raise ValueError(f"Processor '{processor_name}' not found")

        # Concatenate all chunks for this channel
        chunks = self.captured_signals[processor_name]
        return np.concatenate([chunk[channel] for chunk in chunks])

    def get_all_captured_signals(self) -> Dict[str, List[np.ndarray]]:
        """
        Get all captured signals.

        Returns:
            Dict mapping processor names to list of channel arrays.
            Each processor maps to a list where each element is a numpy
            array for one channel, with all chunks concatenated.

        Raises:
            RuntimeError: If capture mode not enabled

        Example:
            all_signals = graph.get_all_captured_signals()
            for name, channels in all_signals.items():
                print(f"{name}: {len(channels)} channels")
                plt.plot(channels[0], label=name)
        """
        if not self.capture_intermediates:
            raise RuntimeError(
                "Capture mode not enabled. Create graph with "
                "capture_intermediates=True"
            )

        result = {}
        for name in self.processor_order:
            if name in self.captured_signals:
                chunks = self.captured_signals[name]
                num_channels = len(chunks[0])

                # Concatenate each channel across all chunks
                result[name] = [
                    np.concatenate([chunk[ch] for chunk in chunks])
                    for ch in range(num_channels)
                ]

        return result

    def clear(self):
        """Remove all processors from the graph."""
        self.processors.clear()
        self.processor_order.clear()
        self.captured_signals.clear()


class AudioGraphParallel:
    """
    More advanced graph supporting arbitrary routing.

    TODO: Implement parallel routing, mixers, splits, etc.
    For now, use AudioGraph for simple serial chains.
    """
    pass
