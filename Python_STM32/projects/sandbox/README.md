# sandbox — Python experimentation scratch space

Throwaway experiments: prototype an idea in numpy, audition a Faust block, or
drive a built C++ graph and plot its probes. It lives under `projects/` on
purpose — being two levels under `Python_STM32/` like every real project means
the shared-tooling import header, `graph_build.mk` includes, and sibling-project
`build/` access all work with the **same relative paths** the demos use, with no
new conventions to learn.

## Using it

Copy `_template.py` to `<whatever>_lab.py` and hack. Conventions (see
`docs/python_experimentation.md`): run from PyCharm under the `scipy` env, no CLI
args, config variables at the bottom, interactive plots (no `savefig`), and
**never** a `test_` prefix (pytest would collect it and block plotting).

The template already wires up `lib.diagnostic_plot` (file I/O + zoom/pan +
`mark_events`) and shows how to optionally import a sibling project's built
module (e.g. `from build.pybind_pitch_shifter import pitch_shifter` after
`make -f pitch_shifter.make` in that project).

## Git policy

Sandbox experiments **are tracked** — commit them like any other file. Only build
artifacts are ignored (`build/`, `*.so`; `__pycache__/` is handled repo-wide).
