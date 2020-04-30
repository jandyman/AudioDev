#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include <stdexcept>
#include "GenericDsp.hpp"
#include "Mixers.hpp"

namespace py = pybind11;
using namespace DspBlocks;
using namespace std;

struct TestFixture {
  GainMute gm;
  ConnectionWire inputWire;
  ConnectionWire outputWire;
  WireSpec ws;

  TestFixture(WireSpec ws) : ws(ws) {
    inputWire.wireSpec = ws;
    outputWire.wireSpec = ws;
    inputWire.buffers = new float*[ws.nChannels];
    outputWire.buffers = new float*[ws.nChannels];
    gm.inputPins[0].wire = &inputWire;
    gm.outputPins[0].wire = &outputWire;
    gm.SetGainDb(3);
    gm.SetEnable(true);
    gm.Init();
  }

  ~TestFixture() {
    delete inputWire.buffers;
    delete outputWire.buffers;
  }

  py::array_t<float, py::array::c_style | py::array::forcecast>
  Process(py::array_t<float, py::array::c_style | py::array::forcecast> input) {
    auto ndim = input.ndim();
    if (ndim > 2) { throw invalid_argument("too many dimensions"); }
    int nChans, bufsiz;
    auto shape = input.shape();
    if (ndim == 1) { nChans = 1; bufsiz = shape[0]; } 
    else { 
      bufsiz = shape[0]; nChans = shape[1]; 
    }
    if (nChans != ws.nChannels) { throw invalid_argument("nchannels mismatch"); }
    if (bufsiz != ws.bufSize) { throw invalid_argument("bufsize mismatch"); }
    auto strides = input.strides();
    auto output = py::array_t<float>(input.size());
    output.resize({shape[0], shape[1]});
    float* ibase_ptr = reinterpret_cast<float*>(input.request().ptr);
    float* obase_ptr = reinterpret_cast<float*>(output.request().ptr);
    for (int i=0; i < nChans; i++) {
      inputWire.buffers[i] = &ibase_ptr[i * bufsiz];
      outputWire.buffers[i] = &obase_ptr[i * bufsiz];
    }
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

