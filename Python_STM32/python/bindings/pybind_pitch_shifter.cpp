// Pybind wrapper for the generated pitch_shifter pipeline.
#include "pitch_shifter.h"

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>

#include <cstring>
#include <stdexcept>

namespace py = pybind11;

PYBIND11_MODULE(pybind_pitch_shifter, m) {
  m.doc() = "Generated pitch-shifter pipeline (one process_chunk + buffer probes)";

  py::class_<pitch_shifter>(m, "pitch_shifter")
    .def(py::init<>())
    .def("init", &pitch_shifter::init, py::arg("sample_rate"))

    .def("process_chunk",
         [](pitch_shifter& self,
            py::array_t<float, py::array::c_style | py::array::forcecast> in_arr)
         -> py::array_t<float> {
           int n = (int)in_arr.size();
           if (n > pitch_shifter::kChunkSize)
             throw std::runtime_error("input length exceeds CHUNK_SIZE");
           py::array_t<float> out_arr(n);
           self.process_chunk(in_arr.data(), out_arr.mutable_data(), n);
           return out_arr;
         },
         "Process the entire input array in one call. Returns the output array.",
         py::arg("input"))

    .def("get_buffer",
         [](pitch_shifter& self, const std::string& name, int n) -> py::array_t<float> {
           const float* p = self.get_buffer(name.c_str());
           if (!p) throw std::runtime_error("unknown buffer: " + name);
           // Non-owning view into the static buffer; valid until the next
           // process_chunk overwrites the contents.
           return py::array_t<float>({(py::ssize_t)n}, {sizeof(float)}, p, py::cast(&self));
         },
         "Return a NumPy view of the named buffer's first n samples. "
         "View is valid until the next process_chunk() call.",
         py::arg("name"), py::arg("n"))

    .def("set_param", &pitch_shifter::set_param, py::arg("path"), py::arg("value"))

    .def_property_readonly_static("CHUNK_SIZE",
         [](py::object) { return pitch_shifter::kChunkSize; });
}
