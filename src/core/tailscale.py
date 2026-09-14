# src/core/tailscale.py
"""TailscaleManager: pure execution facade over TailscaleExecutor.

It owns NO connection state, NO retry timers, and NO SSO timers — those live
in ConnectionStateMachine (state_coordinator.py), and all I/O lives in
TailscaleExecutor (executor.py). One state machine, one execution seam
(Candidates 1+2). Public method names are kept from the legacy API so UI
call sites do not change.
"""

import logging
import os
import sys
import webbrowser

from PySide6.QtCore import QObject, QProcess, Signal

from .executor import (  # noqa: F401  (re-exported for UI imports)
    TailscaleExecutor,
    get_tailscale_path,
)

# Child of the app logger configured in main.py so records reach app.log
logger = logging.getLogger("TailscaleClient.Tailscale")


class TailscaleManager(QObject):
    connection_status_changed = Signal(bool, str)  # (is_connected, status_text)
    diagnostic_ready = Signal(str, str)            # (op_id, output_or_error)

    def __init__(self, cache_dir=None, parent=None, executor=None):
        super().__init__(parent)
        self.use_local_api = True
        self.sso_timeout = 120
        self.insecure_ssl = False
        self._last_server = None
        self._status_inflight = False
        self._pending_connect = None

        # executor is injectable so tests can run without a real worker thread
        self.executor = executor if executor is not None else TailscaleExecutor(self)
        # Compat alias: UI code connects ts_manager.worker.error_received
        self.worker = self.executor

        self.executor.status_ready.connect(self._on_status_ready)
        self.executor.cli_finished.connect(self._on_cli_finished)
        self.executor.prelogout_done.connect(self._on_prelogout_done)
        self.executor.sso_url_found.connect(webbrowser.open)

        from .cache_manager import CacheManager
        cache_file = os.path.join(cache_dir, "ts_cache.json") if cache_dir else "ts_cache.json"
        self.cache = CacheManager(cache_file, expiry_seconds=30)

    # ==========================================
    # Status
    # ==========================================

    def check_status(self, force=False):
        """Non-blocking status query. Answers immediately from cache (emitting
        the cached value to listeners); a fresh fetch always runs on the
        executor's worker thread and arrives via connection_status_changed."""
        cached = self.cache.get("status")
        if not force and cached:
            self.connection_status_changed.emit(cached["connected"], cached["text"])
            return cached["connected"], cached["text"]

        if not self._status_inflight:
            self._status_inflight = True
            self.executor.request_status(self.use_local_api)

        if cached:
            return cached["connected"], cached["text"]
        return False, "Checking..."

    def _on_status_ready(self, payload):
        self._status_inflight = False
        self.cache.set("status", payload)
        self.connection_status_changed.emit(payload["connected"], payload["text"])

    def check_status_sync(self, timeout=4):
        """Bounded synchronous check — app shutdown paths only."""
        return self.executor.status_sync(timeout)

    # ==========================================
    # Connect / disconnect
    # ==========================================

    def connect(self, login_server, auth_key=None, use_sso=False, profile_name=None, exit_node=None, routes=None,
                ssh=False, accept_dns=False, allow_lan=False, disable_snat=False, hostname="", force_reset=False,
                advertise_exit_node=False, shields_up=False, force_reauth=False, advertise_tags="", accept_routes=True,
                unattended=False, webclient=False, advertise_connector=False, accept_risk="", extra_args=""):
        """Legacy kwargs API kept for UI call sites; folds into connect_args()."""
        self.connect_args({
            "login_server": login_server,
            "auth_key": auth_key,
            "use_sso": use_sso,
            "profile_name": profile_name,
            "exit_node": exit_node,
            "routes": routes,
            "ssh": ssh,
            "accept_dns": accept_dns,
            "allow_lan": allow_lan,
            "disable_snat": disable_snat,
            "hostname": hostname,
            "force_reset": force_reset,
            "advertise_exit_node": advertise_exit_node,
            "shields_up": shields_up,
            "force_reauth": force_reauth,
            "advertise_tags": advertise_tags,
            "accept_routes": accept_routes,
            "unattended": unattended,
            "webclient": webclient,
            "advertise_connector": advertise_connector,
            "accept_risk": accept_risk,
            "extra_args": extra_args,
        })

    def connect_args(self, connect_args: dict):
        """Single entry point for starting a connection. The retry/reconnect
        policy is owned by ConnectionStateMachine — this method only executes."""
        self.start_service()
        self.cache.clear()

        last_server = self._last_server
        server = connect_args.get("login_server")
        if last_server and server and last_server.strip() != server.strip():
            # Server switch: logout from the old control plane first (on the
            # worker thread) so the old machine key cannot conflict with the
            # new Headscale registration. 'up' starts when the logout returns.
            self._pending_connect = dict(connect_args)
            self.executor.request_prelogout(connect_args)
            return

        self._launch_up(connect_args)

    def _on_prelogout_done(self, ok, connect_args):
        # Proceed even if the logout failed (best effort) — the up command
        # will surface any registration conflict as an actionable error.
        if (self._pending_connect is not None
                and self._pending_connect.get("login_server") == connect_args.get("login_server")):
            self._pending_connect = None
        self._launch_up(connect_args)

    def _launch_up(self, connect_args):
        args = self._build_up_args(connect_args)
        self._last_server = connect_args.get("login_server")
        self.executor.run_command(args, connect_args.get("profile_name"))

    def switch_profile(self, native_profile_name, profile_name=None):
        """Instantly switch to a native Tailscale profile."""
        self.cache.clear()
        self.executor.run_command(["switch", native_profile_name], profile_name)

    def logout(self, profile_name=None):
        self.cache.clear()
        self.executor.cancel()
        self.executor.run_command(["logout"], profile_name)

    def logout_sync(self, timeout=5):
        """Bounded synchronous logout — app shutdown paths only."""
        self.cache.clear()
        self.executor.logout_sync(timeout)

    # ==========================================
    # Diagnostics (async via executor worker thread)
    # ==========================================

    def request_netcheck(self):
        self.executor.request_cli("netcheck", ["netcheck"], timeout=30)

    def request_version(self):
        self.executor.request_cli("version", ["version"], timeout=8)

    def request_ping(self, target):
        self.executor.request_cli(f"ping:{target}", ["ping", "--timeout", "2s", target], timeout=6)

    def _on_cli_finished(self, op_id, exit_code, stdout, stderr):
        text = stdout.strip()
        if exit_code != 0 and stderr.strip():
            text = f"{text}\n{stderr.strip()}".strip()
        self.diagnostic_ready.emit(op_id, text)

    # ==========================================
    # Helpers
    # ==========================================

    def start_service(self):
        """Try to start Tailscale service if not running (detached, non-blocking)."""
        if sys.platform == "win32":
            QProcess.startDetached("net", ["start", "Tailscale"])
        elif sys.platform.startswith("linux"):
            QProcess.startDetached("systemctl", ["start", "tailscaled"])
        elif sys.platform == "darwin":
            QProcess.startDetached("launchctl", ["start", "com.tailscale.tailscaled"])

    def cleanup(self):
        """Cleanly terminate the executor (streaming process + worker thread)."""
        self.executor.cleanup()

    def get_stats(self):
        """Get psutil stats for the Tailscale interface (fast, GUI-thread safe)."""
        import psutil
        try:
            stats = psutil.net_io_counters(pernic=True)

            cached_status = self.cache.get("status")
            ts_ips = cached_status.get("ips", []) if cached_status else []
            if ts_ips:
                addrs = psutil.net_if_addrs()
                target_iface = None
                for iface, addr_list in addrs.items():
                    for addr in addr_list:
                        if addr.address in ts_ips:
                            target_iface = iface
                            break
                    if target_iface:
                        break

                if target_iface and target_iface in stats:
                    return stats[target_iface]

            for iface, data in stats.items():
                if "tailscale" in iface.lower():
                    return data
        except (KeyError, OSError, psutil.Error):
            return None
        return None

    def _build_up_args(self, connect_args):
        """Construct a complete, unambiguous argument list for 'tailscale up' with explicit true/false values."""
        import shlex
        login_server = connect_args.get("login_server")
        auth_key = connect_args.get("auth_key")
        use_sso = connect_args.get("use_sso")
        exit_node = connect_args.get("exit_node")
        routes = connect_args.get("routes")
        ssh = connect_args.get("ssh", False)
        accept_dns = connect_args.get("accept_dns", False)
        accept_routes = connect_args.get("accept_routes", True)
        allow_lan = connect_args.get("allow_lan", False)
        disable_snat = connect_args.get("disable_snat", False)
        hostname = connect_args.get("hostname", "")
        force_reset = connect_args.get("force_reset", False)
        advertise_exit_node = connect_args.get("advertise_exit_node", False)
        shields_up = connect_args.get("shields_up", False)
        force_reauth = connect_args.get("force_reauth", False)
        advertise_tags = connect_args.get("advertise_tags", "")
        unattended = connect_args.get("unattended", False)
        webclient = connect_args.get("webclient", False)
        advertise_connector = connect_args.get("advertise_connector", False)
        accept_risk = connect_args.get("accept_risk", "")
        extra_args = connect_args.get("extra_args", "")

        args = ["up", f"--login-server={login_server}"]

        if not use_sso and auth_key:
            args.append(f"--auth-key={auth_key}")

        # Explicit tri-state / boolean flags to guarantee toggling works predictably
        args.append(f"--accept-routes={'true' if accept_routes else 'false'}")
        args.append(f"--accept-dns={'true' if accept_dns else 'false'}")
        args.append(f"--shields-up={'true' if shields_up else 'false'}")
        args.append(f"--ssh={'true' if ssh else 'false'}")
        args.append(f"--advertise-exit-node={'true' if advertise_exit_node else 'false'}")

        if force_reset:
            args.append("--reset")
        if force_reauth:
            args.append("--force-reauth")
        if advertise_tags:
            args.append(f"--advertise-tags={advertise_tags}")
        if getattr(self, "insecure_ssl", False):
            args.append("--insecure-skip-tls-verify=true")

        if unattended and sys.platform == "win32":
            args.append(f"--unattended={'true' if unattended else 'false'}")
        if webclient:
            args.append(f"--webclient={'true' if webclient else 'false'}")
        if advertise_connector:
            args.append(f"--advertise-connector={'true' if advertise_connector else 'false'}")

        if accept_risk and accept_risk.lower() != "none":
            args.append(f"--accept-risk={accept_risk}")

        if hostname:
            args.append(f"--hostname={hostname}")

        if exit_node:
            args.append(f"--exit-node={exit_node}")
            args.append(f"--exit-node-allow-lan-access={'true' if allow_lan else 'false'}")

        if routes:
            args.append(f"--advertise-routes={routes}")
            if disable_snat:
                args.append("--snat-subnet-routes=false")

        if extra_args:
            try:
                args.extend(shlex.split(extra_args))
            except ValueError as e:
                logger.error(f"Error parsing extra flags '{extra_args}': {e}")

        return args
