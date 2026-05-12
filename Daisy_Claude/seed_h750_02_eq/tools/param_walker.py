#!/usr/bin/env python3
"""
param_walker.py — Discover and manipulate firmware parameters via OpenOCD.

Usage:
  python3 param_walker.py <map_file> [--host localhost] [--port 4444]

The .map file (e.g., build/seed_h750.map) is parsed to find param_anchor address.
Connects to OpenOCD's telnet interface on localhost:4444 (default) and walks the
parameter tree, reading node structures from DTCMRAM.

Commands:
  tree              Show the full parameter tree
  read <path>       Read a parameter value (e.g., "read left/shelf_gain")
  write <path> <val>  Write a parameter value
  exit              Exit
"""

import socket
import struct
import sys
import re
from pathlib import Path


class OpenOcdClient:
    """Minimal OpenOCD telnet client for memory operations."""

    def __init__(self, host="localhost", port=4444, timeout=2.0):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.sock.connect((host, port))
        # Read banner
        try:
            _ = self.sock.recv(1024)
        except socket.timeout:
            pass

    def cmd(self, command):
        """Send a command and read until we see the prompt."""
        self.sock.sendall((command + "\n").encode())
        response = b""
        try:
            while True:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                response += chunk
                # Look for OpenOCD prompt (usually "> " or similar)
                if b"> " in response:
                    break
        except socket.timeout:
            pass
        return response.decode("utf-8", errors="ignore")

    def read_u32(self, addr):
        """Read a 32-bit word at address (DTCMRAM or SRAM)."""
        resp = self.cmd(f"md32 0x{addr:x} 1")
        # Response format: 0xaddress: 0xvalue
        match = re.search(r"0x[0-9a-f]+:\s+0x([0-9a-f]+)", resp, re.IGNORECASE)
        if match:
            return int(match.group(1), 16)
        raise ValueError(f"Failed to parse md32 response: {resp}")

    def read_float(self, addr):
        """Read a 32-bit float at address."""
        val_u32 = self.read_u32(addr)
        return struct.unpack("f", struct.pack("I", val_u32))[0]

    def write_u32(self, addr, value):
        """Write a 32-bit word at address."""
        self.cmd(f"mw32 0x{addr:x} 0x{value:x}")

    def write_float(self, addr, value):
        """Write a 32-bit float at address."""
        val_u32 = struct.unpack("I", struct.pack("f", value))[0]
        self.write_u32(addr, val_u32)

    def close(self):
        try:
            self.sock.close()
        except:
            pass


def find_param_anchor(map_file):
    """Extract param_anchor address from linker map file."""
    with open(map_file) as f:
        content = f.read()
    # Look for: param_anchor = 0x20000000 (or similar)
    match = re.search(r"param_anchor\s+=\s+0x([0-9a-f]+)", content, re.IGNORECASE)
    if match:
        return int(match.group(1), 16)
    raise ValueError(f"param_anchor not found in {map_file}")


# Node types
NODE_GROUP = 0
NODE_ARRAY = 1
NODE_PARAM = 2

# Magic numbers
PARAM_ANCHOR_MAGIC = 0xDA151E00
PARAM_NODE_MAGIC = 0xDA151E01


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


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    map_file = Path(sys.argv[1])
    host = "localhost"
    port = 4444

    # Parse args
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

    print(f"Connecting to OpenOCD at {host}:{port}...")
    try:
        ocd = OpenOcdClient(host, port)
    except Exception as e:
        print(f"ERROR: Failed to connect to OpenOCD: {e}")
        print("Make sure OpenOCD is running (e.g., via STM32CubeIDE debugger)")
        sys.exit(1)

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
