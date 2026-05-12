#!/usr/bin/env python3
"""
param_walker.py — Discover and manipulate firmware parameters via OpenOCD telnet.

Usage (PyCharm):
  Just run the script — it defaults to ../build/seed_h750.map

Usage (CLI):
  python3 param_walker.py [map_file] [--host localhost] [--port 4444]

The .map file is parsed to find param_anchor address. Connects to OpenOCD's
telnet interface (localhost:4444 by default) and walks the parameter tree
structure from DTCMRAM, displaying the hierarchy and current values.

Typical workflow:
  1. Build firmware: cd .. && make clean && make
  2. Start OpenOCD in a separate terminal:
       openocd -f interface/stlink.cfg -f target/stm32h7x.cfg
  3. Run this script (hit play button in PyCharm)
  4. Step through to inspect the parameter tree
"""

import socket
import struct
import sys
import re
from pathlib import Path


class OpenOcdTelnetClient:
    """OpenOCD telnet client for memory operations (port 4444)."""

    def __init__(self, host="localhost", port=4444, timeout=2.0, auto_resume=True):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.sock.connect((host, port))
        # Read and discard banner
        try:
            banner = self.sock.recv(1024)
        except socket.timeout:
            pass
        # Check if target is halted; if so, resume it
        if auto_resume:
            self._ensure_running()

    def _ensure_running(self):
        """Check if target is halted; resume if so."""
        resp = self._cmd_raw("targets")  # Ask for target state
        if "halted" in resp.lower():
            print("  Target was halted. Resuming...", flush=True)
            self._cmd_raw("resume")
            import time
            time.sleep(0.2)  # Let it start
            return True
        return False

    def _cmd_raw(self, command):
        """Send a command and read response (used before socket is fully setup)."""
        import time
        self.sock.sendall((command + "\n").encode())
        time.sleep(0.05)
        response = b""
        old_timeout = self.sock.gettimeout()
        try:
            self.sock.settimeout(0.15)
            while True:
                try:
                    chunk = self.sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                except socket.timeout:
                    break
        finally:
            self.sock.settimeout(old_timeout)
        return response.decode("utf-8", errors="ignore")

    def _cmd(self, command):
        """Send a command and read the response with a small delay."""
        import time
        self.sock.sendall((command + "\n").encode())
        time.sleep(0.05)  # Give OpenOCD time to respond

        # Read with short timeout - collect all data that arrives quickly
        response = b""
        old_timeout = self.sock.gettimeout()
        try:
            self.sock.settimeout(0.15)  # Very short timeout
            while True:
                try:
                    chunk = self.sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                except socket.timeout:
                    break
        finally:
            self.sock.settimeout(old_timeout)
        return response.decode("utf-8", errors="ignore")

    def read_u32(self, addr):
        """Read a 32-bit word at address via 'mdw' (memory display word)."""
        resp = self._cmd(f"mdw 0x{addr:x}")
        # Response format: "0x20000024: da151e00" (with possible extra whitespace/nulls)
        # Extract the hex value after the colon
        match = re.search(r":\s*([0-9a-f]+)", resp, re.IGNORECASE)
        if match:
            hex_str = match.group(1)
            return int(hex_str, 16)
        # If no match, show what we got for debugging
        raise ValueError(f"Failed to parse mdw response. Got: {repr(resp[:200])}")

    def read_float(self, addr):
        """Read a 32-bit float at address."""
        val_u32 = self.read_u32(addr)
        return struct.unpack("f", struct.pack("I", val_u32))[0]

    def write_u32(self, addr, value):
        """Write a 32-bit word at address via 'mw' (memory write)."""
        self._cmd(f"mw 0x{addr:x} 0x{value:x}")

    def write_float(self, addr, value):
        """Write a 32-bit float at address."""
        val_u32 = struct.unpack("I", struct.pack("f", value))[0]
        self.write_u32(addr, val_u32)

    def set_params_dirty_flag(self, flag_addr, bits):
        """Set specific bits in the params_dirty_flag (OR operation)."""
        current = self.read_u32(flag_addr + 4)  # flags is at offset 4 in ParamsDirtyFlag
        self.write_u32(flag_addr + 4, current | bits)

    def clear_params_dirty_flag(self, flag_addr):
        """Clear all bits in the params_dirty_flag."""
        self.write_u32(flag_addr + 4, 0)

    def close(self):
        try:
            self.sock.close()
        except:
            pass


