# Faust-to-Python Build System
# Compiles a Faust .dsp file to a pybind11 Python module with stateful compute()
#
# Usage:
#   make -f faust.make DSP=attack_detector
#   make -f faust.make DSP=dual_tap_delay
#
# This will:
#   1. Run faust compiler: .dsp -> C++
#   2. Generate pybind11 binding from template
#   3. Compile to .so Python module
#
# The resulting module provides a CppProcessor-compatible interface
# (init, process, set_param, get_param) with persistent state.

# Input: DSP module name (without extension)
# e.g. DSP=attack_detector reads ../../dsp_library/faust/attack_detector.dsp

DSP_LIB_DIR = ../../dsp_library/faust
BINDINGS_DIR = ../bindings
TEMPLATE = $(BINDINGS_DIR)/pybind_faust_module.cpp.template

# Paths
DSP_FILE = $(DSP_LIB_DIR)/$(DSP).dsp
FAUST_CPP = faust_$(DSP).cpp
BINDING_CPP = pybind_faust_$(DSP).cpp
MODULE_NAME = pybind_faust_$(DSP)

# Convert DSP name to CamelCase class name: attack_detector -> FaustAttackDetector
FAUST_CLASS = $(shell echo $(DSP) | python3 -c "import sys; s=sys.stdin.read().strip(); print('Faust' + ''.join(w.capitalize() for w in s.split('_')))")

# Compiler settings
INCLUDE := $(shell python3 -m pybind11 --includes) -I$(BINDINGS_DIR) -I$(DSP_LIB_DIR) -I.
OPT = -O2
FLAG := -g $(OPT) -Wall -shared -std=c++17 -undefined dynamic_lookup -fPIC
SUFFIX := $(shell python3-config --extension-suffix)

target: $(MODULE_NAME)$(SUFFIX)

# Step 1: Compile Faust to C++
$(FAUST_CPP): $(DSP_FILE)
	faust -lang cpp -double -cn $(FAUST_CLASS) -o $(FAUST_CPP) $(DSP_FILE)
	@echo "Faust compiled: $(DSP_FILE) -> $(FAUST_CPP) (class: $(FAUST_CLASS))"

# Step 2: Generate pybind11 binding from template
$(BINDING_CPP): $(TEMPLATE) $(FAUST_CPP)
	sed -e 's/__MODULE_NAME__/$(MODULE_NAME)/g' \
	    -e 's/__FAUST_CLASS__/$(FAUST_CLASS)/g' \
	    -e 's/__FAUST_CPP_FILE__/$(FAUST_CPP)/g' \
	    -e 's/__DSP_NAME__/$(DSP)/g' \
	    $(TEMPLATE) > $(BINDING_CPP)
	@echo "Binding generated: $(BINDING_CPP)"

# Step 3: Compile to Python module
$(MODULE_NAME)$(SUFFIX): $(BINDING_CPP) $(FAUST_CPP)
	clang++ -target arm64-apple-macos $(FLAG) $(INCLUDE) $(BINDING_CPP) -o $(MODULE_NAME)$(SUFFIX)
	@echo ""
	@echo "Built $(MODULE_NAME)$(SUFFIX)"
	@echo "Import with: from build.$(MODULE_NAME) import $(FAUST_CLASS)"
	@echo ""

clean:
	rm -f faust_*.cpp pybind_faust_*.cpp pybind_faust_*.so
	rm -rf *.dSYM
	@echo "Cleaned Faust build artifacts"

.PHONY: target clean
