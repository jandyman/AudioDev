# Faust-to-Python Build System
# Compiles a Faust .dsp file to a pybind11 Python module with stateful compute()
# Run from Python_STM32/python/. Outputs (generated cpp + .so) go to build/.
#
# Usage:
#   make -f faust.make DSP=attack_detector DSP_LIB_DIR=pitch_shifter_demo
#   make -f faust.make DSP=triple_tap_delay DSP_LIB_DIR=pitch_shifter_demo
#   make -f faust.make DSP=input_lpf       DSP_LIB_DIR=pitch_shifter_demo
#   make -f faust.make DSP=zero_crossing_detector DSP_LIB_DIR=pitch_shifter_demo
#
# DSP_LIB_DIR defaults to ../dsp_faust for backwards compatibility.
#
# This will:
#   1. Run faust compiler: .dsp -> build/<name>.cpp
#   2. Generate pybind11 binding from template -> build/pybind_<name>.cpp
#   3. Compile to build/pybind_<name>.so Python module

DSP_LIB_DIR ?= ../dsp_faust
BINDINGS_DIR = bindings
OUTDIR       = build
TEMPLATE = $(BINDINGS_DIR)/pybind_faust_module.cpp.template

DSP_FILE    = $(DSP_LIB_DIR)/$(DSP).dsp
FAUST_BASE  = $(DSP).cpp
FAUST_CPP   = $(OUTDIR)/$(FAUST_BASE)
BINDING_CPP = $(OUTDIR)/pybind_$(DSP).cpp
MODULE_NAME = pybind_$(DSP)

FAUST_CLASS = $(DSP)

INCLUDE := $(shell python3 -m pybind11 --includes) -I$(BINDINGS_DIR) -I../dsp_faust -I$(OUTDIR)
OPT = -O2
FLAG := -g $(OPT) -Wall -shared -std=c++17 -undefined dynamic_lookup -fPIC
SUFFIX := $(shell python3-config --extension-suffix)

target: $(OUTDIR)/$(MODULE_NAME)$(SUFFIX)

$(OUTDIR):
	@mkdir -p $(OUTDIR)

$(FAUST_CPP): $(DSP_FILE) | $(OUTDIR)
	faust -lang cpp -cn $(FAUST_CLASS) -o $(FAUST_CPP) $(DSP_FILE)
	@echo "Faust compiled: $(DSP_FILE) -> $(FAUST_CPP) (class: $(FAUST_CLASS))"

$(BINDING_CPP): $(TEMPLATE) $(FAUST_CPP)
	sed -e 's/__MODULE_NAME__/$(MODULE_NAME)/g' \
	    -e 's/__FAUST_CLASS__/$(FAUST_CLASS)/g' \
	    -e 's|__FAUST_CPP_FILE__|$(FAUST_BASE)|g' \
	    -e 's/__DSP_NAME__/$(DSP)/g' \
	    $(TEMPLATE) > $(BINDING_CPP)
	@echo "Binding generated: $(BINDING_CPP)"

$(OUTDIR)/$(MODULE_NAME)$(SUFFIX): $(BINDING_CPP) $(FAUST_CPP)
	clang++ -target arm64-apple-macos $(FLAG) $(INCLUDE) $(BINDING_CPP) -o $(OUTDIR)/$(MODULE_NAME)$(SUFFIX)
	@echo ""
	@echo "Built $(OUTDIR)/$(MODULE_NAME)$(SUFFIX)"
	@echo "Import with: from build.$(MODULE_NAME) import $(FAUST_CLASS)"
	@echo ""

clean:
	rm -f $(FAUST_CPP) $(BINDING_CPP) $(OUTDIR)/$(MODULE_NAME)$(SUFFIX)
	rm -rf $(OUTDIR)/$(MODULE_NAME)$(SUFFIX).dSYM
	@echo "Cleaned Faust build artifacts in $(OUTDIR)/"

.PHONY: target clean
