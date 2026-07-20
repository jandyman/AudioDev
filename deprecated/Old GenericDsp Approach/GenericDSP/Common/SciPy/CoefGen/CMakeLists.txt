cmake_minimum_required(VERSION 2.8.12)
project(coefgen)

find_package(pybind11 CONFIG REQUIRED)
pybind11_add_module(coefgen ${PROJECT_SOURCE_DIR}/../../DSP/CoefGen.cpp wrapper.cpp)
target_include_directories(coefgen PUBLIC ${PROJECT_SOURCE_DIR}/../../DSP)


