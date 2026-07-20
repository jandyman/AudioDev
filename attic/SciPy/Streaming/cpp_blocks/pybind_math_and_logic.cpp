#include "math_and_logic.h"
#include "pybind_support.h"

PYBIND11_MODULE(pybind_math_and_logic, m) {

  py::class_<Abs>(m, "Abs")
    .def(py::init<>())
    .def("proc", [](Abs& o, py::list buffers) {
          vector<vector<float>> v_buffers = np_list_to_vect_of_vect<float>(buffers);
          o.proc(v_buffers);
          cp_vec_vec_into_list_of_np(v_buffers, buffers);
        }, py::arg("buffers").noconvert() )
    ;

  py::class_<Add>(m, "Add")
    .def(py::init<>())
    .def("proc", [](Add& o, py::list buffers) {
          vector<vector<float>> v_buffers = np_list_to_vect_of_vect<float>(buffers);
          o.proc(v_buffers);
          cp_vec_vec_into_list_of_np(v_buffers, buffers);
        }, py::arg("buffers").noconvert() )
    ;

  py::class_<Comparator>(m, "Comparator")
    .def(py::init<>())
    .def("proc", [](Comparator& o, py::list bufs) {
          vector<vector<float>> v_bufs = np_list_to_vect_of_vect<float>(bufs);
          o.proc(v_bufs);
          cp_vec_vec_into_list_of_np(v_bufs, bufs);
        }, py::arg("bufs").noconvert() )
    ;

  py::class_<EdgeDetectorState>(m, "EdgeDetectorState")
    .def(py::init<>())
    .def_readwrite("prev_samp", &EdgeDetectorState::prev_samp)
    ;

  py::class_<EdgeDetectorParams>(m, "EdgeDetectorParams")
    .def(py::init<>())
    .def_readwrite("thresh", &EdgeDetectorParams::thresh)
    .def_readwrite("mode", &EdgeDetectorParams::mode)
    ;

  py::class_<EdgeDetector>(m, "EdgeDetector")
    .def(py::init<>())
    .def_readwrite("params", &EdgeDetector::params)
    .def_readwrite("state", &EdgeDetector::state)
    .def("proc", [](EdgeDetector& o, py::list bufs) {
          vector<vector<float>> v_bufs = np_list_to_vect_of_vect<float>(bufs);
          o.proc(v_bufs);
          cp_vec_vec_into_list_of_np(v_bufs, bufs);
        }, py::arg("bufs").noconvert() )
    ;

  py::class_<Exp>(m, "Exp")
    .def(py::init<>())
    .def("proc", [](Exp& o, py::list buffers) {
          vector<vector<float>> v_buffers = np_list_to_vect_of_vect<float>(buffers);
          o.proc(v_buffers);
          cp_vec_vec_into_list_of_np(v_buffers, buffers);
        }, py::arg("buffers").noconvert() )
    ;

  py::class_<Log>(m, "Log")
    .def(py::init<>())
    .def("proc", [](Log& o, py::list buffers) {
          vector<vector<float>> v_buffers = np_list_to_vect_of_vect<float>(buffers);
          o.proc(v_buffers);
          cp_vec_vec_into_list_of_np(v_buffers, buffers);
        }, py::arg("buffers").noconvert() )
    ;

  py::class_<Mult>(m, "Mult")
    .def(py::init<>())
    .def("proc", [](Mult& o, py::list buffers) {
          vector<vector<float>> v_buffers = np_list_to_vect_of_vect<float>(buffers);
          o.proc(v_buffers);
          cp_vec_vec_into_list_of_np(v_buffers, buffers);
        }, py::arg("buffers").noconvert() )
    ;

  py::class_<Sqrt>(m, "Sqrt")
    .def(py::init<>())
    .def("proc", [](Sqrt& o, py::list buffers) {
          vector<vector<float>> v_buffers = np_list_to_vect_of_vect<float>(buffers);
          o.proc(v_buffers);
          cp_vec_vec_into_list_of_np(v_buffers, buffers);
        }, py::arg("buffers").noconvert() )
    ;

  py::class_<Square>(m, "Square")
    .def(py::init<>())
    .def("proc", [](Square& o, py::list buffers) {
          vector<vector<float>> v_buffers = np_list_to_vect_of_vect<float>(buffers);
          o.proc(v_buffers);
          cp_vec_vec_into_list_of_np(v_buffers, buffers);
        }, py::arg("buffers").noconvert() )
    ;

  py::class_<Sub>(m, "Sub")
    .def(py::init<>())
    .def("proc", [](Sub& o, py::list buffers) {
          vector<vector<float>> v_buffers = np_list_to_vect_of_vect<float>(buffers);
          o.proc(v_buffers);
          cp_vec_vec_into_list_of_np(v_buffers, buffers);
        }, py::arg("buffers").noconvert() )
    ;
}
