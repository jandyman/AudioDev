#!/usr/bin/env python3
"""Diagnose OSC sending issues"""

from pythonosc import udp_client
from pythonosc.osc_message_builder import OscMessageBuilder
import socket

print("=== OSC Diagnostic Test ===\n")

# Check if we can create a socket
print("1. Testing UDP socket creation...")
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print("   ✓ Socket created successfully")
    sock.close()
except Exception as e:
    print(f"   ✗ Socket creation failed: {e}")
    exit(1)

# Create OSC client
print("\n2. Creating OSC client...")
try:
    client = udp_client.SimpleUDPClient("127.0.0.1", 7400)
    print(f"   ✓ Client created")
    print(f"   Target: {client._address}:{client._port}")
except Exception as e:
    print(f"   ✗ Client creation failed: {e}")
    exit(1)

# Try to send a message
print("\n3. Sending OSC message /gain 0.5...")
try:
    client.send_message("/gain", 0.5)
    print("   ✓ send_message() completed without error")
except Exception as e:
    print(f"   ✗ Send failed: {e}")
    exit(1)

# Send a few more with delays
print("\n4. Sending test sequence...")
import time
for val in [0.0, 0.25, 0.5, 0.75, 1.0]:
    print(f"   Sending /gain {val}")
    client.send_message("/gain", val)
    time.sleep(0.5)

print("\n=== Test Complete ===")
print("\nIf udpreceive in Max didn't flash, the problem is:")
print("  - Max isn't actually receiving UDP packets")
print("  - Firewall blocking localhost (unlikely)")
print("  - Wrong Max object or configuration")
