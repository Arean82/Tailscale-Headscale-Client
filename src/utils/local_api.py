# src/utils/local_api.py
# This is the local API utility for the application.

import json
import os
import socket
import sys
import threading
import time
from collections.abc import Callable

# Default bound for Local API calls so a hung daemon can never freeze a caller
DEFAULT_TIMEOUT = 5.0

_LOCAL_API_REQUEST = b"GET /localapi/v0/status HTTP/1.1\r\nHost: local-tailscaled\r\n\r\n"


class LocalApiError(RuntimeError):
    """The Local API could not be reached, or answered with an unusable response."""


class LocalApiUnauthorized(LocalApiError):
    """The daemon answered but refused this client (HTTP 401/403).

    On Windows the Local API is served over an administrators-only named pipe,
    so a non-elevated process is refused even though the pipe itself opens.
    Callers should fall back to the CLI rather than retry.
    """


def _parse_head(raw):
    """Splits a header block into (status_code, reason, headers)."""
    lines = raw.split(b"\r\n")
    parts = lines[0].decode("latin-1", errors="replace").split(" ", 2)
    if len(parts) < 2 or not parts[1].isdigit():
        raise LocalApiError(f"Malformed HTTP status line: {lines[0]!r}")
    status = int(parts[1])
    reason = parts[2] if len(parts) > 2 else ""
    headers = {}
    for line in lines[1:]:
        name, sep, value = line.partition(b":")
        if sep:
            headers[name.decode("latin-1").strip().lower()] = value.decode("latin-1").strip()
    return status, reason, headers


def _dechunk(body):
    """Decodes an HTTP/1.1 chunked body. Returns (decoded, complete)."""
    out = b""
    while True:
        line_end = body.find(b"\r\n")
        if line_end < 0:
            return out, False
        try:
            size = int(body[:line_end].split(b";", 1)[0].strip(), 16)
        except ValueError:
            return out, False
        if size == 0:
            return out, True
        start = line_end + 2
        if len(body) < start + size + 2:
            return out, False  # chunk still in flight
        out += body[start:start + size]
        body = body[start + size + 2:]


def _read_response(read, deadline):
    """Reads a complete HTTP response, honouring Content-Length or chunked framing.

    A single read() can return the headers without the body (observed on the
    Windows pipe), and the ~66 KB status payload is sent chunked, so completion
    is decided by framing rather than by "did one read return bytes".
    """
    buf = b""
    while b"\r\n\r\n" not in buf:
        if time.monotonic() > deadline:
            raise LocalApiError("timed out waiting for the Local API response headers")
        chunk = read(65536)
        if not chunk:
            break
        buf += chunk

    head, sep, body = buf.partition(b"\r\n\r\n")
    if not sep:
        raise LocalApiError("Local API returned no response (connection closed)")

    status, reason, headers = _parse_head(head)

    if headers.get("transfer-encoding", "").lower() == "chunked":
        decoded = b""
        while True:
            # Keep the raw buffer intact: an incomplete chunk needs the bytes
            # that follow it, which may not have arrived yet.
            decoded, complete = _dechunk(body)
            if complete:
                break
            if time.monotonic() > deadline:
                break
            chunk = read(65536)
            if not chunk:
                break
            body += chunk
        body = decoded
    elif "content-length" in headers:
        try:
            expected = int(headers["content-length"])
        except ValueError:
            expected = len(body)
        while len(body) < expected:
            if time.monotonic() > deadline:
                break
            chunk = read(65536)
            if not chunk:
                break
            body += chunk
        body = body[:expected]  # never let a surplus read bleed into the body

    return status, reason, body


def _status_payload(status, reason, body, where):
    """Turns a parsed response into the status dict, or raises a precise error."""
    if status == 200:
        try:
            return json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as e:
            raise LocalApiError(f"{where}: unparseable status payload: {e}") from e

    if status in (401, 403):
        detail = body.decode("latin-1", errors="replace").strip()
        message = (
            f"{where}: Local API refused this client (HTTP {status} {reason}). "
            "On Windows the Local API pipe is administrators-only, so a non-elevated "
            "process cannot use it; the CLI fallback is used instead."
        )
        raise LocalApiUnauthorized(f"{message} Daemon said: {detail}" if detail else message)

    raise LocalApiError(f"{where}: unexpected HTTP {status} {reason}")


def _run_bounded[T](func: Callable[[], T], timeout: float, description: str) -> T:
    """Runs func() on a daemon thread, returning its result within the deadline.

    OpenFile/ReadFile on a named pipe have no timeout of their own, so a hung
    daemon can only be shed by abandoning the worker thread. It is a daemon, and
    whatever handle it holds is opened *and* closed inside func() — no handle
    ever escapes the thread, so nothing can be orphaned by a timeout.
    """
    results: list[T] = []
    errors: list[BaseException] = []
    done = threading.Event()

    def runner():
        try:
            results.append(func())
        except (OSError, LocalApiError) as e:
            errors.append(e)
        finally:
            done.set()

    threading.Thread(target=runner, daemon=True).start()

    if not done.wait(timeout):
        raise LocalApiError(f"{description} timed out after {timeout}s")
    if errors:
        raise errors[0]
    if not results:
        raise LocalApiError(f"{description} failed unexpectedly")
    return results[0]


def _pipe_request_bounded(pipe_path, request, timeout):
    """One HTTP request over the named pipe, bounded end to end (open, write, read)."""

    def request_once():
        with open(pipe_path, "r+b", buffering=0) as f:
            f.write(request)
            return _read_response(f.read, time.monotonic() + timeout)

    return _run_bounded(request_once, timeout, "Local API named-pipe request")


def query_local_api(path=None, timeout=DEFAULT_TIMEOUT):
    """Query the Tailscale Local API for status JSON with a bounded deadline.

    Raises:
        LocalApiUnauthorized: the daemon answered but refused this client
            (HTTP 401/403) — on Windows the pipe is administrators-only.
        LocalApiError: any other transport, framing or payload failure.
    """
    deadline = time.monotonic() + timeout

    if sys.platform == "win32":
        pipe_path = path or r"\\.\pipe\ProtectedPrefix\administrators\Tailscale\tailscaled"
        try:
            status, reason, body = _pipe_request_bounded(pipe_path, _LOCAL_API_REQUEST, timeout)
        except OSError as e:
            raise LocalApiError(f"Named Pipe connection failed: {e}") from e
        return _status_payload(status, reason, body, "Named Pipe")
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
                s.sendall(_LOCAL_API_REQUEST)
                status, reason, body = _read_response(s.recv, deadline)
        except LocalApiError:
            raise
        except (OSError, ValueError) as e:
            raise LocalApiError(f"Unix Domain Socket connection failed: {e}") from e
        return _status_payload(status, reason, body, "Unix Domain Socket")

def is_local_api_available(path=None):
    """Universal, platform-independent check to see if the Tailscale Local API is available.
    Returns True if the Named Pipe (Windows) or Unix Domain Socket (Linux/macOS) accepts connection.
    """
    if sys.platform == "win32":
        pipe_path = path or r"\\.\pipe\ProtectedPrefix\administrators\Tailscale\tailscaled"

        def probe():
            with open(pipe_path, "r+b", buffering=0):
                pass

        try:
            # Bounded: a hung daemon must not block the caller's thread
            _run_bounded(probe, 0.5, "Named pipe probe")
            return True
        except (OSError, LocalApiError):
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
