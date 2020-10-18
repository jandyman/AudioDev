#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include <stdexcept>
#include "GenericDsp.hpp"
#include "Mixers.hpp"
#include "FddlConvolver.hpp"

namespace py = pybind11;
using namespace DspBlocks;
using namespace std;

typedef py::array_t<float, py::array::c_style | py::array::forcecast> c_pyarray;

// This class tests a DSP block which has one input and one output at a single sample rate

template <class T> struct TestFixture : T {
  ConnectionWire inputWire;
  ConnectionWire outputWire;
  WireSpec ws;

  TestFixture(WireSpec ws) : ws(ws) {
    inputWire.wireSpec = ws;
    outputWire.wireSpec = ws;
    inputWire.buffers = new float*[ws.nChannels];
    outputWire.buffers = new float*[ws.nChannels];
    for (int i=0; i < ws.nChannels; i++) {
      inputWire.buffers[i] = new float[ws.bufSize];
      outputWire.buffers[i] = new float[ws.bufSize];
    }
    T::inputPins[0].wire = &inputWire;
    T::outputPins[0].wire = &outputWire;
    T::Init();
  }

  ~TestFixture() {
    for (int i=0; i < ws.nChannels; i++) {
      delete inputWire.buffers[i];
      delete outputWire.buffers[i];
    }
    delete inputWire.buffers;
    delete outputWire.buffers;
  }

  // This method performs the necessary translation/copy of numpy arrays and then calls the 
  // internal Process function of the inherited class 

  c_pyarray Process(c_pyarray input) {
    using namespace std;
    bool inputIsVector = false;
    auto ndim = input.ndim();
    if (ndim > 2) { throw invalid_argument("too many dimensions"); }
    int nChans, bufsiz;
    auto shape = input.shape();
    if (ndim == 1) { nChans = 1; bufsiz = shape[0]; inputIsVector = true ;} 
    else { 
      bufsiz = shape[0]; nChans = shape[1]; 
    }
    if (nChans != ws.nChannels) { throw invalid_argument("nchannels mismatch"); }
    if (bufsiz != ws.bufSize) { throw invalid_argument("bufsize mismatch"); }
    auto strides = input.strides();
    auto output = py::array_t<float>(input.size());
    if (inputIsVector) {
      output = output.squeeze();
    } else {
      output.resize({bufsiz, nChans});
    }
    float* ibase_ptr = reinterpret_cast<float*>(input.request().ptr);
    float* obase_ptr = reinterpret_cast<float*>(output.request().ptr);
    for (int i=0; i < nChans; i++) {
      auto src = &ibase_ptr[i * bufsiz];
      copy(src, src + bufsiz, inputWire.buffers[i]);
      outputWire.buffers[i] = &obase_ptr[i * bufsiz];
    }
    T::Process();
    for (int i=0; i < nChans; i++) {
      auto src = inputWire.buffers[i];
      copy(src, src + bufsiz, &obase_ptr[i * bufsiz]);
    }
    return output;
  }

};

vector<float> FloatVector(c_pyarray input) {
  auto ndim = input.ndim();
  if (ndim > 2) { throw invalid_argument("too many dimensions"); }
  auto shape = input.shape();
  if (ndim == 2 && shape[1] != 1) { throw invalid_argument("must be vector not matrix"); }
  int size = shape[0];
  float* storage = reinterpret_cast<float*>(input.request().ptr);
  return vector<float>(storage, storage + size);
}

PYBIND11_MODULE(block_test, m) {
  m.doc() = "Test Module for DSP blocks"; // optional module docstring

  py::class_<GainMute>(m, "GainMute")
  .def(py::init<>())
  .def("SetGainDb", &GainMute::SetGainDb)
  .def("GainDb", &GainMute::GainDb)
  .def("SetGain", &GainMute::SetGain)
  .def("Gain", &GainMute::Gain)
  .def("SetInPhase", &GainMute::SetInPhase)
  .def("InPhase", &GainMute::InPhase)
  ;

  py::class_<WireSpec>(m, "WireSpec")
    .def(py::init<const int, const float, const int>(),
      py::arg("n_channels"), py::arg("sample_rate"), py::arg("buf_size"))
    .def_readwrite("nChannels", &WireSpec::nChannels)
    .def_readwrite("SampleRate", &WireSpec::sampleRate)
    .def_readwrite("BufSize", &WireSpec::bufSize)
  ;
  
  py::class_<ConnectionWire>(m, "ConnectionWire")
    .def(py::init<>())
    .def("WireSpec", &ConnectionWire::GetWireSpec)
    .def("SetWirespec", &ConnectionWire::SetWireSpec)
  ;
  
  py::class_<TestFixture<GainMute>>(m, "GainMuteTestFixture")
    .def(py::init<const WireSpec>())
    .def("Init", &TestFixture<GainMute>::Init)
    .def("SetGainDb", &TestFixture<GainMute>::SetGainDb)
    .def("Process", &TestFixture<GainMute>::Process)
  ;

  py::class_<TestFixture<FddlBlock>>(m, "FddlConvolverTestFixture")
    .def(py::init<const WireSpec>())
    .def("Init", &TestFixture<FddlBlock>::Init)
    .def("SetImpulse", [](TestFixture<FddlBlock>& o, c_pyarray data) {
      o.SetImpulse(FloatVector(data));
    })
    .def("Process", &TestFixture<FddlBlock>::Process)
  ;

}

