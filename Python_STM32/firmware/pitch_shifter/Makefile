# pitch_shifter — STM32H750 bare-metal build
#
# Targets:
#   make         build/pitch_shifter.elf, .bin, .hex, .map
#   make size    arm-none-eabi-size on the elf
#   make clean   rm -rf build/

TARGET   := pitch_shifter
BUILDDIR := build

# ----- toolchain -----
TOOLCHAIN_PREFIX ?= arm-none-eabi-
CC      := $(TOOLCHAIN_PREFIX)gcc
CXX     := $(TOOLCHAIN_PREFIX)g++
AS      := $(TOOLCHAIN_PREFIX)gcc
LD      := $(TOOLCHAIN_PREFIX)g++
OBJCOPY := $(TOOLCHAIN_PREFIX)objcopy
SIZE    := $(TOOLCHAIN_PREFIX)size

# ----- paths -----
CMSIS_CORE_DIR   := ../../../DaisyExamples/libDaisy/Drivers/CMSIS/Include
CMSIS_DEVICE_DIR := ../../../DaisyExamples/libDaisy/Drivers/CMSIS/Device/ST/STM32H7xx/Include

PLATFORM := ../seed_h750/src
PYTHON   := ../../python

# include/ MUST come before python bindings so our bare-metal overrides win.
INCLUDES := \
  -Iinclude \
  -Isrc \
  -I$(PLATFORM) \
  -I$(PLATFORM)/rtt \
  -I../seed_h750/include \
  -I$(PYTHON)/build/generated \
  -I$(PYTHON)/build \
  -I$(PYTHON)/pitch_shifter_demo \
  -I$(CMSIS_CORE_DIR) \
  -I$(CMSIS_DEVICE_DIR)

# ----- flags -----
CPU      := -mcpu=cortex-m7 -mthumb -mfpu=fpv5-d16 -mfloat-abi=hard
DEFINES  := -DSTM32H750xx -DHSE_VALUE=16000000 -DSEGGER_RTT_MEMCPY_USE_BYTELOOP=1 \
            -DBARE_METAL=1 -DCHUNK_SIZE=48 -DBUFFER_SIZE_DOWN=256
WARNINGS := -Wall -Wextra -Wshadow -Wundef
OPT      := -Og -g3

CFLAGS  := $(CPU) $(OPT) $(WARNINGS) $(DEFINES) $(INCLUDES) \
           -ffreestanding -nostdlib -nostartfiles -fno-common \
           -fdata-sections -ffunction-sections \
           -std=c11

# C++ flags: drop -ffreestanding so <cmath>/<algorithm> in Faust-generated code
# compile without the "not available in freestanding mode" error. The firmware
# still uses -nostdlib/-nostartfiles so newlib is not linked in; the C++ headers
# are pulled in for declarations only (sinf, cosf, etc. resolve via -lm at link).
CXXFLAGS := $(CPU) $(OPT) $(WARNINGS) $(DEFINES) $(INCLUDES) \
            -nostdlib -nostartfiles -fno-common \
            -fdata-sections -ffunction-sections \
            -std=c++17 \
            -fno-exceptions -fno-rtti \
            -fno-use-cxa-atexit -fno-threadsafe-statics \
            -Wno-register

ASFLAGS := $(CPU) $(OPT) -x assembler-with-cpp

LDSCRIPT := linker/stm32h750_flash.ld
LDFLAGS  := $(CPU) -nostdlib -nostartfiles \
            -T $(LDSCRIPT) \
            -Wl,--gc-sections \
            -Wl,-Map=$(BUILDDIR)/$(TARGET).map \
            -Wl,--print-memory-usage

# ----- sources -----
# Faust .cpp files are NOT listed here — they are compiled inline via
# #include directives inside pitch_shifter.h (included by pitch_shifter_audio.cpp).
#
# Out-of-tree objects are kept under build/ext/ so that `make clean` (rm -rf build/)
# removes everything. Each source→object mapping is explicit.

# Local sources (in src/) — object goes in build/src/
LOCAL_C_SRCS   :=
LOCAL_CXX_SRCS := src/audio.cpp src/pitch_shifter_audio.cpp src/main.cpp src/libstubs.cpp src/rtt_audio.cpp
LOCAL_S_SRCS   :=

