#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include <pybind11/stl_bind.h>
#include <stdexcept>
#include "GenericDsp.hpp"

namespace py = pybind11;
using namespace DspBlocks;
using namespace std;

typedef py::array_t<float, py::array::c_style | py::array::forcecast> c_pyarray;

PYBIND11_MAKE_OPAQUE(std::vector<Pin>);
PYBIND11_MAKE_OPAQUE(std::vector<Parameter>);

PYBIND11_MODULE(GenericDspTest, m) {
  m.doc() = "Test Module for DSP blocks"; // optional module docstring

  py::bind_vector<std::vector<Pin>>(m, "PinVector");
  py::bind_vector<std::vector<Parameter>>(m, "ParameterVector");

  py::class_<Wire>(m, "Wire")
    .def(py::init<>())
    .def(py::init<const int, const float, const int>(),
      py::arg("n_channels"), py::arg("sample_rate"), py::arg("buf_size"))
    .def_readwrite("nChannels", &Wire::nChannels)
    .def_readwrite("SampleRate", &Wire::sampleRate)
    .def_readwrite("BufSize", &Wire::bufSize)
  ;

  py::class_<Pin>(m, "Pin")
    .def(py::init<const char*>(), py::arg("name"))
    .def_readwrite("wire", &Pin::wire)
    .def_readonly("name", &Pin::name)
  ;

  py::class_<Parameter>(m, "Parameter")
    .def(py::init<>())
    .def_readwrite("size", &Parameter::size)
  ;

  py::class_<DspBlock>(m, "DspBlock")
    .def(py::init<>())
    .def_readwrite("input_pins", &DspBlock::input_pins)
    .def_readwrite("output_pins", &DspBlock::output_pins)
    .def_readwrite("parameters", &DspBlock::parameters)
    .def("set_param", &DspBlock::set_param)
  ;  

  py::class_<MyDspBlock, DspBlock>(m, "MyDspBlock")
    .def(py::init<>())
    .def_readwrite("param1", &MyDspBlock::param1)
    .def_readwrite("param2", &MyDspBlock::param2)
  ;

}