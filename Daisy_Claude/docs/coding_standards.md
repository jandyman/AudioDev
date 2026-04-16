# Coding Standards

A starter set of conventions for Daisy_Claude firmware. Intentionally short — we'll extend as real cases come up.

---

## 1. Formatting

- **Base style:** 1TBS (One True Brace Style). The opening brace goes on the **same line** for everything — functions, structs, classes, enums, and control blocks (`if`/`for`/`while`/`switch`). The closing brace gets its own line. This is K&R applied uniformly; the K&R quirk of putting function-definition braces on the next line is dropped.
- **Indent:** 2 spaces. No hard tabs.
- **End-of-line comments:** `//`. When a block has several of them in a row, align them vertically if it's reasonable — we assume a coding-friendly (monospace) font.

Example:

```c
uint32_t pll1_n = 240;   // PLL1 multiplier — (16 MHz / 4) * 240 / 2 = 480 MHz
uint32_t pll1_p = 2;     // post-divider to SYSCLK
uint32_t pll1_q = 20;    // SPI/SDMMC kernel clock divider
```

---

## 2. Naming

- **Case:** `snake_case` for variables, functions, and file names. This keeps abutted acronyms readable (`sai1_rx_dma`, not `Sai1RxDMA`).
- **Length follows distance.** A variable used one line after its declaration can be short; one used 30 lines away, or across function boundaries, earns a longer name. The tradeoff is clarity versus line length — pick the shortest name that stays unambiguous at the point of use.
- **Acronyms.** Well-known domain acronyms (`dma`, `sai`, `pll`, `i2s`, `spi`, `fft`) stay as acronyms. Don't expand them. Obscure or project-specific abbreviations should be spelled out.

---

## 3. Vertical rhythm

The general philosophy is to **conserve vertical space** while keeping code readable like English prose. Think in paragraphs: related lines cluster, and a blank line separates one thought from the next.

Concretely:

- A multi-line comment (say, 3+ lines) describing the block below it gets a blank line between the comment and the code, the same way prose separates a heading from its paragraph.
- Tightly related statements stay contiguous — no gratuitous blank lines inside a small block.
- Two logically distinct steps within one function get a blank line between them, even if each is only one or two lines.

Example:

```c
// Enable the SAI1 peripheral clock and reset the block before any
// register configuration, per RM0433 §8.7.26. Without the reset,
// re-running init after a warm boot can leave FIFOs in odd states.

RCC->APB2ENR |= RCC_APB2ENR_SAI1EN;
RCC->APB2RSTR |=  RCC_APB2RSTR_SAI1RST;
RCC->APB2RSTR &= ~RCC_APB2RSTR_SAI1RST;

// Sub-block A: TX master. FS and SCK are generated here and shared
// with sub-block B via synchronous mode.

SAI1_Block_A->CR1 = ...;
```

---

## 4. Revisions

This document is not append-only (unlike specs in `docs/spec/`). Edit in place as conventions evolve; git history is the record.
