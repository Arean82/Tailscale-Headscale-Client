# src/core/executor.py
"""Single asynchronous execution seam for all Tailscale CLI / LocalAPI I/O.

Every operation either streams through a QProcess (event-loop driven, never
blocks the GUI thread) or runs on a dedicated worker thread with an explicit
timeout. GUI code must never call tailscale, subprocess, or the LocalAPI
socket directly — everything goes through TailscaleExecutor so timeouts,
credential redaction, and error normalization have one home (Candidate 1).
"""

import json
import logging
import subprocess
import sys

from PySide6.QtCore import QObject, QProcess, QThread, Signal, Slot

logger = logging.getLogger("TailscaleClient.Executor")


def get_tailscale_path():
    """Dynamically resolve the absolute path to the Tailscale executable on macOS, Windows, and Linux."""
    import os
    import shutil
    resolved = shutil.which("tailscale")
    if resolved:
        return resolved

    if sys.platform == "darwin":
        mac_paths = [
            "/Applications/Tailscale.app/Contents/Resources/cli/tailscale",
            "/opt/homebrew/bin/tailscale",
            "/usr/local/bin/tailscale",
            "/Applications/Tailscale.app/Contents/MacOS/Tailscale"
        ]
        for path in mac_paths:
            if os.path.exists(path):
                return path

    elif sys.platform == "win32":
        win_paths = [
            os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Tailscale", "tailscale.exe"),  # noqa: SIM112 (Windows env var names)
            os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Tailscale", "tailscale.exe"),  # noqa: SIM112 (Windows env var names)
            os.path.join(os.environ.get("LocalAppData", ""), "Programs", "Tailscale", "tailscale.exe")  # noqa: SIM112 (Windows env var names)
        ]
        for path in win_paths:
            if os.path.exists(path):
                return path

    elif sys.platform.startswith("linux"):
        linux_paths = [
            "/usr/sbin/tailscale",
            "/usr/bin/tailscale",
            "/usr/local/bin/tailscale",
            "/sbin/tailscale"
        ]
        for path in linux_paths:
            if os.path.exists(path):
                return path

    # Fallback default
    return "tailscale"


