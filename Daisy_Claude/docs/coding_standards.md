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

The guiding idea is simply that code should **read like paragraphs**, the way people are used to: a paragraph-style comment is a heading, and a heading sits a blank line above its paragraph.

- A **paragraph-style comment** (multi-line prose) heading a top-level definition — a function *or* a block of constant declarations — gets a blank line beneath it, so the code reads as the paragraph under that heading.
- A **single-line label** hugs the group it introduces (e.g. `// Latency thresholds (ms)` right above its constants) — it's a caption, not a paragraph.
- A comment **inside a function body** hugs the code it annotates, even when it runs several lines — it's an inline note within the paragraph, not a new heading. The blank line that separates two steps goes *above* the next step's comment.
- Tightly related statements stay contiguous — no gratuitous blank lines inside a small block.

Example:

```c
class loop_controller {
  // Latency thresholds (ms)            — single-line label, hugs its group.
  static constexpr float LOWER_THRESHOLD_MS = 100.0f;
  static constexpr float UPPER_THRESHOLD_MS = 200.0f;

  // Crossfade lengths. The bailout fade runs longer than a loop fade, so a
  // forced reset is gentler. This multi-line paragraph heads a constant
  // block, so it gets a blank line — same as a comment above a function.

  static constexpr float LOOP_CROSSFADE_MS    = 5.0f;
  static constexpr float BAILOUT_CROSSFADE_MS = 15.0f;

  // advance_tap_state() — one delay+gain ramp step per tap; parks any tap
  // whose gain reaches zero.

  void advance_tap_state() {
    // Advance each live tap, then park any that reached zero gain. An inline
    // note inside the body hugs its code, even when it runs to two lines.
    for (int i = 0; i < NUM_TAPS; i++) {
      // ...
    }
  }
};
```

These vertical-rhythm rules are language-agnostic — they apply to Faust `.dsp`
source as much as C++. Read "function" as a **top-level definition** (a Faust
`name = …;` binding, including `process`), and a labeled group of parameter
definitions is a **block of constants** — exactly the pattern in blocks like
`attack_detector.dsp`.

---

## 4. Revisions

This document is not append-only (unlike specs in `docs/spec/`). Edit in place as conventions evolve; git history is the record.
