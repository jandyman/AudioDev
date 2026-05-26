# Build the native EQ pybind11 module.
# Run from Python_STM32/python/ with the scipy conda env active:
#   make -f eq.make
#   make -f eq.make clean

DSP_DIR  = ../dsp_cpp
BIND_DIR = bindings
OUTDIR   = build
INCLUDE  := $(shell python3 -m pybind11 --includes) -I$(DSP_DIR)/include
FLAGS    = -O2 -Wall -shared -std=c++14 -undefined dynamic_lookup -fPIC
SUFFIX   := $(shell python3-config --extension-suffix)
TARGET   = pybind_eq
CPP_FILES = $(BIND_DIR)/pybind_eq.cpp $(DSP_DIR)/src/biquad.cpp $(DSP_DIR)/src/eq_design.cpp

all: $(OUTDIR)/$(TARGET)$(SUFFIX)

$(OUTDIR):
	@mkdir -p $(OUTDIR)

$(OUTDIR)/$(TARGET)$(SUFFIX): $(CPP_FILES) $(DSP_DIR)/include/biquad.h | $(OUTDIR)
	clang++ -target arm64-apple-macos $(FLAGS) $(INCLUDE) $(CPP_FILES) -o $@
	@echo "Built $@"

clean:
	rm -f $(OUTDIR)/$(TARGET)*.so $(OUTDIR)/*.pyi
	rm -rf $(OUTDIR)/*.dSYM

.PHONY: all clean
