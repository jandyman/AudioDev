// Pybind wrapper for the generated single-block YIN graph.
#include "yin.h"

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>

#include <cstring>
#include <stdexcept>

namespace py = pybind11;

PYBIND11_MODULE(pybind_yin, m) {
  m.doc() = "Generated YIN pitch detector (one process_chunk + buffer probes)";

  py::class_<yin>(m, "yin")
    .def(py::init<>())
    .def("init", &yin::init, py::arg("sample_rate"))

    .def("process_chunk",
         [](yin& self,
            py::array_t<float, py::array::c_style | py::array::forcecast> in_arr)
         -> py::array_t<float> {
           int n = (int)in_arr.size();
           if (n > yin::kChunkSize)
             throw std::runtime_error("input length exceeds CHUNK_SIZE");
           constexpr int n_out = yin::kNumOutputs;
           py::array_t<float> out_arr({(py::ssize_t)n, (py::ssize_t)n_out});
           std::vector<std::vector<float>> ch_bufs(n_out, std::vector<float>(n));
           float* out_ptrs[n_out];
           for (int c = 0; c < n_out; ++c) out_ptrs[c] = ch_bufs[c].data();
           const float* in_ptrs[] = { in_arr.data() };
           self.process_chunk(in_ptrs, out_ptrs, n);
           float* dst = out_arr.mutable_data();
           for (int i = 0; i < n; ++i)
             for (int c = 0; c < n_out; ++c)
               dst[i * n_out + c] = ch_bufs[c][i];
           return out_arr;
         },
         "Process the input array. Returns (N, kNumOutputs) — column 0 = first "
         "declared output port, etc. Same code path for whole-file or chunked.",
         py::arg("input"))

    .def_property_readonly_static("NUM_OUTPUTS",
         [](py::object) { return yin::kNumOutputs; })
    .def_property_readonly_static("NUM_INPUTS",
         [](py::object) { return yin::kNumInputs; })

    .def("get_buffer",
         [](yin& self, const std::string& name, int n) -> py::array_t<float> {
           const float* p = self.get_buffer(name.c_str());
           if (!p) throw std::runtime_error("unknown buffer: " + name);
           return py::array_t<float>({(py::ssize_t)n}, {sizeof(float)}, p, py::cast(&self));
         },
         "Return a NumPy view of the named buffer's first n samples. "
         "View is valid until the next process_chunk() call.",
         py::arg("name"), py::arg("n"))

    .def("set_param", &yin::set_param, py::arg("path"), py::arg("value"))

    .def_property_readonly_static("CHUNK_SIZE",
         [](py::object) { return yin::kChunkSize; });
}
