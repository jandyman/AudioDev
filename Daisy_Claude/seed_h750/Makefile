# Daisy_Claude — STM32H750 bare-metal build
#
# Targets:
#   make         build/<project>.elf, .bin, .hex, .map
#   make size    arm-none-eabi-size on the elf
#   make clean   rm -rf build/
#
# No `make upload` target — flashing is done from STM32CubeIDE's debug launcher,
# which loads build/<project>.elf into internal flash (0x08000000) over SWD.
# See docs/spec/02_step1_startup_and_clock.md §11 and §12.

# Derive the target name from the project folder so the ELF matches the
# CubeIDE project name, regardless of which archive is open.
TARGET   := $(notdir $(CURDIR))
BUILDDIR := build

# ----- toolchain -----
# We use g++ as the linker driver because it knows about C++ ABI bits
# (init_array iteration via crtbegin/crtend isn't relevant here — we call
# constructors explicitly from Reset path — but g++ won't add anything we
# don't ask for, and gets the right multilib for -mfpu=fpv5-d16).
TOOLCHAIN_PREFIX ?= arm-none-eabi-
CC      := $(TOOLCHAIN_PREFIX)gcc
CXX     := $(TOOLCHAIN_PREFIX)g++
AS      := $(TOOLCHAIN_PREFIX)gcc
LD      := $(TOOLCHAIN_PREFIX)g++
OBJCOPY := $(TOOLCHAIN_PREFIX)objcopy
SIZE    := $(TOOLCHAIN_PREFIX)size

# ----- paths -----
# CMSIS headers are provided by the libDaisy checkout next door. We do NOT
# vendor them into this repo — only these two include paths are needed.
CMSIS_CORE_DIR   := ../../DaisyExamples/libDaisy/Drivers/CMSIS/Include
CMSIS_DEVICE_DIR := ../../DaisyExamples/libDaisy/Drivers/CMSIS/Device/ST/STM32H7xx/Include
DSP_CPP_DIR      := ../../Python_STM32/dsp_cpp

INCLUDES := \
  -Iinclude \
  -Isrc \
  -Isrc/rtt \
  -I$(DSP_CPP_DIR)/include \
  -I$(CMSIS_CORE_DIR) \
  -I$(CMSIS_DEVICE_DIR)

# ----- flags -----
# -ffreestanding -nostdlib -nostartfiles : no libc/newlib, our startup owns entry.
# -fno-common                            : every uninitialized global gets its own .bss slot.
# -DSTM32H750xx                          : selects the right device block in stm32h7xx.h.
# -DHSE_VALUE=16000000                   : irreducible hardware fact from spec 01 §1.
CPU      := -mcpu=cortex-m7 -mthumb -mfpu=fpv5-d16 -mfloat-abi=hard
DEFINES  := -DSTM32H750xx -DHSE_VALUE=16000000 -DSEGGER_RTT_MEMCPY_USE_BYTELOOP=1
WARNINGS := -Wall -Wextra -Wshadow -Wundef
OPT      := -Og -g3

CFLAGS  := $(CPU) $(OPT) $(WARNINGS) $(DEFINES) $(INCLUDES) \
           -ffreestanding -nostdlib -nostartfiles -fno-common \
           -fdata-sections -ffunction-sections \
           -std=c11

# C++ flags mirror C flags, plus bare-metal-friendly disables:
#   -fno-exceptions          : no unwind tables, no eh_personality, smaller .text
#   -fno-rtti                : no typeinfo, no dynamic_cast
#   -fno-use-cxa-atexit      : don't register static-object dtors with __cxa_atexit
#                              (we never destruct globals on this target)
#   -fno-threadsafe-statics  : skip __cxa_guard_* (pulls in pthread on newlib)
CXXFLAGS := $(CPU) $(OPT) $(WARNINGS) $(DEFINES) $(INCLUDES) \
            -ffreestanding -nostdlib -nostartfiles -fno-common \
            -fdata-sections -ffunction-sections \
            -std=c++17 \
            -fno-exceptions -fno-rtti \
            -fno-use-cxa-atexit -fno-threadsafe-statics \
            -Wno-register
# -Wno-register: CMSIS headers (cmsis_gcc.h, core_cm7.h) use the C `register`
# storage-class specifier on a few intrinsics. C++17 deprecated `register`,
# so g++ warns whenever those intrinsics are pulled in via stm32h750xx.h.
# It's vendor code we don't control; silencing the warning is the standard
# workaround. (Doesn't affect codegen — the keyword is a no-op anyway.)

ASFLAGS := $(CPU) $(OPT) -x assembler-with-cpp

LDSCRIPT := linker/stm32h750_flash.ld
LDFLAGS  := $(CPU) -nostdlib -nostartfiles \
            -T $(LDSCRIPT) \
            -Wl,--gc-sections \
            -Wl,-Map=$(BUILDDIR)/$(TARGET).map \
            -Wl,--print-memory-usage

# ----- sources -----
# Discover sources automatically so renaming .c → .cpp doesn't touch the
# Makefile. This is the only place in the project that uses wildcards;
# everything else is explicit.
C_SRCS   := $(wildcard src/*.c) $(wildcard src/rtt/*.c)
CXX_SRCS := $(wildcard src/*.cpp)
S_SRCS   := $(wildcard src/*.s)

DSP_CPP_OBJS := $(BUILDDIR)/dsp_cpp/eq_design.o

OBJS := $(C_SRCS:%.c=$(BUILDDIR)/%.o) \
        $(CXX_SRCS:%.cpp=$(BUILDDIR)/%.o) \
        $(S_SRCS:%.s=$(BUILDDIR)/%.o) \
        $(DSP_CPP_OBJS)
DEPS := $(OBJS:.o=.d)

# ----- rules -----
.PHONY: all clean size
all: $(BUILDDIR)/$(TARGET).elf $(BUILDDIR)/$(TARGET).bin $(BUILDDIR)/$(TARGET).hex size

$(BUILDDIR)/%.o: %.c
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -MMD -MP -c $< -o $@

$(BUILDDIR)/%.o: %.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) -MMD -MP -c $< -o $@

$(BUILDDIR)/dsp_cpp/%.o: $(DSP_CPP_DIR)/src/%.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) -MMD -MP -c $< -o $@

$(BUILDDIR)/%.o: %.s
	@mkdir -p $(dir $@)
	$(AS) $(ASFLAGS) -c $< -o $@

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
