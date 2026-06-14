# Build the generated pitch_shifter pybind module.
# Run from Python_STM32/projects/pitch_shifter/ (scipy conda env for pybind11):
#   make -f pitch_shifter.make                 # build (default CHUNK_SIZE)
#   make -f pitch_shifter.make CHUNK_SIZE=...   # override native buffer size
#   make -f pitch_shifter.make clean
#
# All build rules (Faust generation, graph-header generation, -MMD dependency
# tracking, compile + link) live in the shared fragment; this file just
# declares the project's parts. See ../../python/graph_build.mk.
#
# (faust.make in ../../python/ remains the separate tool for building a
# standalone single-block pybind module; the graph build does not use it.)

MODULE       = pitch_shifter
FAUST_BLOCKS = input_lpf zero_crossing_detector attack_detector triple_tap_delay
DSP_CPP      = harmonic_rejector.cpp loop_controller.cpp mixer3.cpp

include ../../python/graph_build.mk
