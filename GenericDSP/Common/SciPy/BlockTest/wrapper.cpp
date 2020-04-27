#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include "GenericDsp.hpp"
#include "Mixers.hpp"

namespace py = pybind11;
using namespace DspBlocks;

struct TestFixture {
  GainMute gm;
  ConnectionWire inputWire;
  ConnectionWire outputWire;

  TestFixture(WireSpec ws) {
    inputWire.wireSpec = ws;
    outputWire.wireSpec = ws;
    inputWire.buffers = ws.AllocateBuffers();
    outputWire.buffers = ws.AllocateBuffers();
    gm.inputPins[0].wire = &inputWire;
    gm.inputPins[1].wire = &outputWire;
    gm.SetGainDb(3);
    gm.SetEnable(true);
    gm.Init();
  }

  py::array_t<float, py::array::c_style | py::array::forcecast>
  Process(py::array_t<float, py::array::c_style | py::array::forcecast> input) {
    auto buf = input.request();
    auto ndim = input.ndim();
    auto shape = input.shape();
    auto stride = input.strides();
    py::print("ndim =", ndim);
    for (int i=0; i<ndim; i++) {
      py::print("dim", i, "=", shape[i]);
      py::print("stride", i, "=", stride[i]);
    }
    float* bufs[2];
    float* base_ptr = reinterpret_cast<float*>(input.request().ptr);
    inputWire.buffers[0] = base_ptr;
    inputWire.buffers[1] = &base_ptr[shape[1]];
    auto output = py::array_t<float>(input.size());
    output.resize({shape[0], shape[1]});
    float* obase_ptr = reinterpret_cast<float*>(output.request().ptr);
    outputWire.buffers[0] = obase_ptr;
    outputWire.buffers[1] = &obase_ptr[shape[1]]; 
    gm.Process();
    return output;
  }

};


PYBIND11_MODULE(block_test, m) {
  m.doc() = "Test Module for DSP blocks"; // optional module docstring

  py::class_<DspBlocks::GainMute>(m, "GainMute")
  .def(py::init<>())
  .def("SetGainDb", &DspBlocks::GainMute::SetGainDb)
  .def("GainDb", &DspBlocks::GainMute::GainDb)
  .def("SetGain", &DspBlocks::GainMute::SetGain)
  .def("Gain", &DspBlocks::GainMute::Gain)
  .def("SetInPhase", &DspBlocks::GainMute::SetInPhase)
  .def("InPhase", &DspBlocks::GainMute::InPhase)
  ;

  py::class_<DspBlocks::WireSpec>(m, "WireSpec")
    .def(py::init<const int, const float, const int>(),
      py::arg("n_channels"), py::arg("sample_rate"), py::arg("buf_size"))
    .def_readwrite("nChannels", &DspBlocks::WireSpec::nChannels)
    .def_readwrite("SampleRate", &DspBlocks::WireSpec::sampleRate)
    .def_readwrite("BufSize", &DspBlocks::WireSpec::bufSize)
  ;
  
  py::class_<DspBlocks::ConnectionWire>(m, "ConnectionWire")
    .def(py::init<>())
    .def("WireSpec", &DspBlocks::ConnectionWire::GetWireSpec)
    .def("SetWirespec", &DspBlocks::ConnectionWire::SetWireSpec)
  ;
  
  py::class_<TestFixture>(m, "TestFixture")
    .def(py::init<const WireSpec>())
    .def("Process", &TestFixture::Process)
  ;

}

