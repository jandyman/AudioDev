# Build the generated YIN pybind module.
# Run from Python_STM32/projects/yin/ (scipy conda env for pybind11):
#   make -f yin.make                 # build (default CHUNK_SIZE)
#   make -f yin.make CHUNK_SIZE=...   # override native buffer size
#   make -f yin.make clean
#
# All build rules (graph-header generation, -MMD dependency tracking, compile +
# link) live in the shared fragment; this file just declares the project's
# parts. See ../../python/graph_build.mk. (No Faust blocks here — the decimator
# and YIN core are hand-written C++.)

MODULE  = yin
DSP_CPP = yin_detector.cpp

include ../../python/graph_build.mk
