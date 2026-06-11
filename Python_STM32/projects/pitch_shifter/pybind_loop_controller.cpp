#include "loop_controller.h"
#include "audio_support.h"

PYBIND11_MODULE(pybind_loop_controller, m) {
  m.doc() = "Loop Controller: pitch-shift loop point detection and crossfade management";

  py::class_<loop_controller>(m, "loop_controller")
    .def(py::init<>())

    .def("init", &loop_controller::init,
         "Initialize with sample rate",
         py::arg("sample_rate"))

    .def("process",
         [](loop_controller& self, py::list inputs) -> py::list {
           auto inputs_vec = np_list_to_vec_of_vec<float>(inputs);
           int n = inputs_vec.empty() ? 0 : (int)inputs_vec[0].size();
           int num_outputs = self.get_num_outputs();
           vector<vector<float>> outputs_vec(num_outputs, vector<float>(n, 0.0f));

           vector<const float*> in_ptrs(inputs_vec.size());
           for (size_t i = 0; i < inputs_vec.size(); i++) in_ptrs[i] = inputs_vec[i].data();
           vector<float*> out_ptrs(outputs_vec.size());
           for (size_t i = 0; i < outputs_vec.size(); i++) out_ptrs[i] = outputs_vec[i].data();

           self.process(in_ptrs.data(), out_ptrs.data(), n);
           return vec_of_vec_to_np_list(outputs_vec);
         },
         "Process one buffer.\n"
         "inputs: [zc_impulse, attack_impulse, P_samples, sigma_samples, qualified]\n"
         "  (P, sigma, qualified come from HarmonicRejector; pass arrays of zeros\n"
         "   to disable the integer-multiple gate and use legacy newest-valid behaviour.)\n"
         "outputs: [tap1_delay_ms, tap2_delay_ms, tap3_delay_ms,\n"
         "          gain1, gain2, gain3,\n"
         "          latency_ms, loop_event, active_tap, bailout_event,\n"
         "          gated_event, attack_event]",
         py::arg("inputs"))

    .def("get_num_inputs",  &loop_controller::get_num_inputs)
    .def("get_num_outputs", &loop_controller::get_num_outputs)
    .def("get_sample_rate", &loop_controller::get_sample_rate)

    .def("set_param", &loop_controller::set_param,
         py::arg("name"), py::arg("value"))
    .def("get_param", &loop_controller::get_param,
         py::arg("name"))
    .def("get_param_names", &loop_controller::get_param_names);
}
