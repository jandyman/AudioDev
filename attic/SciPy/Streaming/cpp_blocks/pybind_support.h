#pragma once
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>

#include <cstdint>
#include <vector>
#include <math.h>

using std::vector;
using std::copy;

namespace py = pybind11;

template <typename T> 
std::vector<T> np_to_vec(py::array_t<T> input_array) {
  auto buf = input_array.unchecked();  // No bounds checking
  size_t size = buf.size();

  std::vector<T> vec(size);
  memcpy(&vec[0], &buf[0], size * sizeof(T));
  return vec;
}

template <typename T> 
py::array vec_to_np(const std::vector<T>& vec) {
  return py::array(vec.size(), vec.data());
}

template <typename T> 
std::vector<std::vector<T>> np_list_to_vect_of_vect(py::list numpy_list) {
  std::vector<std::vector<T>> result;

  for (py::handle obj : numpy_list) {
    py::array_t<T> arr = py::cast<py::array_t<T>>(obj);
    py::buffer_info buf_info = arr.request();

    if (buf_info.ndim != 1) {
      throw std::runtime_error("Each numpy array must be 1-dimensional");
    }

    T* ptr = static_cast<T*>(buf_info.ptr);
    std::vector<T> vec(ptr, ptr + buf_info.shape[0]);
    result.push_back(std::move(vec));
  }

  return result;
}

// Function to convert std::vector<std::vector<T>> to Python list of NumPy arrays
template <typename T> 
py::list vect_of_vect_to_list_of_np(const std::vector<std::vector<T>>& vec) {
  py::list result;
  for (const auto& inner_vec : vec) {
    result.append(py::array_t<T>(inner_vec.size(), inner_vec.data()));
  }
  return result;
}

template <typename T> 
void copy_vec_to_np(vector<T>& vec, py::array_t<T> a) {
  auto r = a.template mutable_unchecked<1>();  // No bounds checking
  for (py::ssize_t i = 0; i < r.shape(0); i++) {
    r(i) = vec[i];
  }
}

template <typename T> 
void cp_vec_vec_into_list_of_np(vector<vector<T>>& vec_vec, py::list np_list) {
  for (int j=0; j<vec_vec.size(); j++) {
    auto obj = np_list[j];
    py::array_t<T> arr = py::cast<py::array_t<T>>(obj);
    auto r = arr.template mutable_unchecked<1>();  // No bounds checking
    for (py::ssize_t i = 0; i < r.shape(0); i++) {
      r(i) = vec_vec[j][i];
    }
  }
}

// void vector_modifier(vector<vector<float>>& x) {
//   for (auto& o : x) {
//     for (int i=0; i<o.size(); i++) {
//       o[i] *= 5;
//     }
//   }
// }

// void test_modify_list_of_numpy(py::list arg) {
//   vector<vector<float>> vec_vec = np_list_to_vect_of_vect<float>(arg);
//   vector_modifier(vec_vec);
//   for (int j=0; j<vec_vec.size(); j++) {
//     auto obj = arg[j];
//     py::array_t<float> arr = py::cast<py::array_t<float>>(obj);
//     auto r = arr.mutable_unchecked<1>();  // No bounds checking
//     for (py::ssize_t i = 0; i < r.shape(0); i++) {
//       r(i) = vec_vec[j][i] * 4;
//     }
//   }
// }
