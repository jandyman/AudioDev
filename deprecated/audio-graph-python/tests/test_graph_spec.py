"""
Unit tests for graph specification parsing and generation.

Tests the .graph file format parser and automatic graph generation.
"""
import sys
import os
import pytest
import tempfile
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import the spec parser from example_from_spec
# In production, this would be in a proper module
import example_from_spec


@pytest.fixture
def simple_spec_file():
    """Create a temporary simple spec file for testing."""
    content = """# Simple test graph
## Processors
gain1: ExampleProcessor()
gain2: simple_gain.dsp

## Routing
input -> gain1
gain1 -> gain2
gain2 -> output

## Parameters
gain1.gain = 0.5
gain2.gain = 0.8
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.graph', delete=False) as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    # Cleanup
    os.unlink(temp_path)


@pytest.fixture
def sample_rate():
    """Standard sample rate for tests."""
    return 44100


@pytest.fixture
def test_signal(sample_rate):
    """Generate a simple test signal."""
    duration = 0.01  # 10ms
    t = np.linspace(0, duration, int(sample_rate * duration))
    return np.sin(2 * np.pi * 440 * t)


class TestGraphSpecParser:
    """Tests for the graph specification parser."""

    def test_parse_processors(self, simple_spec_file):
        """Test parsing processor declarations."""
        spec = example_from_spec.parse_graph_spec(simple_spec_file)

        assert 'gain1' in spec['processors']
        assert 'gain2' in spec['processors']
        assert spec['processors']['gain1'] == 'ExampleProcessor()'
        assert spec['processors']['gain2'] == 'simple_gain.dsp'

    def test_parse_routing(self, simple_spec_file):
        """Test parsing routing connections."""
        spec = example_from_spec.parse_graph_spec(simple_spec_file)

        assert len(spec['routing']) == 3
        assert ('input', 'gain1') in spec['routing']
        assert ('gain1', 'gain2') in spec['routing']
        assert ('gain2', 'output') in spec['routing']

    def test_parse_parameters(self, simple_spec_file):
        """Test parsing parameter assignments."""
        spec = example_from_spec.parse_graph_spec(simple_spec_file)

        assert 'gain1' in spec['parameters']
        assert 'gain2' in spec['parameters']
        assert spec['parameters']['gain1']['gain'] == 0.5
        assert spec['parameters']['gain2']['gain'] == 0.8

    def test_ignore_comments(self, simple_spec_file):
        """Test that comments are properly ignored."""
        spec = example_from_spec.parse_graph_spec(simple_spec_file)
        # Should parse successfully despite comments
        assert len(spec['processors']) == 2

    def test_empty_file(self):
        """Test parsing an empty file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.graph', delete=False) as f:
            f.write("")
            temp_path = f.name

        try:
            spec = example_from_spec.parse_graph_spec(temp_path)
            assert spec['processors'] == {}
            assert spec['routing'] == []
            assert spec['parameters'] == {}
        finally:
            os.unlink(temp_path)


class TestGraphGeneration:
    """Tests for generating graphs from specifications."""

    def test_create_graph_from_spec(self, simple_spec_file, sample_rate):
        """Test creating a graph from a spec file."""
        spec = example_from_spec.parse_graph_spec(simple_spec_file)

        try:
            graph, processor_order = example_from_spec.generate_graph_from_spec(spec, sample_rate)

            assert 'gain1' in graph.processors
            assert 'gain2' in graph.processors
            assert processor_order == ['gain1', 'gain2']
        except ImportError:
            pytest.skip("C++ module or Faust DSP not available")

    def test_parameters_applied_correctly(self, simple_spec_file, sample_rate):
        """Test that parameters from spec are applied to processors."""
        spec = example_from_spec.parse_graph_spec(simple_spec_file)

        try:
            graph, _ = example_from_spec.generate_graph_from_spec(spec, sample_rate)

            assert graph.processors['gain1'].gain == pytest.approx(0.5)
            assert graph.processors['gain2'].gain == pytest.approx(0.8)
        except ImportError:
            pytest.skip("C++ module or Faust DSP not available")

    def test_processor_order_from_routing(self, simple_spec_file, sample_rate):
        """Test that processor order is derived correctly from routing."""
        spec = example_from_spec.parse_graph_spec(simple_spec_file)

        try:
            graph, processor_order = example_from_spec.generate_graph_from_spec(spec, sample_rate)

            # Order should be: gain1 -> gain2 based on routing
            assert processor_order.index('gain1') < processor_order.index('gain2')
        except ImportError:
            pytest.skip("C++ module or Faust DSP not available")


