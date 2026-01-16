cmake_minimum_required(VERSION 3.19)

#############################################################
# dual_tap_delay~ Max External
# Wraps dual_tap_delay.dsp from dsp_library (Faust-generated)
#############################################################

# Project name (SDK will convert dual_tap_delay_tilde → dual_tap_delay~)
project(dual_tap_delay_tilde)

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
# FAUST CONFIGURATION
#############################################################

# Path to Faust DSP file in shared library
set(FAUST_DSP_FILE "${CMAKE_CURRENT_SOURCE_DIR}/../../dsp_library/faust/dual_tap_delay.dsp")
set(FAUST_CPP_FILE "${CMAKE_CURRENT_BINARY_DIR}/faust_dual_tap_delay.cpp")

# Include directories
include_directories(
    "${CMAKE_CURRENT_BINARY_DIR}"
    "${C74_SUPPORT_DIR}"
    "${MAX_SDK_INCLUDES}"
    "${MAX_SDK_MSP_INCLUDES}"
)

# Custom command to compile Faust to C++
add_custom_command(
    OUTPUT ${FAUST_CPP_FILE}
    COMMAND faust
        -lang cpp
        -double
        -vec
        -lv 0
        -cn FaustDualTapDelay
        -o ${FAUST_CPP_FILE}
        ${FAUST_DSP_FILE}
    DEPENDS ${FAUST_DSP_FILE}
    COMMENT "Compiling Faust DSP to C++ (vectorized, double precision)"
    VERBATIM
)

# Add custom target to ensure Faust compilation happens
add_custom_target(faust_compile DEPENDS ${FAUST_CPP_FILE})

#############################################################
# BUILD CONFIGURATION
#############################################################

# Source files: Max wrapper (generated Faust C++ is #included)
add_library(
    ${PROJECT_NAME}
    MODULE
    dual_tap_delay_tilde.cpp
)

# Ensure Faust compilation happens before building external
add_dependencies(${PROJECT_NAME} faust_compile)

# Include Max's post-target setup
include("${C74_MAX_SDK_PATH}/source/max-sdk-base/script/max-posttarget.cmake")

# Print configuration summary
message(STATUS "")
message(STATUS "dual_tap_delay~ Configuration:")
message(STATUS "  Max SDK: ${C74_MAX_SDK_PATH}")
message(STATUS "  Faust DSP: ${FAUST_DSP_FILE}")
message(STATUS "  Generated C++: ${FAUST_CPP_FILE}")
message(STATUS "  Output: ${C74_LIBRARY_OUTPUT_DIRECTORY}")
message(STATUS "  Architectures: ${CMAKE_OSX_ARCHITECTURES}")
message(STATUS "")
