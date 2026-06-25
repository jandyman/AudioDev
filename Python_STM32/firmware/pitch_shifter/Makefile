# pitch_shifter — STM32H750 bare-metal build
#
# Targets:
#   make         build/pitch_shifter.elf, .bin, .hex, .map
#   make size    arm-none-eabi-size on the elf
#   make clean   rm -rf build/
#
# PREREQUISITE: run the native graph build first so the generated header, the
# Faust block .cpp, and the dependency manifest exist:
#   cd ../../projects/pitch_shifter && make -f pitch_shifter.make
# The block set (hand-written C++ sources + their include dirs) is then taken
# from that build's <graph>.deps.mk manifest — NOT re-declared here — so this
# Makefile cannot drift from the .graph.

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

# ----- graph (native build outputs we consume) -----
GRAPH         := pitch_shifter
GRAPH_PROJECT := ../../projects/pitch_shifter
GRAPH_BUILD   := $(GRAPH_PROJECT)/build
GRAPH_GEN     := $(GRAPH_BUILD)/generated
MANIFEST      := $(GRAPH_GEN)/$(GRAPH).deps.mk
COMMON        := ../common

# Pull GRAPH_CPP_SOURCES + GRAPH_BLOCK_INCLUDE_DIRS from the graph-derived
# manifest (single source of truth for the block set).
-include $(MANIFEST)
ifeq ($(strip $(GRAPH_CPP_SOURCES)),)
$(warning Manifest $(MANIFEST) not found or empty — run the native build first: cd $(GRAPH_PROJECT) && make -f $(GRAPH).make)
endif

# ----- paths -----
CMSIS_CORE_DIR   := ../../../DaisyExamples/libDaisy/Drivers/CMSIS/Include
CMSIS_DEVICE_DIR := ../../../DaisyExamples/libDaisy/Drivers/CMSIS/Device/ST/STM32H7xx/Include

PLATFORM := ../seed_h750/src

# include/ MUST come before generated/bare-metal headers so our overrides win.
# Canonical block-source dirs precede $(GRAPH_BUILD) so the real block headers
# win over any stale shadow copy sitting in the native build/ tree; $(GRAPH_BUILD)
# is still needed for the Faust-generated .cpp the header #includes.
INCLUDES := \
  -Iinclude \
  -Isrc \
  -I$(BUILDDIR) \
  -I$(COMMON)/include \
  -I$(PLATFORM) \
  -I$(PLATFORM)/rtt \
  -I../seed_h750/include \
  $(addprefix -I,$(GRAPH_BLOCK_INCLUDE_DIRS)) \
  -I$(GRAPH_GEN) \
  -I$(GRAPH_BUILD) \
  -I$(CMSIS_CORE_DIR) \
  -I$(CMSIS_DEVICE_DIR)

# ----- flags -----
CPU      := -mcpu=cortex-m7 -mthumb -mfpu=fpv5-d16 -mfloat-abi=hard
DEFINES  := -DSTM32H750xx -DHSE_VALUE=16000000 -DSEGGER_RTT_MEMCPY_USE_BYTELOOP=1 \
            -DBARE_METAL=1 -DCHUNK_SIZE=48 -DBUFFER_SIZE_DOWN=256 \
            -DAUDIO_GRAPH_HEADER=\"$(GRAPH).h\"
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
# Faust .cpp are NOT compiled here — they are #included by the generated header.
# Out-of-tree objects live under build/ext/ so `make clean` removes everything.

# Local sources (src/) — object goes in build/src/
LOCAL_CXX_SRCS := src/audio.cpp src/main.cpp src/libstubs.cpp src/rtt_audio.cpp

# Platform sources (../seed_h750/src/) — objects in build/ext/platform/
PLAT_C_SRCS    := $(PLATFORM)/rtt/SEGGER_RTT.c
PLAT_CXX_SRCS  := $(PLATFORM)/clock.cpp $(PLATFORM)/dma.cpp \
                  $(PLATFORM)/gpio.cpp $(PLATFORM)/mpu.cpp \
                  $(PLATFORM)/sai1.cpp $(PLATFORM)/system_init.cpp \
                  $(PLATFORM)/systick.cpp
