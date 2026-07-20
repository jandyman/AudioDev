#include "delaybuf.h"
#include "pybind_support.h"

PYBIND11_MODULE(pybind_delaybuf, m) {
  m.def("test_modify_numpy_list", &test_modify_list_of_numpy, py::arg("x").noconvert());

  py::class_<DelayBufState>(m, "DelayBufState")
    .def(py::init<>())
    .def_property("data",
                  [](const DelayBufState& o) { return vec_to_np(o.data); },
                  [](DelayBufState& o, py::array_t<float> v) { o.data = np_to_vec<float>(v); })
    .def_readwrite("wr_idx", &DelayBufState::wr_idx)
    ;

  py::class_<DelayBuf>(m, "DelayBuf")
    .def(py::init<>())
    .def_readwrite("state", &DelayBuf::state)
    .def("push", [](DelayBuf& o, py::array_t<float> samples) {
          vector<float> v_samples = np_to_vec<float>(samples);
          o.push(v_samples);
          copy_vec_to_np(v_samples, samples);
        }, py::arg("samples").noconvert() )
    .def("get_values", [](DelayBuf& o, int delay, py::array_t<float> output) {
          vector<float> v_output = np_to_vec<float>(output);
          o.get_values(delay,v_output);
          copy_vec_to_np(v_output, output);
        }, py::arg("delay"), py::arg("output").noconvert() )
    ;
}
