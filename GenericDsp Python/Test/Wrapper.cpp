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

PYBIND11_MAKE_OPAQUE(std::vector<WireSpec>);
PYBIND11_MAKE_OPAQUE(std::vector<Parameter>);

PYBIND11_MODULE(GenericDspTest, m) {
  m.doc() = "Test Module for DSP blocks"; // optional module docstring

  py::bind_vector<std::vector<WireSpec>>(m, "WireSpecVector");
  py::bind_vector<std::vector<Parameter>>(m, "ParameterVector");

  py::class_<WireSpec>(m, "WireSpec")
    .def(py::init<const int, const float, const int>(),
      py::arg("n_channels"), py::arg("sample_rate"), py::arg("buf_size"))
    .def_readwrite("nChannels", &WireSpec::nChannels)
    .def_readwrite("SampleRate", &WireSpec::sampleRate)
    .def_readwrite("BufSize", &WireSpec::bufSize)
  ;

  py::class_<Parameter>(m, "Parameter")
    .def(py::init<>())
    .def_readwrite("size", &Parameter::size)
  ;

  py::class_<DspBlock>(m, "DspBlock")
    .def(py::init<>())
    .def_readwrite("WireSpecs", &DspBlock::wireSpecs)
    .def_readwrite("Parameters", &DspBlock::parameters)
    .def("SetParam", &DspBlock::SetParam)
  ;  

  py::class_<MyDspBlock, DspBlock>(m, "MyDspBlock")
    .def(py::init<>())
    .def_readwrite("Param1", &MyDspBlock::param1)
    .def_readwrite("Param2", &MyDspBlock::param2)
  ;

}