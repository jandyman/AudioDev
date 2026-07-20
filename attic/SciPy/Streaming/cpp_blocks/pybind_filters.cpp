#include "filters.h"
#include "pybind_support.h"

PYBIND11_MODULE(pybind_filters, m) {

  py::class_<BiquadChainState>(m, "BiquadChainState")
    .def(py::init<>())
    .def_property("dlybuf",
                  [](const BiquadChainState& o) { return vec_to_np(o.dlybuf); },
                  [](BiquadChainState& o, py::array_t<float> v) { o.dlybuf = np_to_vec<float>(v); })
    ;

  py::class_<BiquadChainParams>(m, "BiquadChainParams")
    .def(py::init<>())
    .def_readwrite("n_stages", &BiquadChainParams::n_stages)
    .def_property("coefs",
                  [](const BiquadChainParams& o) { return vec_to_np(o.coefs); },
                  [](BiquadChainParams& o, py::array_t<float> v) { o.coefs = np_to_vec<float>(v); })
    ;

  py::class_<BiquadChain>(m, "BiquadChain")
    .def(py::init<>())
    .def_readwrite("params", &BiquadChain::params)
    .def_readwrite("state", &BiquadChain::state)
    .def("init", &BiquadChain::init)
    .def("proc", [](BiquadChain& o, py::list buffers) {
          vector<vector<float>> v_buffers = np_list_to_vect_of_vect<float>(buffers);
          o.proc(v_buffers);
          cp_vec_vec_into_list_of_np(v_buffers, buffers);
        }, py::arg("buffers").noconvert() )
    ;

  py::class_<BiquadChain64State>(m, "BiquadChain64State")
    .def(py::init<>())
    .def_property("dlybuf",
                  [](const BiquadChain64State& o) { return vec_to_np(o.dlybuf); },
                  [](BiquadChain64State& o, py::array_t<double> v) { o.dlybuf = np_to_vec<double>(v); })
    ;

  py::class_<BiquadChain64Params>(m, "BiquadChain64Params")
    .def(py::init<>())
    .def_readwrite("n_stages", &BiquadChain64Params::n_stages)
    .def_property("coefs",
                  [](const BiquadChain64Params& o) { return vec_to_np(o.coefs); },
                  [](BiquadChain64Params& o, py::array_t<double> v) { o.coefs = np_to_vec<double>(v); })
    ;

  py::class_<BiquadChain64>(m, "BiquadChain64")
    .def(py::init<>())
    .def_readwrite("params", &BiquadChain64::params)
    .def_readwrite("state", &BiquadChain64::state)
    .def("init", &BiquadChain64::init)
    .def("proc", [](BiquadChain64& o, py::list buffers) {
          vector<vector<double>> v_buffers = np_list_to_vect_of_vect<double>(buffers);
          o.proc(v_buffers);
          cp_vec_vec_into_list_of_np(v_buffers, buffers);
        }, py::arg("buffers").noconvert() )
    ;

  py::class_<XCoupledPolesState>(m, "XCoupledPolesState")
    .def(py::init<>())
    .def_readwrite("a1", &XCoupledPolesState::a1)
    .def_readwrite("a2", &XCoupledPolesState::a2)
    .def_readwrite("s1", &XCoupledPolesState::s1)
    .def_readwrite("s2", &XCoupledPolesState::s2)
    ;

}
