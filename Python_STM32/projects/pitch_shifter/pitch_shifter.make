# Build the generated pitch_shifter pybind module.
# Run from Python_STM32/projects/pitch_shifter/.
#
# Usage:
#   make -f pitch_shifter.make                 # default CHUNK_SIZE=1048576
#   make -f pitch_shifter.make CHUNK_SIZE=1000000
#   make -f pitch_shifter.make clean
#
# Self-contained: regenerates the per-block Faust C++ from the .dsp sources and
# the graph header, then compiles + links. Header dependencies are tracked
# automatically (clang -MMD emits a .d per object listing every header it
# #includes, transitively — including the generated graph header and the Faust
# .cpp it pulls in). So editing ANY source (.dsp, .graph, block .cpp/.h, or a
# shared support header) rebuilds exactly what depends on it. No hand-maintained
# header lists, no manual faust step, no cross-directory invocation.
#
# (faust.make in ../../python/ remains the separate tool for building a
# standalone single-block pybind module; the graph build below does not use it.)

CHUNK_SIZE ?= 1048576

GRAPH    = pitch_shifter.graph
HEADER   = build/generated/pitch_shifter.h
COMPILER = ../../python/graph_compiler.py

# Translation units linked into the module: the pybind glue + hand-written
# C++ blocks. (The Faust blocks are #included by the generated header, so they
# compile as part of pybind_pitch_shifter.o — captured via -MMD, not listed.)
SRC = pybind_pitch_shifter.cpp harmonic_rejector.cpp loop_controller.cpp mixer3.cpp
OBJ = $(addprefix build/,$(SRC:.cpp=.o))
DEP = $(OBJ:.o=.d)

# Faust blocks: <name>.dsp -> build/<name>.cpp, #included by the graph header.
FAUST_BLOCKS = input_lpf zero_crossing_detector attack_detector triple_tap_delay
FAUST_DSP    = $(addsuffix .dsp,$(FAUST_BLOCKS))
FAUST_CPP    = $(addprefix build/,$(addsuffix .cpp,$(FAUST_BLOCKS)))

# Block-definition sources graph_compiler reads @block markers from (Faust
# markers live in the .dsp, hand-written markers in the .cpp).
BLOCK_DEFS = $(FAUST_DSP) harmonic_rejector.cpp loop_controller.cpp mixer3.cpp

INCLUDE := $(shell python3 -m pybind11 --includes) \
           -I. \
           -I../../python/bindings \
           -I../../dsp_faust \
           -Ibuild \
           -Ibuild/generated
CXXFLAGS := -O2 -Wall -std=c++17 -fPIC -DCHUNK_SIZE=$(CHUNK_SIZE)
LDFLAGS  := -shared -undefined dynamic_lookup
SUFFIX   := $(shell python3-config --extension-suffix)
TARGET   := build/pybind_pitch_shifter$(SUFFIX)

target: $(TARGET)

build build/generated:
	@mkdir -p $@

# Faust block: regenerate C++ whenever its .dsp changes. -cn sets the class
# name the graph header instantiates (new <name>()). Faust already searches the
# .dsp's own directory for any project-local .lib imports.
build/%.cpp: %.dsp | build
	faust -lang cpp -cn $* -o $@ $<
	@echo "Faust compiled: $< -> $@"

$(HEADER): $(GRAPH) $(BLOCK_DEFS) $(COMPILER) | build/generated
	python3 $(COMPILER) $(GRAPH) $(HEADER)

# Compile each TU to an object, emitting a .d of its header dependencies
# (-MMD: user headers only; -MP: phony targets so a deleted header won't wedge
# the build). The order-only prereqs guarantee the generated sources EXIST for
# a clean first build; the .d files (included below) drive rebuilds when those
# generated files — or any header — subsequently change.
build/%.o: %.cpp | $(HEADER) $(FAUST_CPP) build
	clang++ -target arm64-apple-macos $(CXXFLAGS) -MMD -MP $(INCLUDE) -c $< -o $@

$(TARGET): $(OBJ)
	clang++ -target arm64-apple-macos $(LDFLAGS) $(OBJ) -o $(TARGET)
	@echo "Built $(TARGET) (CHUNK_SIZE=$(CHUNK_SIZE))"

clean:
	rm -f $(HEADER) $(FAUST_CPP) $(OBJ) $(DEP) $(TARGET)
	rm -rf $(TARGET).dSYM

-include $(DEP)

.PHONY: target clean
