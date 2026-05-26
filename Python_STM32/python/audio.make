# Pitch Shifter - Build System for C++ Modules
# Run from Python_STM32/python/. Outputs go to build/.
#
# Usage: make -f audio.make TARGET=harmonic_rejector
#        make -f audio.make TARGET=loop_controller
#        make -f audio.make TARGET=mixer2

BINDINGS_DIR = bindings
DSP_LIB_DIR  = ../dsp_cpp
OUTDIR       = build
INCLUDE := $(shell python3 -m pybind11 --includes) -I$(BINDINGS_DIR) -I$(DSP_LIB_DIR)/include
OPT = -O2
FLAG := -g ${OPT} -Wall -shared -std=c++11 -undefined dynamic_lookup -fPIC
SUFFIX := $(shell python3-config --extension-suffix)
PY_TARGET = pybind_$(TARGET)
BINDINGS_CPP = $(BINDINGS_DIR)/$(PY_TARGET).cpp
DSP_CPP = $(DSP_LIB_DIR)/src/$(TARGET).cpp
CPP_FILES = $(BINDINGS_CPP) $(DSP_CPP)

target: | $(OUTDIR)
	clang++ -target arm64-apple-macos $(FLAG) $(INCLUDE) $(CPP_FILES) -o $(OUTDIR)/$(PY_TARGET)$(SUFFIX)
	@echo "Built $(OUTDIR)/$(PY_TARGET)$(SUFFIX)"
	@echo "Import with: from build.$(PY_TARGET) import *"

$(OUTDIR):
	@mkdir -p $(OUTDIR)

clean:
	rm -f $(OUTDIR)/*.so $(OUTDIR)/*.pyi
	rm -rf $(OUTDIR)/*.dSYM
	@echo "Cleaned $(OUTDIR)/"

.PHONY: target clean
