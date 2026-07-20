#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>

#include <cstdint>
#include <vector>
#include <math.h>

using std::vector;
using std::copy;

namespace py = pybind11;

template <typename T> std::vector<T> np_to_vec(py::array_t<T> input_array) {
    auto buf = input_array.unchecked(); // No bounds checking
    size_t size = buf.size();

    std::vector<T> vec(size);
    memcpy(&vec[0], &buf[0], size*sizeof(T));
    return vec;
}

template <typename T> py::array vec_to_np(const std::vector<T>& vec) {
    return py::array(vec.size(), vec.data());
}

struct TestS {
    int x;
    float y;
    std::vector<float> v;
};

PYBIND11_MODULE(pybind_test_1, m) {
    m.def("numpy_to_vector", &np_to_vec<float>);

    py::class_<TestS>(m, "TestS")
    .def(py::init<>())
    .def_readwrite("x", &TestS::x)
    .def_readwrite("y", &TestS::y)
    .def_property("v",
                  [](const TestS& o){ return vec_to_np(o.v); },
                  [](TestS& o, py::array_t<float> val) { o.v = np_to_vec<float>(val); }
                  )
    ;
}