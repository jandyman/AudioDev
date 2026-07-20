SRC_DIR = ../cpp_blocks
INCLUDE := $(shell python3 -m pybind11 --includes) -I$(SRC_DIR)
INCLUDE += -I/Users/andy/CMSIS-DSP/CMSIS-DSP/Include/dsp
INCLUDE += -I/Users/andy/CMSIS-DSP/CMSIS-DSP/Include
OPT = -O2
FLAG := -g ${OPT} -Wall -shared -std=c++11 -undefined dynamic_lookup -fPIC
SUFFIX := $(shell python3-config --extension-suffix)
PY_TARGET = $(addprefix pybind_, $(TARGET))
CPP_FILES = $(addprefix $(SRC_DIR)/, $(addsuffix .cpp, $(PY_TARGET) $(TARGET) $(OTHERS)))
target:
	clang++ -target arm64-apple-macos $(FLAG) $(INCLUDE) libCMSISDSP.a $(CPP_FILES) -o $(PY_TARGET)$(SUFFIX)
	pybind11-stubgen $(PY_TARGET) -o $(PY_TARGET).pyi