PLAT_S_SRCS    := $(PLATFORM)/startup_stm32h750.s

# Shared firmware runner (graph-agnostic glue + metering) — build/ext/common/
COMMON_CXX_SRCS := $(COMMON)/src/audio_graph_runner.cpp

# Graph C++ block sources from the manifest (absolute paths) — build/ext/blocks/
# Found via vpath on their source dirs; objects keyed by basename.
vpath %.cpp $(sort $(dir $(GRAPH_CPP_SOURCES)))

LOCAL_OBJS  := $(patsubst %.cpp, $(BUILDDIR)/%.o, $(LOCAL_CXX_SRCS))
PLAT_OBJS   := $(patsubst $(PLATFORM)/%.c,   $(BUILDDIR)/ext/platform/%.o, $(PLAT_C_SRCS)) \
               $(patsubst $(PLATFORM)/%.cpp, $(BUILDDIR)/ext/platform/%.o, $(PLAT_CXX_SRCS)) \
               $(patsubst $(PLATFORM)/%.s,   $(BUILDDIR)/ext/platform/%.o, $(PLAT_S_SRCS))
COMMON_OBJS := $(patsubst $(COMMON)/src/%.cpp, $(BUILDDIR)/ext/common/%.o, $(COMMON_CXX_SRCS))
BLOCK_OBJS  := $(addprefix $(BUILDDIR)/ext/blocks/,$(notdir $(GRAPH_CPP_SOURCES:.cpp=.o)))

OBJS := $(LOCAL_OBJS) $(PLAT_OBJS) $(COMMON_OBJS) $(BLOCK_OBJS)
DEPS := $(OBJS:.o=.d)

# ----- build-id (source fingerprint for the monitor-registry handshake) -----
# 32-bit hash of HEAD + uncommitted diff + new-untracked-source names, SCOPED to
# the trees that determine firmware layout (so test-audio / output churn doesn't
# move the id). Stable across no-op rebuilds, unique whenever firmware source
# changes. Emits build_id.h (compiled in) and a .buildid sidecar the host reads
# to verify the running firmware matches this .map. See docs/monitor_registry.md.
FINGERPRINT_PATHS := ../../firmware ../../projects ../../dsp_cpp ../../dsp_faust
BUILD_ID := $(shell ( git rev-parse HEAD; \
                      git diff HEAD -- $(FINGERPRINT_PATHS); \
                      git ls-files --others --exclude-standard -- $(FINGERPRINT_PATHS) \
                    ) 2>/dev/null | shasum -a 1 | cut -c1-8)
BUILD_ID := $(if $(strip $(BUILD_ID)),$(BUILD_ID),deadbeef)

# ----- rules -----
.PHONY: all clean size force
all: $(BUILDDIR)/$(TARGET).elf $(BUILDDIR)/$(TARGET).bin $(BUILDDIR)/$(TARGET).hex size

# Regenerated every build but rewritten only on change, so main.o (its only
# consumer) recompiles exactly when the id changes. The sidecar is always refreshed.
$(BUILDDIR)/build_id.h: force
	@mkdir -p $(BUILDDIR)
	@printf '#pragma once\n#define BUILD_ID_HASH 0x%su\n' '$(BUILD_ID)' > $@.tmp
	@if ! cmp -s $@.tmp $@; then mv $@.tmp $@; else rm -f $@.tmp; fi
	@printf '0x%s\n' '$(BUILD_ID)' > $(BUILDDIR)/$(TARGET).buildid

# main.cpp #includes build_id.h for monitor_commit().
$(BUILDDIR)/src/main.o: $(BUILDDIR)/build_id.h

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

# Shared runner (build/ext/common/)
$(BUILDDIR)/ext/common/%.o: $(COMMON)/src/%.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) -MMD -MP -c $< -o $@

# Graph block sources (build/ext/blocks/) — basename via vpath over manifest dirs
$(BUILDDIR)/ext/blocks/%.o: %.cpp
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
