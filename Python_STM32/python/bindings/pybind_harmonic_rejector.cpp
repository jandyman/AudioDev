#include "../../dsp_cpp/include/harmonic_rejector.h"
#include "audio_support.h"

PYBIND11_MODULE(pybind_harmonic_rejector, m) {
  m.doc() = "Harmonic Rejector: multi-LPF bank with cleanness selector for period estimation";

  py::class_<HarmonicRejector>(m, "HarmonicRejector")
    .def(py::init<>())

    .def("init", &HarmonicRejector::init,
         "Initialize with sample rate",
         py::arg("sample_rate"))

    .def("process",
         [](HarmonicRejector& self, py::list inputs) -> py::list {
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
         "Process one buffer. inputs: [audio]\n"
         "outputs are 7*NUM_FILTERS + 4 channels.\n"
         "Per filter k in [0, NUM_FILTERS):\n"
         "  0*N+k : x_filt\n"
         "  1*N+k : env_filt\n"
         "  2*N+k : tall_peak (0/1)\n"
         "  3*N+k : mu (samples)\n"
         "  4*N+k : sigma (samples)\n"
         "  5*N+k : cleanness\n"
         "  6*N+k : amplitude\n"
         "Aggregate:\n"
         "  7*N+0 : selected_filter_index (-1 if none)\n"
         "  7*N+1 : P (selected mu, samples)\n"
         "  7*N+2 : sigma_sel\n"
         "  7*N+3 : qualified (0/1)",
         py::arg("inputs"))

    .def_readonly_static("NUM_FILTERS", &HarmonicRejector::NUM_FILTERS)
    .def_readonly_static("NUM_OUTPUTS", &HarmonicRejector::NUM_OUTPUTS)

    .def("get_num_inputs",  &HarmonicRejector::get_num_inputs)
    .def("get_num_outputs", &HarmonicRejector::get_num_outputs)
    .def("get_sample_rate", &HarmonicRejector::get_sample_rate)

    .def("set_param", &HarmonicRejector::set_param,
         py::arg("name"), py::arg("value"))
    .def("get_param", &HarmonicRejector::get_param,
         py::arg("name"))
    .def("get_param_names", &HarmonicRejector::get_param_names);
}
