# scripts/live_flow_check.py
"""Live mutating-flow verification for the Tailscale/Headscale Client.

Runs the real TailscaleExecutor against the real daemon on this machine and
walks the connect/logout/status lifecycle that headless unit tests cannot
cover. This MUTATES live connection state — run it when a VPN disconnect
for a few minutes is acceptable.

Usage:
    python scripts/live_flow_check.py              # full run (logout -> connect -> logout)
    python scripts/live_flow_check.py --check-only # read-only status/executor sanity check

Requirements:
    - tailscale CLI installed and tailscaled running
    - current status is expected to be "Logged Out" for the connect phase;
      the script logs out first regardless (bounded, best-effort)

Exit codes: 0 = all checks passed, 1 = one or more checks failed.
"""

import argparse
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtCore import QCoreApplication

from src.core.executor import get_tailscale_path
from src.core.tailscale import TailscaleManager

APP: QCoreApplication | None = None
RESULTS: list[tuple[str, bool, str]] = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))
    return ok


def wait_for(predicate, timeout_ms=15000, poll_ms=100, desc="condition"):
    """Runs the Qt event loop until predicate() is truthy or timeout."""
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        if APP is not None:
            APP.processEvents()
        if predicate():
            return True
        time.sleep(poll_ms / 1000)
    if APP is not None:
        APP.processEvents()
    print(f"      (timed out waiting for {desc})")
    return False


def cli_state():
    """Ground truth from the tailscale CLI, independent of the app's executor."""
    import subprocess

    from src.core.executor import _popen_kwargs
    try:
        r = subprocess.run([get_tailscale_path(), "status", "--json"],
                           capture_output=True, text=True, timeout=6, check=False,
                           shell=False, **_popen_kwargs())
        import json
        return json.loads(r.stdout).get("BackendState", "Unknown")
    except (subprocess.SubprocessError, OSError, ValueError) as e:
        return f"cli-error: {e}"


