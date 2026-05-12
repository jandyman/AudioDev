# Daisy_Claude Tools

## param_walker.py

Discover and inspect the parameter tree via OpenOCD memory reads. Useful for debugging the hierarchical parameter structure before building the macOS SwiftUI app.

### Setup

#### Firmware Build
1. Build the firmware in the parent directory:
   ```bash
   cd ../
   make clean && make
   ```

#### Start OpenOCD

**Option A: Manual (recommended for debugging)**

In a separate terminal, start OpenOCD with the provided config:
```bash
openocd -f tools/daisy_h750.cfg
```

You should see output like:
```
Info : STM32H750 core diagnostics in 0.0 ms
Info : Listening on port 4444
Info : Listening on port 3333
Info : Listening on port 6666
```

Then the script can connect to localhost:3333 (GDB remote) or localhost:4444 (telnet).

**Option B: Via STM32CubeIDE**

If you prefer the CubeIDE debugger, start it normally:
```
Debug → Debug As → STM32 C/C++ Application
```

However, CubeIDE's embedded OpenOCD may not expose the standard ports. The manual approach is more reliable for this tool.

#### Run from PyCharm

3. Open the `tools/` folder as a PyCharm project:
   ```bash
   cd seed_h750/tools/
   open . # or just open this folder in PyCharm
   ```

4. Right-click `param_walker.py` → **Run 'param_walker.py'**

   Or hit the ▶ button — the script defaults to `../build/seed_h750.map` and `localhost:4444`.

#### Run from CLI

Alternatively, run directly:
   ```bash
   python3 param_walker.py
   # or with a custom .map file:
   python3 param_walker.py /path/to/seed_h750.map --host localhost --port 4444
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
