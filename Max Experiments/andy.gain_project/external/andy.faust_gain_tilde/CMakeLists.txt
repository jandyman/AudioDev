cmake_minimum_required(VERSION 3.19)

# CONFIGURABLE SDK PATH
# Priority: 1) CMake command line, 2) Environment variable, 3) Default
# Set via: cmake -DMAX_SDK_PATH=/path/to/sdk ..
# Or: export MAX_SDK_PATH=/path/to/sdk
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
# (Without these, SDK assumes project is inside max-sdk/source/)
set(C74_SUPPORT_DIR "${C74_MAX_SDK_PATH}/source/max-sdk-base/c74support")
set(C74_LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/../../../objects")

# Build for both Intel and Apple Silicon (universal binary)
set(CMAKE_OSX_ARCHITECTURES "x86_64;arm64")

# Include Max's pre-target setup (sets up variables, compiler flags, etc.)
include("${C74_MAX_SDK_PATH}/source/max-sdk-base/script/max-pretarget.cmake")

# Include directories for Max and MSP headers
include_directories(
  "${CMAKE_CURRENT_BINARY_DIR}"
  "${C74_SUPPORT_DIR}"
  "${MAX_SDK_INCLUDES}"
  "${MAX_SDK_MSP_INCLUDES}"
)

# Faust configuration
set(FAUST_DSP_FILE "${CMAKE_CURRENT_SOURCE_DIR}/gain.dsp")
set(FAUST_CPP_FILE "${CMAKE_CURRENT_BINARY_DIR}/faust_gain.cpp")

# Custom command to compile Faust to C++
add_custom_command(
  OUTPUT ${FAUST_CPP_FILE}
  COMMAND faust
    -lang cpp
    -double
    -vec
    -lv 0
    -cn FaustGain
    -o ${FAUST_CPP_FILE}
    ${FAUST_DSP_FILE}
  DEPENDS ${FAUST_DSP_FILE}
  COMMENT "Compiling Faust DSP to C++ (vectorized, double precision)"
  VERBATIM
)

# Add custom target to ensure Faust compilation happens
add_custom_target(faust_compile DEPENDS ${FAUST_CPP_FILE})

# Add the external as a MODULE (loadable library/bundle)
# Note: faust_gain.cpp is #included in faust_gain_tilde.cpp, so don't add it as a separate source
add_library(
  ${PROJECT_NAME}
  MODULE
  faust_gain_tilde.cpp
)

# Ensure Faust compilation happens before building external
add_dependencies(${PROJECT_NAME} faust_compile)

# Include Max's post-target setup (handles bundle creation, linking, etc.)
include("${C74_MAX_SDK_PATH}/source/max-sdk-base/script/max-posttarget.cmake")
