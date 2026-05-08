# src/utils/local_api.py
# This is the local API utility for the application.

import os
import sys
import json
import socket

def query_local_api(path=None):
    """Query the Tailscale Local API for status JSON securely and with near-zero CPU footprint."""
    if sys.platform == "win32":
        pipe_path = path or r"\\.\pipe\ProtectedPrefix\administrators\Tailscale\tailscaled"
        try:
            # Open Windows Named Pipe
            f = open(pipe_path, "r+b", buffering=0)
            request = b"GET /localapi/v0/status HTTP/1.1\r\nHost: local-tailscaled\r\n\r\n"
            f.write(request)
            response = f.read(65536)
            f.close()
            
            parts = response.split(b"\r\n\r\n", 1)
            if len(parts) == 2:
                return json.loads(parts[1].decode('utf-8'))
        except Exception as e:
            raise RuntimeError(f"Named Pipe connection failed: {e}")
    else:
        sock_path = path or "/var/run/tailscale/tailscaled.sock"
        # Common macOS App Store socket path fallback
        mac_fallback = "/Library/Containers/io.tailscale.ipn.macos/Data/tailscaled.sock"
        if not os.path.exists(sock_path) and os.path.exists(mac_fallback):
            sock_path = mac_fallback
            
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(sock_path)
            request = b"GET /localapi/v0/status HTTP/1.1\r\nHost: local-tailscaled\r\n\r\n"
            s.sendall(request)
            
            response = b""
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                response += chunk
            s.close()
            
            parts = response.split(b"\r\n\r\n", 1)
            if len(parts) == 2:
                return json.loads(parts[1].decode('utf-8'))
        except Exception as e:
            raise RuntimeError(f"Unix Domain Socket connection failed: {e}")
            
    raise RuntimeError("Unsupported platform or empty response")

def is_local_api_available(path=None):
    """Universal, platform-independent check to see if the Tailscale Local API is available.
    Returns True if the Named Pipe (Windows) or Unix Domain Socket (Linux/macOS) accepts connection.
    """
    if sys.platform == "win32":
        pipe_path = path or r"\\.\pipe\ProtectedPrefix\administrators\Tailscale\tailscaled"
        try:
            # Try to open the Named Pipe briefly to test availability
            f = open(pipe_path, "r+b", buffering=0)
            f.close()
            return True
        except Exception:
            return False
    else:
        sock_path = path or "/var/run/tailscale/tailscaled.sock"
        mac_fallback = "/Library/Containers/io.tailscale.ipn.macos/Data/tailscaled.sock"
        if not os.path.exists(sock_path) and os.path.exists(mac_fallback):
            sock_path = mac_fallback
            
        if not os.path.exists(sock_path):
            return False
            
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.settimeout(0.5) # Sub-second timeout to keep checks lightning-fast
            s.connect(sock_path)
            s.close()
            return True
        except Exception:
            return False
