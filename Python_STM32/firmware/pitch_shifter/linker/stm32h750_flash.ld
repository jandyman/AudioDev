/* pitch_shifter — STM32H750IBK6 linker script
 *
 * Same as the platform/eq linker script but with .bss placed in RAM_D1 (512KB AXI SRAM) rather
 * than DTCMRAM, because the pitch_shifter graph state + 128KB bump allocator
 * exceeds the 128KB DTCMRAM limit.
 *
 * Layout:
 *   FLASH    0x08000000  128 KB   code + rodata + .data LMA
 *   DTCMRAM  0x20000000  128 KB   .data (VMA) + stack only
 *   RAM_D1   0x24000000  512 KB   .bss + .dma_buffers + bump heap (via .bss)
 *
 * .dma_buffers still starts at ORIGIN(RAM_D1) for the MPU region alignment.
 * We satisfy this by placing .dma_buffers first in RAM_D1, then .bss after it.
 *
 * Note: The MPU ASSERT checks that .dma_buffers <= 2KB. The .bss that follows
 * it is NOT covered by the non-cacheable MPU region — that is intentional.
 * DSP state (which the CPU reads/writes coherently, not DMA) should be
 * cacheable. Only the DMA RX/TX buffers need non-cacheable treatment.
 */

ENTRY(Reset_Handler)

MEMORY
{
    FLASH   (rx)  : ORIGIN = 0x08000000, LENGTH = 128K
    DTCMRAM (rwx) : ORIGIN = 0x20000000, LENGTH = 128K
    RAM_D1  (rw)  : ORIGIN = 0x24000000, LENGTH = 512K
}

/* Top of stack = top of DTCMRAM. Stack grows downward. */
_estack = ORIGIN(DTCMRAM) + LENGTH(DTCMRAM);

SECTIONS
{
    .isr_vector :
    {
        . = ALIGN(4);
        KEEP(*(.isr_vector))
        . = ALIGN(4);
    } > FLASH

    .text :
    {
        . = ALIGN(4);
        *(.text)
        *(.text*)
        *(.rodata)
        *(.rodata*)
        *(.glue_7)
        *(.glue_7t)
        *(.eh_frame)
        KEEP(*(.init))
        KEEP(*(.fini))
        . = ALIGN(4);
        _etext = .;
    } > FLASH

    .init_array :
    {
        . = ALIGN(4);
        _sinit_array = .;
        KEEP(*(SORT(.init_array.*)))
        KEEP(*(.init_array))
        . = ALIGN(4);
        _einit_array = .;
    } > FLASH

    /* Initialized data: LMA in FLASH, VMA in DTCMRAM. */
    .data :
    {
        . = ALIGN(4);
        _sdata = .;
        *(.data)
        *(.data*)
        . = ALIGN(4);
        _edata = .;
    } > DTCMRAM AT > FLASH
    _sidata = LOADADDR(.data);
    /* End of the flash image (LMA). The .bin spans [ORIGIN(FLASH), _eidata):
     * vector table + .text/.rodata + .init_array + .data LMA. The host CRCs the
     * .bin over exactly this range and the firmware self-CRCs the same bytes at
     * boot (see crc32 in main.cpp) to verify the running image. */
    _eidata = LOADADDR(.data) + SIZEOF(.data);

    /* Stack check: .data must leave room for the stack in DTCMRAM. */
    _min_stack = 4K;
    ._stack_check (NOLOAD) :
    {
        . = ALIGN(8);
        . = . + _min_stack;
    } > DTCMRAM

    /* DMA buffers: must start at ORIGIN(RAM_D1) for MPU alignment. */
    .dma_buffers (NOLOAD) :
    {
        . = ALIGN(32);
        _sdma_buffers = .;
        *(.dma_buffers)
        *(.dma_buffers*)
        . = ALIGN(32);
        _edma_buffers = .;
    } > RAM_D1

    ASSERT(_sdma_buffers == ORIGIN(RAM_D1),
           "DMA buffers must start at RAM_D1 base for MPU region alignment")
    ASSERT((_edma_buffers - _sdma_buffers) <= 2048,
           "DMA buffers exceed the 2 KB MPU non-cacheable region")

    /* BSS in RAM_D1: zero-init globals/statics including the bump allocator
     * and all pitch_shifter graph state. At ~146KB this fits easily in 512KB. */
    .bss (NOLOAD) :
    {
        . = ALIGN(4);
        _sbss = .;
        *(.bss)
        *(.bss*)
        *(COMMON)
        . = ALIGN(4);
        _ebss = .;
    } > RAM_D1

    /DISCARD/ :
    {
        *(.ARM.exidx*)
        *(.ARM.extab*)
    }
}
