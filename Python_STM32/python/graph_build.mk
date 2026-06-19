# Shared build rules for a generated graph-based pybind module.
#
# `include` this from a project makefile in Python_STM32/projects/<name>/,
# AFTER declaring:
#   MODULE       — graph/module base name. The graph is $(MODULE).graph, the
#                  generated header build/generated/$(MODULE).h, the module
#                  build/pybind_$(MODULE)<suffix>. The pybind glue is generated
#                  from a shared template (no hand-written pybind_*.cpp).
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
COMPILER = ../../python/graph_compiler.py

# The pybind glue is NOT hand-written — it's generated from a single graph-
# agnostic template (sed-filled with module/class names), so every project gets
# the same probe/process_chunk API for free. See pybind_graph_module.cpp.template.
PYBIND_TEMPLATE = ../../python/bindings/pybind_graph_module.cpp.template
PYBIND_GEN = build/pybind_$(MODULE).cpp
PYBIND_OBJ = build/pybind_$(MODULE).o

# Objects: the generated pybind glue + the hand-written C++ blocks. (Faust blocks
# are #included by the generated header, so they compile as part of the pybind
# object — captured via -MMD, not listed here.)
BLOCK_OBJ = $(addprefix build/,$(DSP_CPP:.cpp=.o))
OBJ = $(PYBIND_OBJ) $(BLOCK_OBJ)
DEP = $(OBJ:.o=.d)

FAUST_DSP = $(addsuffix .dsp,$(FAUST_BLOCKS))
FAUST_CPP = $(addprefix build/,$(addsuffix .cpp,$(FAUST_BLOCKS)))

# Sources graph_compiler reads @block markers from (Faust markers in the .dsp,
# hand-written markers in the .cpp).
BLOCK_DEFS = $(FAUST_DSP) $(DSP_CPP)

# Shared graph-block sources live under dsp_cpp/{src,include} — a STANDING source
# location (like dsp_faust). A project uses a shared C++ block by listing its
# basename in DSP_CPP and adding (include-dir ../../dsp_cpp/src) to its .graph so
# the compiler discovers the @block; the .cpp is found here via vpath, the .h via
# the include path below.
#
# BLOCK_DIRS (optional): ADDITIONAL dirs for genuinely cross-project block sources
# not yet promoted to dsp_cpp. Same treatment (include path + .cpp search path).
BLOCK_DIRS ?=
vpath %.cpp ../../dsp_cpp/src $(BLOCK_DIRS)

INCLUDE := $(shell python3 -m pybind11 --includes) \
           -I. \
           -I../../python/bindings \
           -I../../dsp_faust \
           -I../../dsp_cpp/include \
           -Ibuild \
           -Ibuild/generated \
           $(addprefix -I,$(BLOCK_DIRS))
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

# Generate the pybind glue from the shared template: substitute the module name,
# the generated-header filename, and the Python-visible class name.
$(PYBIND_GEN): $(PYBIND_TEMPLATE) | build
	sed -e 's/__MODULE_NAME__/pybind_$(MODULE)/g' \
	    -e 's/__GRAPH_HEADER__/$(MODULE).h/g' \
	    -e 's/__GRAPH_PYNAME__/$(MODULE)/g' \
	    $(PYBIND_TEMPLATE) > $(PYBIND_GEN)

# Compile each TU to an object, emitting a .d of its header dependencies
# (-MMD: user headers only; -MP: phony targets so a deleted header won't wedge
# the build). The order-only prereqs guarantee the generated sources EXIST for
# a clean first build; the .d files (included below) drive rebuilds when those
# generated files — or any header — subsequently change.
$(PYBIND_OBJ): $(PYBIND_GEN) | $(HEADER) $(FAUST_CPP) build
	clang++ -target arm64-apple-macos $(CXXFLAGS) -MMD -MP $(INCLUDE) -c $< -o $@

build/%.o: %.cpp | $(HEADER) $(FAUST_CPP) build
	clang++ -target arm64-apple-macos $(CXXFLAGS) -MMD -MP $(INCLUDE) -c $< -o $@

$(TARGET): $(OBJ)
	clang++ -target arm64-apple-macos $(LDFLAGS) $(OBJ) -o $(TARGET)
	@echo "Built $(TARGET) (CHUNK_SIZE=$(CHUNK_SIZE))"

clean:
	rm -f $(HEADER) $(FAUST_CPP) $(PYBIND_GEN) $(OBJ) $(DEP) $(TARGET)
	rm -rf $(TARGET).dSYM

# The Faust cpp are made by a pattern rule and referenced only as order-only
# prerequisites, so make would treat them as intermediate and delete them after
# a build — forcing a spurious full regen + relink on the next invocation. Mark
# them secondary so they persist.
.SECONDARY: $(FAUST_CPP)

-include $(DEP)

.PHONY: target clean