def find_param_anchor(map_file):
    """Extract param_anchor address from linker map file.

    The .map file format is:
                0x20000024                param_anchor
    """
    with open(map_file) as f:
        content = f.read()
    # Look for: 0x20000024                param_anchor
    match = re.search(r"0x([0-9a-f]+)\s+param_anchor", content, re.IGNORECASE)
    if match:
        return int(match.group(1), 16)
    raise ValueError(f"param_anchor not found in {map_file}")


def find_params_dirty_flag(map_file):
    """Extract params_dirty_flag address from linker map file."""
    with open(map_file) as f:
        content = f.read()
    match = re.search(r"0x([0-9a-f]+)\s+params_dirty_flag", content, re.IGNORECASE)
    if match:
        return int(match.group(1), 16)
    raise ValueError(f"params_dirty_flag not found in {map_file}")


# Node types
NODE_GROUP = 0
NODE_ARRAY = 1
NODE_PARAM = 2

# Magic numbers
PARAM_ANCHOR_MAGIC = 0xDA151E00
PARAM_NODE_MAGIC = 0xDA151E01
PARAMS_DIRTY_FLAG_MAGIC = 0xDA151E02

# Handshaking bits
PARAMS_DIRTY_BIT_DIRTY = 0x1  # bit 0: host has written parameters
PARAMS_DIRTY_BIT_READY = 0x2  # bit 1: background has new coefficients


def read_node_header(ocd, addr):
    """Read a ParamNodeHdr from memory (20 bytes: magic, type, unit, pad, name*, child*, next*)."""
    magic = ocd.read_u32(addr + 0)
    # type and unit are packed at offset 4-5; read as u32 and mask
    type_unit = ocd.read_u32(addr + 4)
    node_type = (type_unit >> 0) & 0xFF
    unit = (type_unit >> 8) & 0xFF
    name_ptr = ocd.read_u32(addr + 8)
    child_ptr = ocd.read_u32(addr + 12)
    next_ptr = ocd.read_u32(addr + 16)
    return {
        "magic": magic,
        "type": node_type,
        "unit": unit,
        "name_ptr": name_ptr,
        "child": child_ptr,
        "next": next_ptr,
        "addr": addr,
    }


def read_string(ocd, addr, max_len=64):
    """Read a null-terminated string from flash memory (slow, byte by byte)."""
    s = ""
    for i in range(max_len):
        # String is in flash; read via OpenOCD's flash read
        # For simplicity, just read as "unknown" for now
        pass
    return "?"


def read_param_node(ocd, addr):
    """Read a full ParamNode (leaf parameter)."""
    hdr = read_node_header(ocd, addr)
    value = ocd.read_float(addr + 20)
    min_val = ocd.read_float(addr + 24)
    max_val = ocd.read_float(addr + 28)
    default_val = ocd.read_float(addr + 32)
    return {
        **hdr,
        "value": value,
        "min": min_val,
        "max": max_val,
        "default": default_val,
    }


def walk_tree(ocd, root_addr, path="", indent=0):
    """Recursively walk the parameter tree and print it."""
    if root_addr == 0:
        return

    hdr = read_node_header(ocd, root_addr)

    if hdr["magic"] != PARAM_NODE_MAGIC:
        print(f"Warning: magic mismatch at 0x{root_addr:x}: 0x{hdr['magic']:x}")
        return

    prefix = "  " * indent
    node_type_name = ["GROUP", "ARRAY", "PARAM"][hdr["type"]]

    if hdr["type"] == NODE_PARAM:
        param = read_param_node(ocd, root_addr)
        full_path = f"{path}/{node_type_name}" if path else node_type_name
        print(
            f"{prefix}[PARAM] {full_path}: value={param['value']:.3f} "
            f"({param['min']:.3f}..{param['max']:.3f})"
        )
    else:
        full_path = f"{path}/{node_type_name}" if path else node_type_name
        print(f"{prefix}[{node_type_name}] {full_path}")

        if hdr["child"]:
            walk_tree(ocd, hdr["child"], full_path, indent + 1)

    if hdr["next"]:
        walk_tree(ocd, hdr["next"], path, indent)