class TestGraphExecution:
    """Tests for executing graphs generated from specs."""

    def test_cascade_processing(self, simple_spec_file, sample_rate, test_signal):
        """Test that cascaded processing produces correct output."""
        spec = example_from_spec.parse_graph_spec(simple_spec_file)

        try:
            graph, _ = example_from_spec.generate_graph_from_spec(spec, sample_rate)

            # Process signal through cascade
            output = graph.process_serial(test_signal)

            # Expected: input * 0.5 * 0.8 = input * 0.4
            expected = test_signal * 0.4

            np.testing.assert_allclose(output, expected, rtol=1e-5)
        except ImportError:
            pytest.skip("C++ module or Faust DSP not available")

    def test_intermediate_signal_capture(self, simple_spec_file, sample_rate, test_signal):
        """Test that intermediate signals can be captured."""
        spec = example_from_spec.parse_graph_spec(simple_spec_file)

        try:
            graph, _ = example_from_spec.generate_graph_from_spec(spec, sample_rate)

            # Process signal
            output = graph.process_serial(test_signal)

            # Check intermediate signals
            gain1_output = graph.get_captured_signal('gain1', channel=0)
            gain2_output = graph.get_captured_signal('gain2', channel=0)

            # gain1 should be input * 0.5
            expected_gain1 = test_signal * 0.5
            np.testing.assert_allclose(gain1_output, expected_gain1, rtol=1e-5)

            # gain2 should be input * 0.5 * 0.8 = input * 0.4
            expected_gain2 = test_signal * 0.4
            np.testing.assert_allclose(gain2_output, expected_gain2, rtol=1e-5)
        except ImportError:
            pytest.skip("C++ module or Faust DSP not available")

    def test_total_gain_calculation(self, simple_spec_file, sample_rate):
        """Test calculating total gain from cascaded processors."""
        spec = example_from_spec.parse_graph_spec(simple_spec_file)

        # Calculate expected total gain
        expected_gain = 1.0
        for proc_name, params in spec['parameters'].items():
            if 'gain' in params:
                expected_gain *= params['gain']

        assert expected_gain == pytest.approx(0.4)


class TestGraphSpecFormats:
    """Tests for different spec file formats and edge cases."""

    def test_single_processor(self, sample_rate):
        """Test spec with single processor."""
        content = """## Processors
gain: ExampleProcessor()

## Routing
input -> gain
gain -> output

## Parameters
gain.gain = 0.75
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.graph', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            spec = example_from_spec.parse_graph_spec(temp_path)
            assert len(spec['processors']) == 1
            assert len(spec['routing']) == 2

            try:
                graph, _ = example_from_spec.generate_graph_from_spec(spec, sample_rate)
                assert graph.processors['gain'].gain == pytest.approx(0.75)
            except ImportError:
                pytest.skip("C++ module not available")
        finally:
            os.unlink(temp_path)

    def test_no_parameters_section(self, sample_rate):
        """Test spec without parameters section (uses defaults)."""
        content = """## Processors
gain: ExampleProcessor()

## Routing
input -> gain
gain -> output
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.graph', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            spec = example_from_spec.parse_graph_spec(temp_path)
            assert spec['parameters'] == {}

            try:
                graph, _ = example_from_spec.generate_graph_from_spec(spec, sample_rate)
                # Should use default gain value (1.0 for ExampleProcessor)
                assert graph.processors['gain'].gain == pytest.approx(1.0)
            except ImportError:
                pytest.skip("C++ module not available")
        finally:
            os.unlink(temp_path)
