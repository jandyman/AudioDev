#include "../pitch_shifter_demo/mixer3.h"
#include "audio_support.h"

PYBIND11_MODULE(pybind_mixer3, m) {
  m.doc() = "mixer3: three-input weighted mixer — out = in1*gain1 + in2*gain2 + in3*gain3";

  py::class_<mixer3>(m, "mixer3")
    .def(py::init<>())
    .def("init", &mixer3::init, py::arg("sample_rate"))
    .def("process",
         [](mixer3& self, py::list inputs) -> py::list {
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
         "inputs: [in1, in2, in3, gain1, gain2, gain3]  outputs: [out]",
         py::arg("inputs"))
    .def("get_num_inputs",  &mixer3::get_num_inputs)
    .def("get_num_outputs", &mixer3::get_num_outputs)
    .def("get_sample_rate", &mixer3::get_sample_rate)
    .def("set_param", &mixer3::set_param, py::arg("name"), py::arg("value"))
    .def("get_param", &mixer3::get_param, py::arg("name"))
    .def("get_param_names", &mixer3::get_param_names);
}
