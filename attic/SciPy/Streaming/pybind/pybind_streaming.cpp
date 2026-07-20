
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>

#include <cstdint>
#include <vector>
#include <math.h>

#include "../Daisy/TryStreaming/blocks.h"

using std::vector;
using std::copy;

namespace py = pybind11;

namespace AWV {

#include "../Daisy/TryStreaming/py_gen.cpp"

typedef py::array_t<float, py::array::c_style | py::array::forcecast> pyFloatArray;

template <typename T>
py::array_t<T, py::array::c_style | py::array::forcecast> ToNumpyArray(T* params, size_t cnt) {  
  auto output = py::array_t<T, py::array::c_style | py::array::forcecast>(cnt);
  T* obase_ptr = reinterpret_cast<T*>(output.request().ptr);
  copy(params, params + cnt, obase_ptr);
  return output;
}

pyFloatArray get_buffer(int buf_no) {
  Buffer buf = buffer_pool.buffers[buf_no];
  float* ptr = &buf.data[0];
  return ToNumpyArray(ptr, buf.size);
}

PYBIND11_MODULE(pybind_streaming, m) {
  m.doc() = "streaming demo plugin"; // optional module docstring

  m.def("add_buffer", &add_buffer, "create new buffer in buffer pool",
    py::arg("bufsize"));

  m.def("get_buffer", &get_buffer, "retrieve contents of buffer as numpy array",
    py::arg("buf_idx"));

  m.def("graph_init", &graph_init);
  m.def("graph_proc", &graph_proc);
    
  py::class_<Pin>(m, "Pin")
    .def(py::init<>())
    .def_readwrite("fs", &Pin::fs)
    .def_readwrite("n_chans", &Pin::n_chans)
    .def_readwrite("bufsiz", &Pin::bufsiz);

  py::class_<Block>(m, "Block")
    .def("set_signal_specs", &Block::set_signal_specs);

  py::class_<SingleChanWrapper, Block>(m, "SingleChanWrapper")
    .def(py::init<float>())
    .def("assign_buffer", &SingleChanWrapper::assign_buffer)
    .def("init", &SingleChanWrapper::init)
    .def("proc", &SingleChanWrapper::proc)
    .def_readwrite("buffers", &SingleChanWrapper::buffers)
    .def_readwrite("pins", &SingleChanWrapper::pins)
    .def_readwrite("bufsiz", &SingleChanWrapper::bufsiz);

  py::class_<SineBlock, SingleChanWrapper>(m, "SineBlock")
    .def(py::init<float>())
    .def_readwrite("freq", &SineBlock::freq)
    .def_readwrite("incr", &SineBlock::incr);

  py::class_<GainBlock, SingleChanWrapper>(m, "GainBlock")
    .def(py::init<float>())
    .def_readwrite("gain", &GainBlock::gain);

}

}

