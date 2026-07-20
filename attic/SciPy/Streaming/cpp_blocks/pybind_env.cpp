#include "env.h"
#include "pybind_support.h"

PYBIND11_MODULE(pybind_env, m) {

  py::class_<AttRelState>(m, "AttRelState")
    .def(py::init<>())
    .def_readwrite("lastout", &AttRelState::lastout)
    ;

  py::class_<AttRelParams>(m, "AttRelParams")
    .def(py::init<>())
    .def_readwrite("fs", &AttRelParams::fs)
    .def_readwrite("attTime", &AttRelParams::attTime)
    .def_readwrite("relTime", &AttRelParams::relTime)
    .def_readwrite("attCoef", &AttRelParams::attCoef)
    .def_readwrite("relCoef", &AttRelParams::relCoef)
    ;

  py::class_<AttRel>(m, "AttRel")
    .def(py::init<>())
    .def_readwrite("params", &AttRel::params)
    .def_readwrite("state", &AttRel::state)
    .def("init", &AttRel::init)
    .def("proc", [](AttRel& o, py::list buffers) {
          vector<vector<float>> v_buffers = np_list_to_vect_of_vect<float>(buffers);
          o.proc(v_buffers);
          cp_vec_vec_into_list_of_np(v_buffers, buffers);
        }, py::arg("buffers").noconvert() )
    ;

  py::class_<FollowPeaksState>(m, "FollowPeaksState")
    .def(py::init<>())
    .def_readwrite("lastpeak", &FollowPeaksState::lastpeak)
    .def_readwrite("lastout", &FollowPeaksState::lastout)
    .def_readwrite("sampSincePeak", &FollowPeaksState::sampSincePeak)
    ;

  py::class_<FollowPeaksParams>(m, "FollowPeaksParams")
    .def(py::init<>())
    .def_readwrite("attCoef", &FollowPeaksParams::attCoef)
    .def_readwrite("div", &FollowPeaksParams::div)
    ;

  py::class_<FollowPeaks>(m, "FollowPeaks")
    .def(py::init<>())
    .def_readwrite("params", &FollowPeaks::params)
    .def_readwrite("state", &FollowPeaks::state)
    .def("init", &FollowPeaks::init)
    .def("proc", [](FollowPeaks& o, py::list buffers) {
          vector<vector<float>> v_buffers = np_list_to_vect_of_vect<float>(buffers);
          o.proc(v_buffers);
          cp_vec_vec_into_list_of_np(v_buffers, buffers);
        }, py::arg("buffers").noconvert() )
    ;
}
