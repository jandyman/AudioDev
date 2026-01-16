#include "../../dsp_library/cpp/include/split_chorus.h"
#include "audio_support.h"

PYBIND11_MODULE(pybind_split_chorus, m) {
  m.doc() = "Split chorus processor - lows bypass, highs with random modulation";

  py::class_<SplitChorus>(m, "SplitChorus")
    .def(py::init<>())

    // Lifecycle
    .def("init", &SplitChorus::init,
         "Initialize processor with sample rate",
         py::arg("sample_rate"))

    // Processing - convert between numpy and C++ vectors
    .def("process",
         [](SplitChorus& self, py::list inputs) -> py::list {
           // Convert input: list of numpy arrays -> vector of vectors
           auto inputs_vec = np_list_to_vec_of_vec<float>(inputs);

           // Prepare output buffers with same shape as inputs
           vector<vector<float>> outputs_vec;
           for (const auto& input_ch : inputs_vec) {
             outputs_vec.push_back(vector<float>(input_ch.size()));
           }

           // Process
           self.process(inputs_vec, outputs_vec);

           // Convert output: vector of vectors -> list of numpy arrays
           return vec_of_vec_to_np_list(outputs_vec);
         },
         "Process audio buffers",
         py::arg("inputs"))

    // Introspection
    .def("get_num_inputs", &SplitChorus::get_num_inputs,
         "Get number of input channels")
    .def("get_num_outputs", &SplitChorus::get_num_outputs,
         "Get number of output channels")
    .def("get_sample_rate", &SplitChorus::get_sample_rate,
         "Get current sample rate")

    // Parameters
    .def("set_param", &SplitChorus::set_param,
         "Set parameter value by name",
         py::arg("name"), py::arg("value"))
    .def("get_param", &SplitChorus::get_param,
         "Get parameter value by name",
         py::arg("name"))
    .def("get_param_names", &SplitChorus::get_param_names,
         "Get list of all parameter names");
}
