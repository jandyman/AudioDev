# Build the generated PitchShifter pybind module.
# Run from Python_STM32/python/.
#
# Usage:
#   make -f pitch_shifter.make                 # default CHUNK_SIZE=524288
#   make -f pitch_shifter.make CHUNK_SIZE=1000000
#   make -f pitch_shifter.make clean
#
# Prerequisite: the four Faust pybind/cpp must already exist in build/ (run
# faust.make first if a clean checkout). The graph compiler runs every build.

CHUNK_SIZE ?= 524288

GRAPH       = pitch_shifter_demo/pitch_shifter.graph
HEADER      = build/generated/pitch_shifter.h
PYBIND      = bindings/pybind_pitch_shifter.cpp
DSP_CPP     = ../dsp_cpp/src/harmonic_rejector.cpp ../dsp_cpp/src/loop_controller.cpp ../dsp_cpp/src/mixer2.cpp
COMPILER    = graph_compiler.py

INCLUDE := $(shell python3 -m pybind11 --includes) -Ibindings -I../dsp_cpp/include -I../dsp_faust -Ibuild -Ibuild/generated
FLAG    := -O2 -Wall -shared -std=c++17 -undefined dynamic_lookup -fPIC -DCHUNK_SIZE=$(CHUNK_SIZE)
SUFFIX  := $(shell python3-config --extension-suffix)
TARGET  := build/pybind_pitch_shifter$(SUFFIX)

target: $(TARGET)

$(HEADER): $(GRAPH) $(COMPILER)
	python3 $(COMPILER) $(GRAPH) $(HEADER)

$(TARGET): $(HEADER) $(PYBIND) $(DSP_CPP)
	clang++ -target arm64-apple-macos $(FLAG) $(INCLUDE) $(PYBIND) $(DSP_CPP) -o $(TARGET)
	@echo "Built $(TARGET) (CHUNK_SIZE=$(CHUNK_SIZE))"

clean:
	rm -f $(HEADER) $(TARGET)
	rm -rf $(TARGET).dSYM

.PHONY: target clean
