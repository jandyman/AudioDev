"""
Unit tests for FaustProcessor and CppProcessor.

Tests both traditional set_param/get_param interface and property-based interface.
"""
import sys
import os
import pytest
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'build'))

from processors import FaustProcessor, CppProcessor


# Fixtures
@pytest.fixture
def sample_rate():
    """Standard sample rate for tests."""
    return 44100


@pytest.fixture
def test_signal(sample_rate):
    """Generate a simple test signal."""
    duration = 0.01  # 10ms
    t = np.linspace(0, duration, int(sample_rate * duration))
    return np.sin(2 * np.pi * 440 * t)  # 440 Hz sine wave


@pytest.fixture
def faust_processor(sample_rate):
    """Create and initialize a Faust processor."""
    dsp_path = os.path.join(os.path.dirname(__file__), '..', '..',
                            'faust-python-interop', 'faust', 'simple_gain.dsp')
    if not os.path.exists(dsp_path):
        pytest.skip(f"Faust DSP file not found: {dsp_path}")

    proc = FaustProcessor(dsp_path, name="test_faust")
    proc.init(sample_rate)
    return proc


@pytest.fixture
def cpp_processor(sample_rate):
    """Create and initialize a C++ processor."""
    try:
        from pybind_example_processor import ExampleProcessor
        cpp_instance = ExampleProcessor()
        proc = CppProcessor(cpp_instance)
        proc.init(sample_rate)
        return proc
    except ImportError:
        pytest.skip("C++ module not built. Run: cd build && make -f audio.make TARGET=example_processor")


# Faust Processor Tests
class TestFaustProcessor:
    """Tests for FaustProcessor."""

    def test_initialization(self, faust_processor):
        """Test processor initializes correctly."""
        assert faust_processor.get_num_inputs() == 1
        assert faust_processor.get_num_outputs() == 1

    def test_parameter_set_get_traditional(self, faust_processor):
        """Test traditional set_param/get_param interface."""
        faust_processor.set_param("gain", 0.75)
        assert faust_processor.get_param("gain") == pytest.approx(0.75)

    def test_parameter_property_interface(self, faust_processor):
        """Test property-based parameter interface."""
        faust_processor.gain = 0.5
        assert faust_processor.gain == pytest.approx(0.5)

    def test_parameter_interfaces_equivalent(self, faust_processor):
        """Test that both interfaces access the same parameter."""
        faust_processor.set_param("gain", 0.6)
        assert faust_processor.gain == pytest.approx(0.6)

        faust_processor.gain = 0.4
        assert faust_processor.get_param("gain") == pytest.approx(0.4)

    def test_default_gain_value(self, faust_processor):
        """Test default gain value from Faust DSP."""
        # simple_gain.dsp has default gain of 0.5
        assert faust_processor.gain == pytest.approx(0.5)

    def test_audio_processing_unity_gain(self, faust_processor, test_signal):
        """Test audio processing with unity gain."""
        faust_processor.gain = 1.0
        output = faust_processor.process([test_signal])
        np.testing.assert_allclose(output[0], test_signal, rtol=1e-5)

    def test_audio_processing_half_gain(self, faust_processor, test_signal):
        """Test audio processing with 0.5 gain."""
        faust_processor.gain = 0.5
        output = faust_processor.process([test_signal])
        expected = test_signal * 0.5
        np.testing.assert_allclose(output[0], expected, rtol=1e-5)

    def test_audio_processing_zero_gain(self, faust_processor, test_signal):
        """Test audio processing with zero gain."""
        faust_processor.gain = 0.0
        output = faust_processor.process([test_signal])
        expected = np.zeros_like(test_signal)
        np.testing.assert_allclose(output[0], expected, atol=1e-7)


# C++ Processor Tests
class TestCppProcessor:
    """Tests for CppProcessor."""

    def test_initialization(self, cpp_processor):
        """Test processor initializes correctly."""
        assert cpp_processor.get_num_inputs() == 1
        assert cpp_processor.get_num_outputs() == 1

    def test_parameter_names(self, cpp_processor):
        """Test parameter names are reported correctly."""
        param_names = cpp_processor.cpp.get_param_names()
        assert "gain" in param_names

    def test_parameter_set_get_traditional(self, cpp_processor):
        """Test traditional set_param/get_param interface."""
        cpp_processor.set_param("gain", 0.75)
        assert cpp_processor.get_param("gain") == pytest.approx(0.75)

    def test_parameter_property_interface(self, cpp_processor):
        """Test property-based parameter interface."""
        cpp_processor.gain = 0.5
        assert cpp_processor.gain == pytest.approx(0.5)

    def test_parameter_interfaces_equivalent(self, cpp_processor):
        """Test that both interfaces access the same parameter."""
        cpp_processor.set_param("gain", 0.6)
        assert cpp_processor.gain == pytest.approx(0.6)

        cpp_processor.gain = 0.4
        assert cpp_processor.get_param("gain") == pytest.approx(0.4)

    def test_default_gain_value(self, cpp_processor):
        """Test default gain value from C++ code."""
        # ExampleProcessor initializes gain to 1.0
        assert cpp_processor.gain == pytest.approx(1.0)

    def test_audio_processing_unity_gain(self, cpp_processor, test_signal):
        """Test audio processing with unity gain."""
        cpp_processor.gain = 1.0
        output = cpp_processor.process([test_signal])
        np.testing.assert_allclose(output[0], test_signal, rtol=1e-5)

    def test_audio_processing_half_gain(self, cpp_processor, test_signal):
        """Test audio processing with 0.5 gain."""
        cpp_processor.gain = 0.5
        output = cpp_processor.process([test_signal])
        expected = test_signal * 0.5
        np.testing.assert_allclose(output[0], expected, rtol=1e-5)

    def test_audio_processing_zero_gain(self, cpp_processor, test_signal):
        """Test audio processing with zero gain."""
        cpp_processor.gain = 0.0
        output = cpp_processor.process([test_signal])
        expected = np.zeros_like(test_signal)
        np.testing.assert_allclose(output[0], expected, atol=1e-7)

    def test_audio_processing_double_gain(self, cpp_processor, test_signal):
        """Test audio processing with 2.0 gain."""
        cpp_processor.gain = 2.0
        output = cpp_processor.process([test_signal])
        expected = test_signal * 2.0
        np.testing.assert_allclose(output[0], expected, rtol=1e-5)

    def test_invalid_parameter_name(self, cpp_processor):
        """Test that invalid parameter name raises error."""
        with pytest.raises(RuntimeError):
            cpp_processor.set_param("invalid_param", 1.0)


# Cross-processor tests
class TestProcessorUniformity:
    """Tests that both processor types behave consistently."""

    def test_both_process_identically(self, faust_processor, cpp_processor, test_signal):
        """Test that both processors produce identical output for same gain."""
        gain = 0.7

        faust_processor.gain = gain
        cpp_processor.gain = gain

        faust_output = faust_processor.process([test_signal])
        cpp_output = cpp_processor.process([test_signal])

        np.testing.assert_allclose(faust_output[0], cpp_output[0], rtol=1e-5)

    def test_both_support_property_interface(self, faust_processor, cpp_processor):
        """Test that both processors support property-based interface."""
        faust_processor.gain = 0.3
        cpp_processor.gain = 0.3

        assert faust_processor.gain == pytest.approx(0.3)
        assert cpp_processor.gain == pytest.approx(0.3)
