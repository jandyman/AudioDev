#pragma once
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>

#include <cstdint>
#include <vector>
#include <cmath>
#include <cstring>

using std::vector;
using std::copy;

namespace py = pybind11;

// Convert numpy array to std::vector
template <typename T>
std::vector<T> np_to_vec(py::array_t<T> input_array) {
  auto buf = input_array.unchecked();  // No bounds checking
  size_t size = buf.size();

  std::vector<T> vec(size);
  memcpy(&vec[0], &buf[0], size * sizeof(T));
  return vec;
}

// Convert std::vector to numpy array
template <typename T>
py::array vec_to_np(const std::vector<T>& vec) {
  return py::array(vec.size(), vec.data());
}

// Copy std::vector contents into existing numpy array (in-place)
template <typename T>
void copy_vec_to_np(const vector<T>& vec, py::array_t<T> a) {
  auto r = a.template mutable_unchecked<1>();  // No bounds checking
  for (py::ssize_t i = 0; i < r.shape(0); i++) {
    r(i) = vec[i];
  }
}

// Convert list of numpy arrays to vector of vectors
template <typename T>
std::vector<std::vector<T>> np_list_to_vec_of_vec(py::list numpy_list) {
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

// Convert vector of vectors to Python list of numpy arrays
template <typename T>
py::list vec_of_vec_to_np_list(const std::vector<std::vector<T>>& vec) {
  py::list result;
  for (const auto& inner_vec : vec) {
    result.append(py::array_t<T>(inner_vec.size(), inner_vec.data()));
  }
  return result;
}

// Copy vector of vectors into existing list of numpy arrays (in-place)
template <typename T>
void copy_vec_of_vec_to_np_list(const vector<vector<T>>& vec_vec, py::list np_list) {
  for (size_t j = 0; j < vec_vec.size(); j++) {
    auto obj = np_list[j];
    py::array_t<T> arr = py::cast<py::array_t<T>>(obj);
    auto r = arr.template mutable_unchecked<1>();  // No bounds checking
    for (py::ssize_t i = 0; i < r.shape(0); i++) {
      r(i) = vec_vec[j][i];
    }
  }
}
