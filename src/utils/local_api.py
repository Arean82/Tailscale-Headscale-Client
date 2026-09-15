# src/utils/local_api.py
# This is the local API utility for the application.

import contextlib
import json
import os
import socket
import sys
import threading

# Default bound for Local API calls so a hung daemon can never freeze a caller
DEFAULT_TIMEOUT = 5.0


@contextlib.contextmanager
def _open_pipe_bounded(pipe_path, timeout):
    """Opens the Windows named pipe with a hard timeout and deterministic closure.

    A blocking open() on a named pipe waits until the server accepts the
    connection; if tailscaled is hung this would block forever. The open runs
    in a short-lived helper thread; on timeout we abandon that thread (it is
    a daemon and will die with the process) and raise TimeoutError.
    """
    result = {}

    def _open():
        try:
            result["f"] = open(pipe_path, "r+b", buffering=0)
        except OSError as e:
            result["e"] = e

    opener = threading.Thread(target=_open, daemon=True)
    opener.start()
    opener.join(timeout)
    if "f" in result:
        handle = result["f"]
        try:
            yield handle
        finally:
            handle.close()
        return
    if "e" in result:
        raise result["e"]
    raise TimeoutError(f"Named pipe open timed out after {timeout}s")


def query_local_api(path=None, timeout=DEFAULT_TIMEOUT):
    """Query the Tailscale Local API for status JSON with a bounded deadline."""
    if sys.platform == "win32":
        pipe_path = path or r"\\.\pipe\ProtectedPrefix\administrators\Tailscale\tailscaled"
        try:
            with _open_pipe_bounded(pipe_path, timeout) as f:
                request = b"GET /localapi/v0/status HTTP/1.1\r\nHost: local-tailscaled\r\n\r\n"
                f.write(request)
                response = f.read(65536)

            parts = response.split(b"\r\n\r\n", 1)
            if len(parts) == 2:
                return json.loads(parts[1].decode('utf-8'))
        except (OSError, ValueError) as e:
            raise RuntimeError(f"Named Pipe connection failed: {e}") from e
    else:
        sock_path = path or "/var/run/tailscale/tailscaled.sock"
        # Common macOS App Store socket path fallback
        mac_fallback = "/Library/Containers/io.tailscale.ipn.macos/Data/tailscaled.sock"
        if not os.path.exists(sock_path) and os.path.exists(mac_fallback):
            sock_path = mac_fallback

        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                s.connect(sock_path)
                request = b"GET /localapi/v0/status HTTP/1.1\r\nHost: local-tailscaled\r\n\r\n"
                s.sendall(request)

                response = b""
                while True:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    response += chunk

            parts = response.split(b"\r\n\r\n", 1)
            if len(parts) == 2:
                return json.loads(parts[1].decode('utf-8'))
        except (OSError, ValueError) as e:
            raise RuntimeError(f"Unix Domain Socket connection failed: {e}") from e

    raise RuntimeError("Unsupported platform or empty response")

def is_local_api_available(path=None):
    """Universal, platform-independent check to see if the Tailscale Local API is available.
    Returns True if the Named Pipe (Windows) or Unix Domain Socket (Linux/macOS) accepts connection.
    """
    if sys.platform == "win32":
        pipe_path = path or r"\\.\pipe\ProtectedPrefix\administrators\Tailscale\tailscaled"
        try:
            # Try to open the Named Pipe briefly to test availability
            with open(pipe_path, "r+b", buffering=0):
                pass
            return True
        except OSError:
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
        except OSError:
            return False
