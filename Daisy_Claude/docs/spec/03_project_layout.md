# Spec 03 — Project Layout: per-target subfolders

**Status:** frozen 2026-04-16. Supersedes spec 02 §2 (file tree only).

Spec 02 was written when there was exactly one firmware project, so its file tree placed `Makefile`, `src/`, `include/`, `linker/`, and `build/` directly under `Daisy_Claude/`. As soon as a second hardware target enters the picture (Stage 2's custom H743 board, per `CLAUDE.md`), that flat layout breaks: there is no clean place for the second project's Makefile and linker script to live without colliding with the first.

This spec introduces **one subfolder per firmware target**. Stage 1 lives in `seed_h750/`. A future Stage 2 port lives in `custom_h743/` as a sibling. Spec 02's intent — what files exist, what they contain — is unchanged; only their location moves.

---

## 1. New layout

```
Daisy_Claude/
├── CLAUDE.md
├── .metadata/                        CubeIDE workspace state (gitignored)
├── docs/spec/                        shared, append-only
├── hardware/                         shared reference material (datasheets, schematics)
└── seed_h750/                        Stage 1 firmware project (this is the only one for now)
    ├── Makefile
    ├── linker/stm32h750_flash.ld
    ├── include/board.h
    ├── src/                          startup_*.s, clock.c, gpio.c, systick.c, system_init.c, main.c
    ├── build/                        gitignored
    └── .project, .cproject, .settings/, *.launch       CubeIDE project metadata
```

Future Stage 2 port adds `Daisy_Claude/custom_h743/` alongside `seed_h750/`, with its own self-contained Makefile, linker script, and CubeIDE project. Both share `docs/` and `hardware/`.

---

## 2. Why a subfolder rather than a flat layout

Three things naturally belong "to a firmware target," not "to the repo as a whole":

- The **Makefile** — its toolchain flags (`-mcpu`, `-mfpu`) and source list are target-specific.
- The **linker script** — memory map differs per chip variant.
- The **CubeIDE project metadata** — `target_mcu` in `.cproject` pins one MCU; SFR view, debug launches, and the indexer all key off that.

Putting these under a per-target subfolder means a Stage 2 port is purely additive: a new sibling folder, no rename or merge of the existing one. Git history of `seed_h750/` stays intact. The shared `docs/` and `hardware/` directories don't move.

---

## 3. Why not separate per-step subfolders (e.g. `step1_blink/`, `step1_audio/`)

Step-by-step progression (`blink → audio → DSP`) is handled by **git commits and tags**, not parallel folders. The same `seed_h750/` evolves through every step; earlier states are recoverable via `git checkout step1-part1-blink` etc. Parallel per-step folders would duplicate the startup file, clock code, GPIO helpers, etc. across N copies — the opposite of what we want.

The `step1-part1-blink` tag at commit `f4ff0ce` marks the first such checkpoint.

---

## 4. CubeIDE workspace placement

The CubeIDE workspace is rooted at `Daisy_Claude/` itself (not at `seed_h750/`). One workspace can hold multiple projects, so when `custom_h743/` arrives, it joins the same workspace as a second project. This is why `Daisy_Claude/.metadata/` exists and is gitignored — it's the workspace state, distinct from project state.

The CubeIDE project (`.project`, `.cproject`, `.settings/`, `.launch`) lives **inside** the per-target subfolder, not at the workspace root. That's the natural Eclipse/CubeIDE pattern: the workspace is "your IDE session," each project is its own self-contained unit.

---

## 5. What this spec does NOT change

- All decisions in spec 02 §14 (CMSIS headers, SWD upload, run-from-flash, no dynamic allocation) are unchanged.
- Build invocation: `cd seed_h750 && make` from a shell with `arm-none-eabi-gcc` on `PATH`.
- Spec 01 (hardware overview) is unaffected — it describes hardware, not file layout.

---

## 6. Decisions — locked

1. **Per-target subfolder convention.** Each hardware target gets its own self-contained subfolder containing its Makefile, linker script, `src/`, `include/`, `build/`, and CubeIDE project metadata.
2. **Step progression via git.** Steps 1, 2, 3 etc. are commits/tags within a single project, not parallel folders.
3. **CubeIDE workspace at `Daisy_Claude/`.** Holds all per-target projects as siblings.
