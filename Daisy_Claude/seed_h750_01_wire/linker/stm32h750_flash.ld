/* Daisy_Claude — STM32H750IBK6 linker script
 *
 * Layout (spec 02 §5):
 *   FLASH    0x08000000  128 KB   code + rodata + .data LMA
 *   DTCMRAM  0x20000000  128 KB   .data (VMA) + .bss + stack
 *   RAM_D1   0x24000000  512 KB   AXI SRAM — holds .dma_buffers, rest unused
 *
 * The first 2 KB of RAM_D1 holds .dma_buffers and is covered by a single
 * MPU region configured Normal / Non-cacheable / Shareable so the Cortex-M7
 * D-cache and DMA never fight over the same cache lines. Audio buffers,
 * and anything else DMA touches, must go in this section.
 *
 * No heap. No _end/_sbrk. Any accidental malloc reference fails to link,
 * which is exactly what the CLAUDE.md hard rule asks for.
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
    /* Cortex-M vector table: must be first in FLASH so the core reads
     * initial MSP from [0x08000000] and reset vector from [0x08000004]. */
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

    /* Initialized data: LMA in FLASH, VMA in DTCMRAM. Reset_Handler
     * copies [_sidata, _sidata + (_edata - _sdata)) → [_sdata, _edata). */
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

    .bss (NOLOAD) :
    {
        . = ALIGN(4);
        _sbss = .;
        *(.bss)
        *(.bss*)
        *(COMMON)
        . = ALIGN(4);
        _ebss = .;
    } > DTCMRAM

    /* Reserve room for the stack at the very top of DTCMRAM by checking
     * that _ebss leaves at least _min_stack bytes before _estack. */
    _min_stack = 4K;
    ._stack_check (NOLOAD) :
    {
        . = ALIGN(8);
        . = . + _min_stack;
    } > DTCMRAM

    /* .dma_buffers lives at the base of RAM_D1 (AXI SRAM). The section is
     * NOLOAD because DMA fills it at runtime — we do not want the startup
     * zero-init path to touch it, and we definitely do not want it in the
     * .data LMA copied from flash. It is the only section placed in RAM_D1,
     * which is what guarantees _sdma_buffers == ORIGIN(RAM_D1) and keeps
     * the MPU region alignment simple (see the ASSERTs below).
     *
     * The section is padded up to 2 KB so the MPU region (base = RAM_D1
     * origin, size = 2 KB = MPU SIZE field 10) covers exactly what we want
     * and nothing more. */
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

    /* Discard ARM unwind tables — no C++ exceptions on this target. */
    /DISCARD/ :
    {
        *(.ARM.exidx*)
        *(.ARM.extab*)
    }
}
