#include "delaybuf.h"
#include "resample.h"
#include "pybind_support.h"

PYBIND11_MODULE(pybind_resample, m) {

  py::class_<JosFractDelayParams>(m, "JosFractDelayParams")
    .def(py::init<>())
    .def_property("buffer",
                  [](const JosFractDelayParams& o) { return vec_to_np(o.buffer); },
                  [](JosFractDelayParams& o, py::array_t<float> v) { o.buffer = np_to_vec<float>(v); })
    .def_property("h_coef_set",
                  [](const JosFractDelayParams& o) { return vec_to_np(o.h_coef_set); },
                  [](JosFractDelayParams& o, py::array_t<float> v) { o.h_coef_set = np_to_vec<float>(v); })
    .def_readwrite("oversamp_bits", &JosFractDelayParams::oversamp_bits)
    .def_readwrite("allow_overflow", &JosFractDelayParams::allow_overflow)
    ;

  py::class_<JosFractDelay>(m, "JosFractDelay")
    .def(py::init<>())
    .def_readwrite("params", &JosFractDelay::params)
    .def("fixed_delay", &JosFractDelay::fixed_delay)
    ;

  py::class_<ResamplerState>(m, "ResamplerState")
    .def(py::init<>())
    .def_readwrite("frac_dly", &ResamplerState::frac_dly)
    .def_readwrite("dly_buf", &ResamplerState::dly_buf)
    ;

  py::class_<Resampler>(m, "Resampler")
    .def(py::init<>())
    .def_readwrite("state", &Resampler::state)
    .def("proc", [](Resampler& o, py::list bufs) {
          vector<vector<float>> v_bufs = np_list_to_vect_of_vect<float>(bufs);
          o.proc(v_bufs);
          cp_vec_vec_into_list_of_np(v_bufs, bufs);
        }, py::arg("bufs").noconvert() )
    ;

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
    .def("get_values", [](DelayBuf& o, type delay, py::array_t<float> output) {
          vector<float> v_output = np_to_vec<float>(output);
          o.get_values(delay,v_output);
          copy_vec_to_np(v_output, output);
        }, py::arg("delay"), py::arg("output").noconvert() )
    ;
}
