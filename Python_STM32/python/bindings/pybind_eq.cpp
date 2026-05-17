// pybind_eq.cpp — Native EQ bindings: EqChannel (hi-shelf + LP) + coefficient functions.
//
// Exposes:
//   EqChannel          — init(), set_params(), process_block()
//   compute_hishelf()  — returns (b0,b1,b2,a1,a2) with a1/a2 stored negated (biquad.h convention)
//   compute_lpf()      — same
//
// set_params() collapses recompute()+apply_new_coefficients() into one call —
// the ISR staging handshake is not needed in the native build.

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include "biquad.h"

namespace py = pybind11;

PYBIND11_MODULE(pybind_eq, m) {
  m.doc() = "Native EQ — hi-shelf + LP biquad chain";

  // Free coefficient functions — Python uses these to compute the theoretical
  // frequency response via scipy.signal.freqz for comparison against measured.
  // a1/a2 in the returned tuple are stored negated (biquad.h convention):
  //   scipy b = [b0, b1, b2],  a = [1, -a1_returned, -a2_returned]
  m.def("compute_hishelf",
    [](float gain_db, float fc_hz, float sample_rate) {
      auto c = biquad_compute_hishelf(gain_db, fc_hz, sample_rate);
      return py::make_tuple(c.b0, c.b1, c.b2, c.a1, c.a2);
    },
    py::arg("gain_db"), py::arg("fc_hz"), py::arg("sample_rate"));

  m.def("compute_lpf",
    [](float fc_hz, float sample_rate) {
      auto c = biquad_compute_lpf_butterworth(fc_hz, sample_rate);
      return py::make_tuple(c.b0, c.b1, c.b2, c.a1, c.a2);
    },
    py::arg("fc_hz"), py::arg("sample_rate"));

  py::class_<EqChannel>(m, "EqChannel")
    .def(py::init<>())
    .def("init",
      &EqChannel::init,
      py::arg("shelf_gain_db"), py::arg("shelf_fc_hz"),
      py::arg("lp_fc_hz"), py::arg("sample_rate"))
    .def("set_params",
      [](EqChannel& s, float shelf_gain_db, float shelf_fc_hz,
         float lp_fc_hz, float sample_rate) {
        s.recompute(shelf_gain_db, shelf_fc_hz, lp_fc_hz, sample_rate);
        s.apply_new_coefficients();
      },
      py::arg("shelf_gain_db"), py::arg("shelf_fc_hz"),
      py::arg("lp_fc_hz"), py::arg("sample_rate"))
    .def("process_block",
      [](EqChannel& s, py::array_t<float, py::array::c_style | py::array::forcecast> input) {
        auto in_buf  = input.request();
        auto output  = py::array_t<float>(in_buf.size);
        auto out_buf = output.request();
        auto* in_ptr  = static_cast<float*>(in_buf.ptr);
        auto* out_ptr = static_cast<float*>(out_buf.ptr);
        for (py::ssize_t i = 0; i < in_buf.size; ++i)
          out_ptr[i] = s.process(in_ptr[i]);
        return output;
      },
      py::arg("input"));
}
