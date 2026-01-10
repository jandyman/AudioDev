#include "example_processor.h"
#include "audio_support.h"

PYBIND11_MODULE(pybind_example_processor, m) {
  m.doc() = "Example audio processor with gain parameter";

  py::class_<ExampleProcessor>(m, "ExampleProcessor")
    .def(py::init<>())

    // Lifecycle
    .def("init", &ExampleProcessor::init,
         "Initialize processor with sample rate",
         py::arg("sample_rate"))

    // Processing - convert between numpy and C++ vectors
    .def("process",
         [](ExampleProcessor& self, py::list inputs) -> py::list {
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
    .def("get_num_inputs", &ExampleProcessor::get_num_inputs,
         "Get number of input channels")
    .def("get_num_outputs", &ExampleProcessor::get_num_outputs,
         "Get number of output channels")
    .def("get_sample_rate", &ExampleProcessor::get_sample_rate,
         "Get current sample rate")

    // Parameters
    .def("set_param", &ExampleProcessor::set_param,
         "Set parameter value by name",
         py::arg("name"), py::arg("value"))
    .def("get_param", &ExampleProcessor::get_param,
         "Get parameter value by name",
         py::arg("name"))
    .def("get_param_names", &ExampleProcessor::get_param_names,
         "Get list of all parameter names");
}
