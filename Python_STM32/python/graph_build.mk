# Shared build rules for a generated graph-based pybind module.
#
# `include` this from a project makefile in Python_STM32/projects/<name>/,
# AFTER declaring:
#   MODULE       — graph/module base name. The graph is $(MODULE).graph, the
#                  generated header build/generated/$(MODULE).h, the pybind glue
#                  pybind_$(MODULE).cpp, the module build/pybind_$(MODULE)<suffix>.
#   FAUST_BLOCKS — Faust block names; each <name>.dsp compiles to build/<name>.cpp
#                  and is #included by the generated header.
#   DSP_CPP      — hand-written C++ block sources (the @block marker lives in the
#                  .cpp; the sibling .h is what the generated header #includes).
# Optional:
#   CHUNK_SIZE   — native ring-buffer size (default 1048576).
#
# Builds entirely from the project directory (run under the scipy conda env so
# `python3 -m pybind11` resolves). Header dependencies are tracked automatically
# via clang -MMD, so editing any source — .dsp, .graph, block .cpp, or any
# header it transitively #includes — rebuilds exactly what depends on it.
#
# Assumes the project lives two levels below Python_STM32 (so ../../python and
# ../../dsp_faust resolve from the project dir).

CHUNK_SIZE ?= 1048576

GRAPH    = $(MODULE).graph
HEADER   = build/generated/$(MODULE).h
DOC      = build/generated/$(MODULE).md
PYBIND   = pybind_$(MODULE).cpp
COMPILER = ../../python/graph_compiler.py

# Translation units linked into the module: the pybind glue + hand-written
# blocks. (Faust blocks are #included by the generated header, so they compile
# as part of $(PYBIND)'s object — captured via -MMD, not listed here.)
SRC = $(PYBIND) $(DSP_CPP)
OBJ = $(addprefix build/,$(SRC:.cpp=.o))
DEP = $(OBJ:.o=.d)

FAUST_DSP = $(addsuffix .dsp,$(FAUST_BLOCKS))
FAUST_CPP = $(addprefix build/,$(addsuffix .cpp,$(FAUST_BLOCKS)))

# Sources graph_compiler reads @block markers from (Faust markers in the .dsp,
# hand-written markers in the .cpp).
BLOCK_DEFS = $(FAUST_DSP) $(DSP_CPP)

INCLUDE := $(shell python3 -m pybind11 --includes) \
           -I. \
           -I../../python/bindings \
           -I../../dsp_faust \
           -Ibuild \
           -Ibuild/generated
CXXFLAGS := -O2 -Wall -std=c++17 -fPIC -DCHUNK_SIZE=$(CHUNK_SIZE)
LDFLAGS  := -shared -undefined dynamic_lookup
SUFFIX   := $(shell python3-config --extension-suffix)
TARGET   := build/pybind_$(MODULE)$(SUFFIX)

.DEFAULT_GOAL := target
target: $(TARGET)

build build/generated:
	@mkdir -p $@

# Faust block: regenerate C++ whenever its .dsp changes. -cn sets the class
# name the generated header instantiates (new <name>()). Faust already searches
# the .dsp's own directory for any project-local .lib imports.
build/%.cpp: %.dsp | build
	faust -lang cpp -cn $* -o $@ $<
	@echo "Faust compiled: $< -> $@"

$(HEADER): $(GRAPH) $(BLOCK_DEFS) $(COMPILER) | build/generated
	python3 $(COMPILER) $(GRAPH) $(HEADER)

# Documentation: assemble the per-graph intro + each block's sibling .md (in
# topological order) into build/generated/$(MODULE).md. Not built by default;
# run `make -f <graph>.make doc`. Depends on every .md in the project folder.
doc: $(DOC)
$(DOC): $(GRAPH) $(BLOCK_DEFS) $(wildcard *.md) $(COMPILER) | build/generated
	python3 $(COMPILER) --doc $(GRAPH) $(DOC)

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
	rm -f $(HEADER) $(DOC) $(FAUST_CPP) $(OBJ) $(DEP) $(TARGET)
	rm -rf $(TARGET).dSYM

# The Faust cpp are made by a pattern rule and referenced only as order-only
# prerequisites, so make would treat them as intermediate and delete them after
# a build — forcing a spurious full regen + relink on the next invocation. Mark
# them secondary so they persist.
.SECONDARY: $(FAUST_CPP)

-include $(DEP)

.PHONY: target doc clean
