cmake_minimum_required(VERSION 2.8.12)
project(block_test)

set(COMMON ${PROJECT_SOURCE_DIR}/../..)
find_package(pybind11 CONFIG REQUIRED)
pybind11_add_module(${PROJECT_NAME} wrapper.cpp)
target_include_directories(${PROJECT_NAME} PUBLIC ${COMMON}/DSP ${COMMON}/GenericDSP)