def write_parameter(ocd, param_addr, new_value, params_dirty_flag_addr, wait_for_clear=True):
    """Write a parameter value and trigger coefficient recomputation.

    Steps:
    1. Write the new parameter value
    2. Set params_dirty bit 0 (DIRTY) to signal background task
    3. Optionally wait for bit to clear (indicates ISR applied the change)

    Args:
      ocd: OpenOcdTelnetClient instance
      param_addr: Address of the parameter (float)
      new_value: New parameter value (float)
      params_dirty_flag_addr: Address of params_dirty_flag structure
      wait_for_clear: If True, wait for the DIRTY bit to clear
    """
    print(f"  Writing parameter at 0x{param_addr:x} = {new_value:.3f}", flush=True)
    ocd.write_float(param_addr, new_value)

    print(f"  Setting DIRTY flag...", flush=True)
    ocd.set_params_dirty_flag(params_dirty_flag_addr, PARAMS_DIRTY_BIT_DIRTY)

    if wait_for_clear:
        print(f"  Waiting for DSP to apply changes...", flush=True)
        import time
        max_wait = 50  # 50 * 0.1 sec = 5 seconds
        for i in range(max_wait):
            flags = ocd.read_u32(params_dirty_flag_addr + 4)
            if (flags & PARAMS_DIRTY_BIT_DIRTY) == 0:
                print(f"  ✓ DSP applied the change after {i*0.1:.1f}ms", flush=True)
                return True
            time.sleep(0.1)
        print(f"  ✗ Timeout waiting for DIRTY bit to clear", flush=True)
        return False
    return True


def main():
    # Default to .map file in ../build/ (relative to this script)
    script_dir = Path(__file__).parent.parent
    default_map = script_dir / "build" / "seed_h750.map"

    map_file = default_map
    host = "localhost"
    port = 4444  # OpenOCD telnet port

    # Parse args if provided
    if len(sys.argv) > 1:
        map_file = Path(sys.argv[1])
        for i in range(2, len(sys.argv)):
            if sys.argv[i] == "--host" and i + 1 < len(sys.argv):
                host = sys.argv[i + 1]
            elif sys.argv[i] == "--port" and i + 1 < len(sys.argv):
                port = int(sys.argv[i + 1])

    if not map_file.exists():
        print(f"ERROR: Map file not found: {map_file}")
        sys.exit(1)

    print(f"Reading map file: {map_file}")
    try:
        anchor_addr = find_param_anchor(str(map_file))
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    print(f"Found param_anchor at 0x{anchor_addr:x}")

    print(f"Connecting to OpenOCD telnet at {host}:{port}...")
    try:
        ocd = OpenOcdTelnetClient(host, port)
    except Exception as e:
        print(f"ERROR: Failed to connect: {e}")
        print("Make sure OpenOCD is running:")
        print("  openocd -f interface/stlink.cfg -f target/stm32h7x.cfg")
        sys.exit(1)

    # Find params_dirty_flag address for write operations
    try:
        params_dirty_flag_addr = find_params_dirty_flag(str(map_file))
        print(f"Found params_dirty_flag at 0x{params_dirty_flag_addr:x}")
    except ValueError as e:
        print(f"Warning: {e} — write operations will not work")
        params_dirty_flag_addr = None

    try:
        # Verify anchor magic
        try:
            anchor_magic = ocd.read_u32(anchor_addr)
        except Exception as e:
            print(f"ERROR: Failed to read memory at 0x{anchor_addr:x}: {e}")
            sys.exit(1)

        if anchor_magic != PARAM_ANCHOR_MAGIC:
            print(
                f"ERROR: Expected magic 0x{PARAM_ANCHOR_MAGIC:x}, "
                f"got 0x{anchor_magic:x}"
            )
            sys.exit(1)

        print("✓ param_anchor magic verified")
        root_ptr = ocd.read_u32(anchor_addr + 8)
        print(f"✓ Root parameter group at 0x{root_ptr:x}\n")
        print("Parameter Tree:")
        print("-" * 60)
        walk_tree(ocd, root_ptr)
        print("-" * 60)

    finally:
        ocd.close()


if __name__ == "__main__":
    main()
