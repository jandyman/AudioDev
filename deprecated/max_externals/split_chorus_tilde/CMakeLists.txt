cmake_minimum_required(VERSION 3.19)

#############################################################
# split_chorus~ Max External
# Wraps SplitChorus from dsp_library (shared DSP code)
#############################################################

# Project name (SDK will convert split_chorus_tilde → split_chorus~)
project(split_chorus_tilde)

# CONFIGURABLE SDK PATH
if(NOT DEFINED MAX_SDK_PATH)
    if(DEFINED ENV{MAX_SDK_PATH})
        set(MAX_SDK_PATH "$ENV{MAX_SDK_PATH}")
        message(STATUS "Using MAX SDK from environment: ${MAX_SDK_PATH}")
    else()
        set(MAX_SDK_PATH "/Users/andy/max-sdk")
        message(STATUS "Using default MAX SDK path: ${MAX_SDK_PATH}")
    endif()
else()
    message(STATUS "Using MAX SDK from command line: ${MAX_SDK_PATH}")
endif()

set(C74_MAX_SDK_PATH "${MAX_SDK_PATH}")

# Override SDK defaults to make build location-independent
set(C74_SUPPORT_DIR "${C74_MAX_SDK_PATH}/source/max-sdk-base/c74support")
set(C74_LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/../../Max Experiments/objects")

# Build for both Intel and Apple Silicon (universal binary)
set(CMAKE_OSX_ARCHITECTURES "x86_64;arm64")

# Include Max's pre-target setup
include("${C74_MAX_SDK_PATH}/source/max-sdk-base/script/max-pretarget.cmake")

#############################################################
# DSP LIBRARY CONFIGURATION
#############################################################

# Path to shared DSP library
set(DSP_LIB_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../dsp_library/cpp")

# Include directories
include_directories(
    "${MAX_SDK_INCLUDES}"
    "${MAX_SDK_MSP_INCLUDES}"
    "${DSP_LIB_DIR}/include"
)

#############################################################
# BUILD CONFIGURATION
#############################################################

# Source files: Max wrapper + shared DSP code
add_library(
    ${PROJECT_NAME}
    MODULE
    split_chorus_tilde.cpp
    ${DSP_LIB_DIR}/src/split_chorus.cpp
)

# Include Max's post-target setup
include("${C74_MAX_SDK_PATH}/source/max-sdk-base/script/max-posttarget.cmake")

# Print configuration summary
message(STATUS "")
message(STATUS "split_chorus~ Configuration:")
message(STATUS "  Max SDK: ${C74_MAX_SDK_PATH}")
message(STATUS "  DSP Library: ${DSP_LIB_DIR}")
message(STATUS "  Output: ${C74_LIBRARY_OUTPUT_DIRECTORY}")
message(STATUS "  Architectures: ${CMAKE_OSX_ARCHITECTURES}")
message(STATUS "")
