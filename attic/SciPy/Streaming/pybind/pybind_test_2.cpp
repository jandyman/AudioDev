#include "pybind_support.h"

struct DelayBufState {
  vector<float> data;
  int wr_idx;
};
PYBIND11_MODULE(pybind_test_2, m) {
  py::class_<DelayBufState>(m, "DelayBufState")
    .def(py::init<>())
    .def_property("data",
                  [](const DelayBufState& o) { return vec_to_np(o.data); },
                  [](DelayBufState& o, py::array_t<float> v) { o.data = np_to_vec<float>(v); })
    .def_readwrite("wr_idx", &DelayBufState::wr_idx)
    ;
}