def _popen_kwargs():
    """Windows: suppress the console window for CLI subprocesses."""
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return {"startupinfo": startupinfo, "creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


def status_from_json(data: dict):
    """Maps a LocalAPI/CLI status JSON payload to (is_connected, status_text, ips)."""
    state = data.get("BackendState", "")
    ips = data.get("TailscaleIPs", [])
    if state == "Running":
        return True, "Connected", ips
    if state == "NeedsLogin":
        return False, "Logged Out", ips
    if state == "NeedsMachineAuth":
        return False, "Pending Admin Approval", ips
    return False, (state or "Disconnected"), ips


def status_from_text(output: str):
    """Legacy text heuristics for CLI output that is not valid JSON."""
    lowered = output.lower()
    if "logged out" in lowered:
        return False, "Logged Out"
    if "running" in lowered or "connected" in lowered:
        return True, "Connected"
    return False, "Disconnected"


class _BlockingWorker(QObject):
    """Runs on the executor's QThread; every call has a hard timeout.

    Request signals are emitted from the GUI thread and auto-queue to these
    slots, which execute on the worker thread. The slots are also directly
    callable for unit tests.
    """

    status_ready = Signal(dict)
    cli_done = Signal(str, int, str, str)      # op_id, exit_code, stdout, stderr
    prelogout_done = Signal(bool, dict)        # logout_ok, pending connect args

    _request_status = Signal(bool)
    _request_cli = Signal(str, list, int)
    _request_prelogout = Signal(dict)

    def __init__(self):
        super().__init__()
        self._request_status.connect(self.run_status)
        self._request_cli.connect(self.run_cli)
        self._request_prelogout.connect(self.run_prelogout)

    @Slot(bool)
    def run_status(self, use_local_api: bool) -> None:
        payload = {"connected": False, "text": "Disconnected", "ips": [], "raw_data": {}}
        if use_local_api:
            try:
                from src.utils.local_api import query_local_api
                data = query_local_api(timeout=2.0)
                connected, text, ips = status_from_json(data)
                payload = {"connected": connected, "text": text, "ips": ips, "raw_data": data}
                self.status_ready.emit(payload)
                return
            except (RuntimeError, OSError, ValueError) as e:
                # Local API unavailable; fall through to the CLI on this thread
                logger.debug(f"Local API status query failed, falling back to CLI: {e}")

        try:
            result = subprocess.run(
                [get_tailscale_path(), "status", "--json"],
                capture_output=True, text=True, timeout=6, check=False, shell=False, **_popen_kwargs()
            )
            try:
                data = json.loads(result.stdout)
            except (ValueError, TypeError):
                data = {}
            if data:
                connected, text, ips = status_from_json(data)
            else:
                connected, text = status_from_text(result.stdout)
                ips = []
            payload = {"connected": connected, "text": text, "ips": ips, "raw_data": data}
        except subprocess.TimeoutExpired:
            payload = {"connected": False, "text": "Error: daemon not responding", "ips": [], "raw_data": {}}
        except (subprocess.SubprocessError, OSError) as e:
            logger.error(f"Status query failed: {e}")
            payload = {"connected": False, "text": "Error: tailscale CLI unavailable", "ips": [], "raw_data": {}}
        self.status_ready.emit(payload)

    @Slot(str, list, int)
    def run_cli(self, op_id: str, args: list, timeout: int) -> None:
        try:
            result = subprocess.run(
                [get_tailscale_path()] + list(args),
                capture_output=True, text=True, timeout=timeout, check=False, shell=False, **_popen_kwargs()
            )
            self.cli_done.emit(op_id, result.returncode, result.stdout, result.stderr)
        except subprocess.TimeoutExpired:
            self.cli_done.emit(op_id, -1, "", f"Command timed out after {timeout}s")
        except (subprocess.SubprocessError, OSError) as e:
            self.cli_done.emit(op_id, -1, "", str(e))

    @Slot(dict)
    def run_prelogout(self, connect_args: dict) -> None:
        """Server-switch guard: logout from the old control plane before 'up'
        so the old machine key cannot conflict. Runs on the worker thread so
        the GUI never blocks on it."""
        ok = False
        try:
            result = subprocess.run(
                [get_tailscale_path(), "logout"],
                capture_output=True, timeout=5, check=False, shell=False, **_popen_kwargs()
            )
            ok = result.returncode == 0
        except (subprocess.SubprocessError, OSError) as e:
            logger.warning(f"Pre-connect logout failed (proceeding anyway): {e}")
        self.prelogout_done.emit(ok, connect_args)


class TailscaleExecutor(QObject):
    """Owns all tailscale I/O: one streaming QProcess for interactive commands
    (up/switch/logout) and one worker thread for bounded blocking calls
    (status, ping, netcheck, version, pre-connect logout)."""

    # Streaming command surface (kept compatible with the old TailscaleProcess)
    output_received = Signal(str)
    error_received = Signal(str)
    sso_url_found = Signal(str)
    finished = Signal(int, str)

    # Async result surface
    status_ready = Signal(dict)
    cli_finished = Signal(str, int, str, str)   # op_id, exit_code, stdout, stderr
    prelogout_done = Signal(bool, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.profile_name = None

        # 1. Streaming process for interactive commands (event-loop async)
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self._handle_stdout)
        self.process.readyReadStandardError.connect(self._handle_stderr)
        self.process.finished.connect(self._handle_finished)
        self.process.errorOccurred.connect(self._handle_error)

        # 2. Dedicated worker thread for bounded blocking calls
        self._thread = QThread(self)
        self._thread.setObjectName("TailscaleExecutorWorker")
        self._worker = _BlockingWorker()
        self._worker.moveToThread(self._thread)
        self._worker.status_ready.connect(self.status_ready)
        self._worker.cli_done.connect(self.cli_finished)
        self._worker.prelogout_done.connect(self.prelogout_done)
        self._thread.start()

    # ---- streaming commands (QProcess, never blocks the GUI thread) ----

    def run_command(self, cmd_args, profile_name=None):
        """Starts a streaming tailscale command, replacing any previous one."""
        try:
            if self.process.state() != QProcess.NotRunning:
                self.process.terminate()
                if not self.process.waitForFinished(1000):
                    self.process.kill()
        except (RuntimeError, AttributeError):
            return

        self.profile_name = profile_name
        self.process.start(get_tailscale_path(), list(cmd_args))

    def cancel(self):
        """Terminates the active streaming command (SSO timeout, logout, ...)."""
        try:
            if self.process.state() != QProcess.NotRunning:
                self.process.terminate()
                if not self.process.waitForFinished(500):
                    self.process.kill()
        except (RuntimeError, AttributeError):
            return

    def cleanup(self):
        """Full shutdown: stop the streaming process and retire the worker thread."""
        self.cancel()
        self._thread.quit()
        if not self._thread.wait(5000):
            # A bounded blocking call (worst case: netcheck, 30s) is still in
            # flight; force-stop the worker so app exit cannot hang or crash.
            self._thread.terminate()
            self._thread.wait(1000)

    def _extract_auth_url(self, text: str) -> "str | None":
        """Deterministically extracts and validates an authentication/registration URL without regex."""
        import urllib.parse
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            for token in line.split():
                clean = token.strip(" \t\r\n'\"()[]<>,;")
                clean = clean.rstrip(".")
                if clean.startswith(("https://", "http://")):
                    try:
                        parsed = urllib.parse.urlparse(clean)
                        if parsed.scheme in ("http", "https") and parsed.netloc:
                            path_lower = parsed.path.lower()
                            if any(k in path_lower for k in ("/register", "/a/", "/auth", "mkey:")) or "mkey:" in clean:
                                return clean
                            line_lower = line.lower()
                            if "authenticate" in line_lower or "visit:" in line_lower:
                                return clean
                    except ValueError:
                        continue
        return None

    def _handle_stdout(self):
        data = self.process.readAllStandardOutput().data().decode(errors="ignore").strip()
        if not data:
            return
        self.output_received.emit(data)

        if self.profile_name:
            from ..utils.logger import write_profile_log
            write_profile_log(self.profile_name, data)

        url = self._extract_auth_url(data)
        if url:
            self.sso_url_found.emit(url)

    def _handle_stderr(self):
        data = self.process.readAllStandardError().data().decode(errors="ignore").strip()
        if not data:
            return
        url = self._extract_auth_url(data)
        if url:
            self.sso_url_found.emit(url)
            return  # Do NOT emit as a critical error

        # Actionable diagnostics for Headscale pre-auth key expiration
        data_lower = data.lower()
        if "invalid auth key" in data_lower or "key has expired" in data_lower or "authorization failed" in data_lower:
            p_info = f" for profile '{self.profile_name}'" if self.profile_name else ""
            data = f"Authentication Failed{p_info}: Headscale Auth Key is expired or invalid. Please update the key in the profile settings.\n\nDetails: {data}"

        self.error_received.emit(data)

    def _handle_finished(self, exit_code, exit_status):
        self.finished.emit(exit_code, str(exit_status))

    def _handle_error(self, error):
        if error == QProcess.FailedToStart:
            msg = "Tailscale is not installed on this system or is not found in your system's PATH. Please install Tailscale."
            self.error_received.emit(msg)
            self.finished.emit(-1, "FailedToStart")

    # ---- bounded blocking requests (run on the worker thread) ----

    def request_status(self, use_local_api=True):
        self._worker._request_status.emit(bool(use_local_api))

    def request_cli(self, op_id, args, timeout=10):
        self._worker._request_cli.emit(str(op_id), list(args), int(timeout))

    def request_prelogout(self, connect_args):
        self._worker._request_prelogout.emit(dict(connect_args))

    # ---- bounded synchronous helpers (app shutdown ONLY) ----
    # These run on the caller's thread by design: the close/quit path must get
    # an answer before the event loop dies. The hard timeout is what the old
    # code was missing — a wedged daemon can no longer make the app un-closeable.

    def status_sync(self, timeout=4):
        try:
            result = subprocess.run(
                [get_tailscale_path(), "status", "--json"],
                capture_output=True, text=True, timeout=timeout, check=False, shell=False, **_popen_kwargs()
            )
            data = json.loads(result.stdout)
            state = data.get("BackendState")
            is_connected = (state != "NeedsLogin" and state != "Stopped" and state != "NoState")
            return is_connected, state
        except (subprocess.SubprocessError, OSError, ValueError):
            return False, "Error"

    def logout_sync(self, timeout=5):
        try:
            subprocess.run(
                [get_tailscale_path(), "logout"],
                capture_output=True, timeout=timeout, check=False, shell=False, **_popen_kwargs()
            )
        except (subprocess.SubprocessError, OSError):
            # Service may already be logged out or stopped
            return
