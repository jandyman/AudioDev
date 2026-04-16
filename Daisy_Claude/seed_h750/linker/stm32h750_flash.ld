/* Daisy_Claude — STM32H750IBK6 linker script
 *
 * Layout (spec 02 §5):
 *   FLASH    0x08000000  128 KB   code + rodata + .data LMA
 *   DTCMRAM  0x20000000  128 KB   .data (VMA) + .bss + stack
 *
 * No heap. No _end/_sbrk. Any accidental malloc reference fails to link,
 * which is exactly what the CLAUDE.md hard rule asks for.
 */

ENTRY(Reset_Handler)

MEMORY
{
    FLASH   (rx)  : ORIGIN = 0x08000000, LENGTH = 128K
    DTCMRAM (rwx) : ORIGIN = 0x20000000, LENGTH = 128K
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

    /* Discard ARM unwind tables — no C++ exceptions on this target. */
    /DISCARD/ :
    {
        *(.ARM.exidx*)
        *(.ARM.extab*)
    }
}