# Platform sources (../seed_h750/src/) — objects go in build/ext/platform/
PLAT_C_SRCS    := $(PLATFORM)/rtt/SEGGER_RTT.c
PLAT_CXX_SRCS  := $(PLATFORM)/clock.cpp $(PLATFORM)/dma.cpp \
                  $(PLATFORM)/gpio.cpp $(PLATFORM)/mpu.cpp \
                  $(PLATFORM)/sai1.cpp $(PLATFORM)/system_init.cpp \
                  $(PLATFORM)/systick.cpp
PLAT_S_SRCS    := $(PLATFORM)/startup_stm32h750.s

# Python DSP block sources — objects go in build/ext/python/
PY_CXX_SRCS    := $(PYTHON)/pitch_shifter_demo/pitch_detector.cpp \
                  $(PYTHON)/pitch_shifter_demo/loop_controller.cpp \
                  $(PYTHON)/pitch_shifter_demo/mixer3.cpp

# Compute object paths — strip the source prefix and put under build/ext/
LOCAL_OBJS  := $(patsubst %.c,   $(BUILDDIR)/%.o, $(LOCAL_C_SRCS)) \
               $(patsubst %.cpp, $(BUILDDIR)/%.o, $(LOCAL_CXX_SRCS)) \
               $(patsubst %.s,   $(BUILDDIR)/%.o, $(LOCAL_S_SRCS))

PLAT_OBJS   := $(patsubst $(PLATFORM)/%.c,   $(BUILDDIR)/ext/platform/%.o, $(PLAT_C_SRCS)) \
               $(patsubst $(PLATFORM)/%.cpp, $(BUILDDIR)/ext/platform/%.o, $(PLAT_CXX_SRCS)) \
               $(patsubst $(PLATFORM)/%.s,   $(BUILDDIR)/ext/platform/%.o, $(PLAT_S_SRCS))

PY_OBJS     := $(patsubst $(PYTHON)/pitch_shifter_demo/%.cpp, \
                           $(BUILDDIR)/ext/python/%.o, $(PY_CXX_SRCS))

OBJS := $(LOCAL_OBJS) $(PLAT_OBJS) $(PY_OBJS)
DEPS := $(OBJS:.o=.d)

# ----- rules -----
.PHONY: all clean size
all: $(BUILDDIR)/$(TARGET).elf $(BUILDDIR)/$(TARGET).bin $(BUILDDIR)/$(TARGET).hex size

# Local source rules
$(BUILDDIR)/%.o: %.c
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -MMD -MP -c $< -o $@

$(BUILDDIR)/%.o: %.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) -MMD -MP -c $< -o $@

$(BUILDDIR)/%.o: %.s
	@mkdir -p $(dir $@)
	$(AS) $(ASFLAGS) -c $< -o $@

# Platform source rules (build/ext/platform/)
$(BUILDDIR)/ext/platform/%.o: $(PLATFORM)/%.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) -MMD -MP -c $< -o $@

$(BUILDDIR)/ext/platform/%.o: $(PLATFORM)/%.c
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -MMD -MP -c $< -o $@

$(BUILDDIR)/ext/platform/%.o: $(PLATFORM)/%.s
	@mkdir -p $(dir $@)
	$(AS) $(ASFLAGS) -c $< -o $@

# Python DSP block rules (build/ext/python/)
$(BUILDDIR)/ext/python/%.o: $(PYTHON)/pitch_shifter_demo/%.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) -MMD -MP -c $< -o $@

$(BUILDDIR)/$(TARGET).elf: $(OBJS) $(LDSCRIPT)
	$(LD) $(OBJS) $(LDFLAGS) -lm -lgcc -o $@

$(BUILDDIR)/$(TARGET).bin: $(BUILDDIR)/$(TARGET).elf
	$(OBJCOPY) -O binary $< $@

$(BUILDDIR)/$(TARGET).hex: $(BUILDDIR)/$(TARGET).elf
	$(OBJCOPY) -O ihex $< $@

size: $(BUILDDIR)/$(TARGET).elf
	$(SIZE) $<

clean:
	rm -rf $(BUILDDIR)

-include $(DEPS)
