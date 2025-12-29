cmake_minimum_required(VERSION 3.19)

#############################################################
# LOCATION-INDEPENDENT MAX EXTERNAL BUILD CONFIGURATION
#
# This CMakeLists.txt eliminates all location dependencies:
# - Project can exist ANYWHERE on your system
# - Build output stays within the project folder
# - Only the SDK path below needs to be configured
#
# See BUILD_DEPENDENCIES.md for full explanation
#############################################################

# ONLY REQUIRED PATH: Absolute path to Max SDK
set(C74_MAX_SDK_PATH "/Users/andy/Dropbox/Developer/AudioDev/max-sdk")

# Override SDK defaults to make build location-independent
# (Without these, SDK assumes project is inside max-sdk/source/)
set(C74_SUPPORT_DIR "${C74_MAX_SDK_PATH}/source/max-sdk-base/c74support")
set(C74_LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/../../../objects")

# Build for both Intel and Apple Silicon (universal binary)
set(CMAKE_OSX_ARCHITECTURES "x86_64;arm64")

# Include Max's pre-target setup (sets up variables, compiler flags, etc.)
include("${C74_MAX_SDK_PATH}/source/max-sdk-base/script/max-pretarget.cmake")

#############################################################
# MAX EXTERNAL PROJECT
#############################################################

# Include directories for Max and MSP headers
include_directories(
    "${MAX_SDK_INCLUDES}"
    "${MAX_SDK_MSP_INCLUDES}"
)

# Add the external as a MODULE (loadable library/bundle)
add_library(
    ${PROJECT_NAME}
    MODULE
    gain_tilde.cpp
)

# Include Max's post-target setup (handles bundle creation, linking, etc.)
include("${C74_MAX_SDK_PATH}/source/max-sdk-base/script/max-posttarget.cmake")
