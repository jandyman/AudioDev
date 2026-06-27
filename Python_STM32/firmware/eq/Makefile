# eq — STM32H750 bare-metal build
#
# Targets:
#   make         build/eq.elf, .bin, .hex, .map
#   make size    arm-none-eabi-size on the elf
#   make clean   rm -rf build/
#
# No `make upload` target — flashing is done from STM32CubeIDE's debug launcher,
# which loads build/eq.elf into internal flash (0x08000000) over SWD.
#
# The EQ app (src/) links against the shared platform driver layer in ../platform
# (clock/dma/gpio/mpu/sai1/systick/system_init/rgb_led + SEGGER RTT + startup).
# Platform objects live under build/ext/platform/ so `make clean` removes them.

TARGET   := $(notdir $(CURDIR))
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
DSP_CPP_DIR      := ../../dsp_cpp
PLATFORM         := ../platform

INCLUDES := \
  -Isrc \
  -I$(PLATFORM) \
  -I$(PLATFORM)/rtt \
  -I$(DSP_CPP_DIR)/include \
  -I$(CMSIS_CORE_DIR) \
  -I$(CMSIS_DEVICE_DIR)

# ----- flags -----
CPU      := -mcpu=cortex-m7 -mthumb -mfpu=fpv5-d16 -mfloat-abi=hard
DEFINES  := -DSTM32H750xx -DHSE_VALUE=16000000 -DSEGGER_RTT_MEMCPY_USE_BYTELOOP=1
WARNINGS := -Wall -Wextra -Wshadow -Wundef
OPT      := -Og -g3

CFLAGS  := $(CPU) $(OPT) $(WARNINGS) $(DEFINES) $(INCLUDES) \
           -ffreestanding -nostdlib -nostartfiles -fno-common \
           -fdata-sections -ffunction-sections \
           -std=c11

CXXFLAGS := $(CPU) $(OPT) $(WARNINGS) $(DEFINES) $(INCLUDES) \
            -ffreestanding -nostdlib -nostartfiles -fno-common \
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
# Local app sources (src/) — objects in build/src/
LOCAL_CXX_SRCS := $(wildcard src/*.cpp)
LOCAL_C_SRCS   := $(wildcard src/*.c)

# Platform driver sources (../platform/) — objects in build/ext/platform/
PLAT_C_SRCS    := $(PLATFORM)/rtt/SEGGER_RTT.c
PLAT_CXX_SRCS  := $(PLATFORM)/clock.cpp $(PLATFORM)/dma.cpp \
                  $(PLATFORM)/gpio.cpp $(PLATFORM)/mpu.cpp \
                  $(PLATFORM)/rgb_led.cpp \
                  $(PLATFORM)/sai1.cpp $(PLATFORM)/system_init.cpp \
                  $(PLATFORM)/systick.cpp
PLAT_S_SRCS    := $(PLATFORM)/startup_stm32h750.s

# Shared DSP design code — object in build/dsp_cpp/
DSP_CPP_OBJS   := $(BUILDDIR)/dsp_cpp/eq_design.o

LOCAL_OBJS  := $(patsubst %.cpp, $(BUILDDIR)/%.o, $(LOCAL_CXX_SRCS)) \
               $(patsubst %.c,   $(BUILDDIR)/%.o, $(LOCAL_C_SRCS))
PLAT_OBJS   := $(patsubst $(PLATFORM)/%.c,   $(BUILDDIR)/ext/platform/%.o, $(PLAT_C_SRCS)) \
               $(patsubst $(PLATFORM)/%.cpp, $(BUILDDIR)/ext/platform/%.o, $(PLAT_CXX_SRCS)) \
               $(patsubst $(PLATFORM)/%.s,   $(BUILDDIR)/ext/platform/%.o, $(PLAT_S_SRCS))

OBJS := $(LOCAL_OBJS) $(PLAT_OBJS) $(DSP_CPP_OBJS)
DEPS := $(OBJS:.o=.d)

# ----- rules -----
.PHONY: all clean size
all: $(BUILDDIR)/$(TARGET).elf $(BUILDDIR)/$(TARGET).bin $(BUILDDIR)/$(TARGET).hex size

# Editing any makefile forces a full rebuild so stale objects can't linger.
$(OBJS): $(MAKEFILE_LIST)

# Local source rules (build/src/)
$(BUILDDIR)/%.o: %.c
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -MMD -MP -c $< -o $@

$(BUILDDIR)/%.o: %.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) -MMD -MP -c $< -o $@

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

# Shared DSP design code (build/dsp_cpp/)
$(BUILDDIR)/dsp_cpp/%.o: $(DSP_CPP_DIR)/src/%.cpp
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
