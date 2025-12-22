#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "CoefGen.hpp"

namespace py = pybind11;

PYBIND11_MODULE(coefgen, m) {
  m.doc() = "CoefGen plugin"; // optional module docstring
  m.def("PeakingCoefs", &CoefGen::PeakingCoefs, "Compute Coefs for peaking filter",
    py::arg("Fc"), py::arg("dBboost"), py::arg("Q"), py::arg("Fs"));
}