def main():
    global APP  # noqa: PLW0603 (single QApplication handle for the wait_for helper)
    APP = QCoreApplication.instance() or QCoreApplication(sys.argv)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true",
                        help="Read-only executor sanity checks; no connect/logout.")
    parser.add_argument("--login-server", default=os.environ.get("TS_TEST_LOGIN_SERVER", ""),
                        help="Login server for the connect phase ( Headscale URL or default SaaS).")
    parser.add_argument("--sso", action="store_true",
                        help="Use SSO flow for connect (opens browser).")
    args = parser.parse_args()

    if not shutil.which("tailscale") and not os.path.exists(get_tailscale_path()):
        print("FATAL: tailscale CLI not found on this machine.")
        return 1

    print(f"tailscale CLI: {get_tailscale_path()}")
    print(f"CLI ground truth before start: BackendState={cli_state()}\n")

    tmp = tempfile.mkdtemp(prefix="live_flow_")
    status_events = []
    diag_events = []
    finished_events = []

    manager = TailscaleManager(cache_dir=tmp)
    manager.connection_status_changed.connect(lambda c, t: status_events.append((c, t)))
    manager.diagnostic_ready.connect(lambda op, text: diag_events.append((op, text)))
    manager.executor.finished.connect(lambda code, st: finished_events.append((code, st)))

    failures = 0

    # ---- Check 1: async status via executor (read-only) ----
    print("== 1. Async status query (worker thread, LocalAPI -> CLI fallback) ==")
    manager.check_status()
    got_status = wait_for(lambda: any(t != "Checking..." for _, t in status_events),
                          desc="first status payload")
    cur_text = next((t for _, t in reversed(status_events) if t != "Checking..."), None)
    failures += 0 if check("executor produced a status payload", got_status and cur_text is not None,
                           f"text={cur_text!r}") else 1
    cli = cli_state()
    agree = cur_text is not None and (
        (cli == "Running" and cur_text == "Connected")
        or (cli == "NeedsLogin" and cur_text == "Logged Out")
        or (cli == "NeedsMachineAuth" and cur_text == "Pending Admin Approval"))
    failures += 0 if check("app status agrees with CLI ground truth", agree,
                           f"app={cur_text!r} cli={cli!r}") else 1

    # ---- Check 2: bounded version query (read-only) ----
    print("== 2. Bounded CLI diagnostic (version) ==")
    manager.request_version()
    got_ver = wait_for(lambda: any(op == "version" for op, _ in diag_events), desc="version result")
    ver = next((t for op, t in reversed(diag_events) if op == "version"), "")
    failures += 0 if check("version via executor", got_ver and ver.strip() != "", ver.strip().splitlines()[:1]) else 1

    # ---- Check 3: cache shape used by peer dialog / tray ----
    cached = manager.cache.get("status")
    failures += 0 if check("status cache populated with raw_data/ips for UI consumers",
                           bool(cached) and "raw_data" in cached and "ips" in cached) else 1

    if args.check_only:
        print()
        manager.cleanup()
        shutil.rmtree(tmp, ignore_errors=True)
        return summarize(failures)

    # ---- Check 4: bounded sync logout (mutating) ----
    print("== 4. Bounded synchronous logout ==")
    t0 = time.monotonic()
    manager.logout_sync(timeout=5)
    dt = time.monotonic() - t0
    failures += 0 if check("logout_sync returned within its timeout", dt < 6.0, f"{dt:.2f}s") else 1
    cli = cli_state()
    failures += 0 if check("CLI confirms logged out after logout_sync",
                           cli in ("NeedsLogin", "Stopped", "NoState"), f"cli={cli!r}") else 1

    # ---- Check 5: connect (mutating; auth-key or SSO) ----
    print("== 5. Connect via executor streaming command ==")
    status_events.clear()
    if args.sso:
        print("   SSO mode: a browser window will open; complete the login there.")
        manager.connect(login_server=args.login_server or "https://controlplane.tailscale.com",
                        use_sso=True, profile_name="live-flow-check")
    else:
        key = os.environ.get("TS_TEST_AUTH_KEY", "")
        if not key:
            print("   NOTE: TS_TEST_AUTH_KEY not set; connecting without a key "
                  "(daemon will surface its own auth flow or fail — still a valid executor test).")
        manager.connect(login_server=args.login_server or "https://controlplane.tailscale.com",
                        auth_key=key, use_sso=False, profile_name="live-flow-check")

    connected = wait_for(
        lambda: any(t == "Connected" for _, t in status_events), timeout_ms=30000, desc="'Connected' status")
    cli = cli_state()
    failures += 0 if check("app reached Connected", connected) else 1
    failures += 0 if check("CLI BackendState=Running after connect", cli == "Running", f"cli={cli!r}") else 1

    # ---- Check 6: streaming command lifecycle observed ----
    ups = list(finished_events)
    failures += 0 if check("streaming command(s) reported completion", len(ups) >= 1,
                           f"{len(ups)} finished event(s)") else 1

    # ---- Check 7: final cleanup logout ----
    print("== 7. Cleanup logout ==")
    status_events.clear()
    manager.logout()
    logged_out = wait_for(lambda: any(t == "Logged Out" for _, t in status_events)
                          or cli_state() in ("NeedsLogin", "Stopped"), timeout_ms=15000,
                          desc="logged out")
    failures += 0 if check("streaming logout restored Logged Out", logged_out,
                           f"cli={cli_state()!r}") else 1

    print()
    manager.cleanup()
    shutil.rmtree(tmp, ignore_errors=True)
    return summarize(failures)


def summarize(failures):
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print("=" * 60)
    print(f"RESULT: {passed}/{total} checks passed, {failures} failure group(s)")
    for name, ok, detail in RESULTS:
        if not ok:
            print(f"  FAILED: {name}" + (f" — {detail}" if detail else ""))
    print("=" * 60)
    return 0 if failures == 0 and passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
