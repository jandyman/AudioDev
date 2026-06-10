# Build the generated PitchShifter pybind module.
# Run from Python_STM32/python/.
#
# Usage:
#   make -f pitch_shifter.make                 # default CHUNK_SIZE=524288
#   make -f pitch_shifter.make CHUNK_SIZE=1000000
#   make -f pitch_shifter.make clean
#
# Prerequisite: the four Faust-emitted build/<name>.cpp must already exist in build/.
# Rebuild them with (run from python/):
#   make -f faust.make DSP=input_lpf              DSP_LIB_DIR=pitch_shifter_demo
#   make -f faust.make DSP=zero_crossing_detector DSP_LIB_DIR=pitch_shifter_demo
#   make -f faust.make DSP=attack_detector        DSP_LIB_DIR=pitch_shifter_demo
#   make -f faust.make DSP=triple_tap_delay       DSP_LIB_DIR=pitch_shifter_demo

CHUNK_SIZE ?= 524288

GRAPH       = pitch_shifter_demo/pitch_shifter.graph
HEADER      = build/generated/pitch_shifter.h
PYBIND      = bindings/pybind_pitch_shifter.cpp
DSP_CPP     = pitch_shifter_demo/harmonic_rejector.cpp pitch_shifter_demo/loop_controller.cpp pitch_shifter_demo/mixer3.cpp
COMPILER    = graph_compiler.py

INCLUDE := $(shell python3 -m pybind11 --includes) -Ibindings -Ipitch_shifter_demo -I../dsp_faust -Ibuild -Ibuild/generated
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
