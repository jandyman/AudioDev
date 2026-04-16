# Daisy_Claude — STM32H750 bare-metal build
#
# Targets:
#   make         build/daisy_step1.elf, .bin, .hex, .map
#   make size    arm-none-eabi-size on the elf
#   make clean   rm -rf build/
#
# No `make upload` target — flashing is done from STM32CubeIDE's debug launcher,
# which loads build/daisy_step1.elf into internal flash (0x08000000) over SWD.
# See docs/spec/02_step1_startup_and_clock.md §11 and §12.

TARGET   := daisy_step1
BUILDDIR := build

# ----- toolchain -----
TOOLCHAIN_PREFIX ?= arm-none-eabi-
CC      := $(TOOLCHAIN_PREFIX)gcc
AS      := $(TOOLCHAIN_PREFIX)gcc
LD      := $(TOOLCHAIN_PREFIX)gcc
OBJCOPY := $(TOOLCHAIN_PREFIX)objcopy
SIZE    := $(TOOLCHAIN_PREFIX)size

# ----- paths -----
# CMSIS headers are provided by the libDaisy checkout next door. We do NOT
# vendor them into this repo — only these two include paths are needed.
CMSIS_CORE_DIR   := ../../DaisyExamples/libDaisy/Drivers/CMSIS/Include
CMSIS_DEVICE_DIR := ../../DaisyExamples/libDaisy/Drivers/CMSIS/Device/ST/STM32H7xx/Include

INCLUDES := \
  -Iinclude \
  -Isrc \
  -I$(CMSIS_CORE_DIR) \
  -I$(CMSIS_DEVICE_DIR)

# ----- flags -----
# -ffreestanding -nostdlib -nostartfiles : no libc/newlib, our startup owns entry.
# -fno-common                            : every uninitialized global gets its own .bss slot.
# -DSTM32H750xx                          : selects the right device block in stm32h7xx.h.
# -DHSE_VALUE=16000000                   : irreducible hardware fact from spec 01 §1.
CPU      := -mcpu=cortex-m7 -mthumb -mfpu=fpv5-d16 -mfloat-abi=hard
DEFINES  := -DSTM32H750xx -DHSE_VALUE=16000000
WARNINGS := -Wall -Wextra -Wshadow -Wundef
OPT      := -Og -g3

CFLAGS  := $(CPU) $(OPT) $(WARNINGS) $(DEFINES) $(INCLUDES) \
           -ffreestanding -nostdlib -nostartfiles -fno-common \
           -fdata-sections -ffunction-sections \
           -std=c11
ASFLAGS := $(CPU) $(OPT) -x assembler-with-cpp

LDSCRIPT := linker/stm32h750_flash.ld
LDFLAGS  := $(CPU) -nostdlib -nostartfiles \
            -T $(LDSCRIPT) \
            -Wl,--gc-sections \
            -Wl,-Map=$(BUILDDIR)/$(TARGET).map \
            -Wl,--print-memory-usage

# ----- sources -----
C_SRCS := \
  src/system_init.c \
  src/clock.c       \
  src/gpio.c        \
  src/systick.c     \
  src/main.c

S_SRCS := \
  src/startup_stm32h750.s

OBJS := $(C_SRCS:%.c=$(BUILDDIR)/%.o) $(S_SRCS:%.s=$(BUILDDIR)/%.o)
DEPS := $(OBJS:.o=.d)

# ----- rules -----
.PHONY: all clean size
all: $(BUILDDIR)/$(TARGET).elf $(BUILDDIR)/$(TARGET).bin $(BUILDDIR)/$(TARGET).hex size

$(BUILDDIR)/%.o: %.c
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -MMD -MP -c $< -o $@

$(BUILDDIR)/%.o: %.s
	@mkdir -p $(dir $@)
	$(AS) $(ASFLAGS) -c $< -o $@

$(BUILDDIR)/$(TARGET).elf: $(OBJS) $(LDSCRIPT)
	$(LD) $(OBJS) $(LDFLAGS) -o $@

$(BUILDDIR)/$(TARGET).bin: $(BUILDDIR)/$(TARGET).elf
	$(OBJCOPY) -O binary $< $@

$(BUILDDIR)/$(TARGET).hex: $(BUILDDIR)/$(TARGET).elf
	$(OBJCOPY) -O ihex $< $@

size: $(BUILDDIR)/$(TARGET).elf
	$(SIZE) $<

clean:
	rm -rf $(BUILDDIR)

-include $(DEPS)
