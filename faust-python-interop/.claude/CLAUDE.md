# Faust-Python Interop Project - Claude Context

This project explores Faust DSP code generation and interoperability with Python tools.

---

## Project Overview

**Purpose:** Evaluate Faust code generation capabilities and integration with Python-based DSP tools

**Key Technologies:**
- **Faust:** Functional audio DSP programming language
- **Python:** For analysis, design tools, and wrappers
- Code generation targets: C++, Python bindings, Max externals (potentially)

---

## Project Structure

```
faust-python-interop/
├── .claude/            # Claude Code context (this file)
├── faust/              # Faust DSP source files (.dsp)
├── python/             # Python tools, wrappers, analysis
├── tests/              # Test code and examples
└── README.md           # Project documentation
```

---

## Faust Overview

**What is Faust:**
- Functional AUdio STream language
- Compiles to highly optimized C++, LLVM, etc.
- Block diagram composition
- Mathematical approach to DSP

**Typical Workflow:**
1. Write `.dsp` file with Faust code
2. Compile to target (C++, Python, Max external, etc.)
3. Integrate generated code into host application

---

## Python Integration Goals

**Potential approaches to explore:**

1. **Faust → C++ → Python bindings:**
   - Use pybind11 or similar
   - Python interface to Faust-generated DSP

2. **Faust for design, Python for analysis:**
   - Generate frequency responses
   - Plot characteristics
   - Design-time tools

3. **Code generation workflows:**
   - Automate Faust compilation
   - Template-based code generation
   - Integration with build systems

---

## Related to Max Experiments

This project is a sibling to `Max Experiments/`:
- Shares parent git repo (`AudioDev`)
- May generate Max externals from Faust code
- Complementary approach: Faust (functional) vs. C++ (imperative)

---

## Instructions for Claude

- Focus on experimental/evaluation code
- Document learnings about Faust capabilities
- Keep examples simple and focused
- Prioritize understanding over production code
- Compare approaches with Max C++ externals

---

## Resources

- Faust documentation: https://faust.grame.fr
- Faust compiler: `faust` (command-line tool)
- Python: Standard scientific stack (numpy, scipy, matplotlib)

---

*This is a Claude Code context file. It provides project-specific information that supplements the parent AudioDev context.*
