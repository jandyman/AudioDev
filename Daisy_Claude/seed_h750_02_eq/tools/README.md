# Daisy_Claude Tools

## param_walker.py

Discover and inspect the parameter tree via OpenOCD memory reads. Useful for debugging the hierarchical parameter structure before building the macOS SwiftUI app.

### Setup

1. Build the firmware normally:
   ```bash
   cd ../
   make clean && make
   ```

2. Start the debugger in STM32CubeIDE (or start OpenOCD separately):
   ```bash
   # Via CubeIDE: Debug → Debug As → STM32 C/C++ Application
   # This starts OpenOCD on localhost:4444
   ```

3. Run the tool:
   ```bash
   python3 tools/param_walker.py build/seed_h750.map
   ```

### Expected output

The tool reads the parameter tree structure from DTCMRAM and prints it like:
```
Parameter Tree:
[GROUP] root
  [GROUP] root/left
    [PARAM] root/left/shelf_gain: value=0.000 (-12.000..12.000)
    [PARAM] root/left/shelf_fc: value=2000.000 (100.000..10000.000)
    [PARAM] root/left/lp_fc: value=10000.000 (100.000..20000.000)
  [GROUP] root/right
    ...
```

### How it works

1. **Map file parsing:** Reads the linker .map file to find the `param_anchor` symbol's address (e.g., 0x20000024)
2. **Memory reading:** Connects to OpenOCD's telnet interface (port 4444) and reads node structures from DTCMRAM
3. **Tree traversal:** Walks the parameter tree via child/next pointers, reading node headers and parameter values
4. **Magic verification:** Checks PARAM_NODE_MAGIC and PARAM_ANCHOR_MAGIC to ensure the structure is valid

### Debugging tips

- **Connection refused:** Make sure OpenOCD is running (start the CubeIDE debugger)
- **Magic mismatch:** The DTCMRAM layout might not match params.h; check that params_init() is being called in main()
- **Address not found:** Verify the .map file is from the current build

### Next steps

Once this tool shows the tree correctly, the macOS SwiftUI app will use the same discovery protocol to walk the tree and render parameter controls.
