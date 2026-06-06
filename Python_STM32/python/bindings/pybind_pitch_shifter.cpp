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
           constexpr int n_out = pitch_shifter::kNumOutputs;
           // (n, n_out) C-contiguous: row = sample, col = output channel.
           py::array_t<float> out_arr({(py::ssize_t)n, (py::ssize_t)n_out});
           // Process into separate channel buffers, then interleave into (n, n_out).
           // Two channels stay on the stack for n <= kChunkSize; if n_out grows we'd
           // need a different strategy, but for stereo this is fine.
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
         "declared output port, column 1 = second, etc.",
         py::arg("input"))

    .def_property_readonly_static("NUM_OUTPUTS",
         [](py::object) { return pitch_shifter::kNumOutputs; })

    .def_property_readonly_static("NUM_INPUTS",
         [](py::object) { return pitch_shifter::kNumInputs; })

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
