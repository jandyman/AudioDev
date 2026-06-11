# Build the generated PitchShifter pybind module.
# Run from Python_STM32/projects/pitch_shifter/.
#
# Usage:
#   make -f pitch_shifter.make                 # default CHUNK_SIZE=524288
#   make -f pitch_shifter.make CHUNK_SIZE=1000000
#   make -f pitch_shifter.make clean
#
# Prerequisite: the four Faust-emitted build/<name>.cpp must already exist locally
# in build/. Generate them by running (from this directory):
#   make -f ../../python/faust.make DSP=input_lpf              DSP_LIB_DIR=$(CURDIR)
#   make -f ../../python/faust.make DSP=zero_crossing_detector DSP_LIB_DIR=$(CURDIR)
#   make -f ../../python/faust.make DSP=attack_detector        DSP_LIB_DIR=$(CURDIR)
#   make -f ../../python/faust.make DSP=triple_tap_delay       DSP_LIB_DIR=$(CURDIR)
# (Some include paths in this Makefile reference ../../python/ as a transitional
# bridge until the host-side tools move to ../../tools/ in a later reorg step.)

CHUNK_SIZE ?= 1048576

GRAPH       = pitch_shifter.graph
HEADER      = build/generated/pitch_shifter.h
PYBIND      = pybind_pitch_shifter.cpp
DSP_CPP     = harmonic_rejector.cpp loop_controller.cpp mixer3.cpp
COMPILER    = ../../python/graph_compiler.py

INCLUDE := $(shell python3 -m pybind11 --includes) \
           -I. \
           -I../../python/bindings \
           -I../../python/build \
           -I../../dsp_faust \
           -Ibuild \
           -Ibuild/generated
FLAG    := -O2 -Wall -shared -std=c++17 -undefined dynamic_lookup -fPIC -DCHUNK_SIZE=$(CHUNK_SIZE)
SUFFIX  := $(shell python3-config --extension-suffix)
TARGET  := build/pybind_pitch_shifter$(SUFFIX)

target: $(TARGET)

$(HEADER): $(GRAPH) $(COMPILER)
	@mkdir -p build/generated
	python3 $(COMPILER) $(GRAPH) $(HEADER)

$(TARGET): $(HEADER) $(PYBIND) $(DSP_CPP)
	clang++ -target arm64-apple-macos $(FLAG) $(INCLUDE) $(PYBIND) $(DSP_CPP) -o $(TARGET)
	@echo "Built $(TARGET) (CHUNK_SIZE=$(CHUNK_SIZE))"

clean:
	rm -f $(HEADER) $(TARGET)
	rm -rf $(TARGET).dSYM

.PHONY: target clean
