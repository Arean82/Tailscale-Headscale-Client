import os
import shutil
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtCore import QCoreApplication, QObject, Signal

if QCoreApplication.instance() is None:
    QCoreApplication([])


class FakeExecutor(QObject):
    """Headless stand-in for TailscaleExecutor: records every request so tests
    can assert exactly one command, one retry, one prelogout, etc."""

    output_received = Signal(str)
    error_received = Signal(str)
    sso_url_found = Signal(str)
    finished = Signal(int, str)
    status_ready = Signal(dict)
    cli_finished = Signal(str, int, str, str)
    prelogout_done = Signal(bool, dict)

    def __init__(self):
        super().__init__()
        self.commands = []
        self.prelogout_requests = []
        self.status_requests = []
        self.cli_requests = []
        self.messages = []
        self.error_received.connect(self.messages.append)

    def run_command(self, cmd_args, profile_name=None):
        self.commands.append((list(cmd_args), profile_name))

    def cancel(self):
        self.commands.append(("CANCEL", None))

    def cleanup(self):
        self.commands.append(("CLEANUP", None))

    def request_status(self, use_local_api=True):
        self.status_requests.append(bool(use_local_api))

    def request_cli(self, op_id, args, timeout=10):
        self.cli_requests.append((op_id, list(args), timeout))

    def request_prelogout(self, connect_args):
        self.prelogout_requests.append(dict(connect_args))

    def status_sync(self, timeout=4):
        return False, "Stopped"

    def logout_sync(self, timeout=5):
        pass


class FakeManagerForStateMachine:
    """Minimal ts_manager stand-in for ConnectionStateMachine tests."""

    def __init__(self):
        self.worker = FakeExecutor()
        self.connect_calls = []

    def connect_args(self, connect_args):
        self.connect_calls.append(dict(connect_args))


class StubCoordinator:
    def __init__(self, ts_manager):
        self.ts_manager = ts_manager
        self.manager = SimpleNamespace(settings=SimpleNamespace(sso_timeout=120))


_created_managers = []


def make_manager(executor=None):
    from src.core.tailscale import TailscaleManager
    tmp = tempfile.mkdtemp()
    mgr = TailscaleManager(cache_dir=tmp, executor=executor)
    mgr._tmp = tmp
    _created_managers.append(mgr)
    return mgr


def tearDownModule():
    """connect_args() stages the auth key in a temp file; drop any that a test
    left staged (and their temp dirs) so the suite does not litter %TEMP%."""
    for mgr in _created_managers:
        mgr._clear_auth_key_file()
        if getattr(mgr, "_tmp", None):
            shutil.rmtree(mgr._tmp, ignore_errors=True)
    _created_managers.clear()


class TestSingleRetryPolicy(unittest.TestCase):
    """Candidate 2: the state machine is the ONE retry/backoff owner."""

    def make_machine(self):
        from src.core.state_coordinator import ConnectionStateMachine
        ts = FakeManagerForStateMachine()
        coordinator = StubCoordinator(ts)
        machine = ConnectionStateMachine(coordinator, ts)
        machine.last_connect_args = {"login_server": "https://hs.example.com", "auth_key": "k"}
        return ts, machine

    def test_backoff_schedule(self):
        from src.core.state_coordinator import ConnectionStateMachine
        self.assertEqual(ConnectionStateMachine._retry_delay_ms(1), 3000)
        self.assertEqual(ConnectionStateMachine._retry_delay_ms(2), 6000)
        self.assertEqual(ConnectionStateMachine._retry_delay_ms(3), 12000)

    def test_failure_while_connecting_schedules_exactly_one_retry(self):
        from src.core.models import AppState
        ts, machine = self.make_machine()
        machine.transition_to(AppState.CONNECTING, force=True)
        machine.on_command_finished(1)                      # up failed
        self.assertEqual(machine.state, AppState.ERROR)
        self.assertTrue(machine.reconnect_timer.isActive())
        self.assertEqual(len(ts.connect_calls), 0)          # no immediate re-fire

        machine._on_reconnect_timer_fired()                 # timer fires once
        self.assertEqual(len(ts.connect_calls), 1)
        self.assertIn("https://hs.example.com", ts.connect_calls[0]["login_server"])
        self.assertEqual(machine.state, AppState.CONNECTING)

    def test_success_while_connecting_does_not_retry(self):
        from src.core.models import AppState
        ts, machine = self.make_machine()
        machine.transition_to(AppState.CONNECTING, force=True)
        machine.on_command_finished(0)                      # up succeeded
        self.assertEqual(machine.state, AppState.CONNECTING)
        self.assertFalse(machine.reconnect_timer.isActive())
        self.assertEqual(len(ts.connect_calls), 0)

    def test_failure_outside_connecting_does_not_retry(self):
        from src.core.models import AppState
        ts, machine = self.make_machine()
        machine.transition_to(AppState.DISCONNECTED, force=True)
        machine.on_command_finished(1)                      # e.g. logout failed
        self.assertEqual(machine.state, AppState.DISCONNECTED)
        self.assertFalse(machine.reconnect_timer.isActive())
        self.assertEqual(len(ts.connect_calls), 0)

    def test_retries_capped_at_three(self):
        from src.core.models import AppState
        ts, machine = self.make_machine()
        machine.transition_to(AppState.CONNECTING, force=True)
        for _ in range(3):
            machine.on_command_finished(1)
            machine._on_reconnect_timer_fired()
        self.assertEqual(len(ts.connect_calls), 3)

        machine.on_command_finished(1)                      # 4th failure
        self.assertFalse(machine.reconnect_timer.isActive())  # no more retries
        self.assertEqual(len(ts.connect_calls), 3)
        self.assertTrue(any("Maximum reconnection attempts" in m for m in ts.worker.messages))


class TestExecutorFacade(unittest.TestCase):
    """Candidate 1: TailscaleManager delegates all I/O to the injected seam."""

    def test_same_server_connect_runs_up_directly(self):
        ex = FakeExecutor()
        mgr = make_manager(executor=ex)
        with patch.object(type(mgr), "start_service", lambda self: None):
            mgr.connect_args({"login_server": "https://hs.example.com", "auth_key": "k1"})
        self.assertEqual(len(ex.commands), 1)
        self.assertEqual(ex.commands[0][0][0], "up")
        self.assertIn("--login-server=https://hs.example.com", ex.commands[0][0])
        self.assertEqual(ex.prelogout_requests, [])

    def test_server_switch_prelogouts_before_up(self):
        ex = FakeExecutor()
        mgr = make_manager(executor=ex)
        with patch.object(type(mgr), "start_service", lambda self: None):
            mgr.connect_args({"login_server": "https://a.example.com", "auth_key": "k1"})
        ex.commands.clear()

        # Different server: up must be deferred until prelogout completes
        with patch.object(type(mgr), "start_service", lambda self: None):
            mgr.connect_args({"login_server": "https://b.example.com", "auth_key": "k2"})
        self.assertEqual(len(ex.prelogout_requests), 1)
        self.assertEqual(ex.commands, [])

        ex.prelogout_done.emit(True, {"login_server": "https://b.example.com", "auth_key": "k2"})
        self.assertEqual(len(ex.commands), 1)
        self.assertIn("--login-server=https://b.example.com", ex.commands[0][0])

    def test_failed_prelogout_still_proceeds(self):
        ex = FakeExecutor()
        mgr = make_manager(executor=ex)
        with patch.object(type(mgr), "start_service", lambda self: None):
            mgr.connect_args({"login_server": "https://a.example.com"})
        ex.commands.clear()
        with patch.object(type(mgr), "start_service", lambda self: None):
            mgr.connect_args({"login_server": "https://b.example.com"})
        ex.prelogout_done.emit(False, {"login_server": "https://b.example.com"})
        self.assertEqual(len(ex.commands), 1)

    def test_status_request_debounced_and_cache_emitted(self):
        ex = FakeExecutor()
        mgr = make_manager(executor=ex)
        got = []

        mgr.connection_status_changed.connect(lambda c, t: got.append((c, t)))

        # Empty cache: fire one worker request, report "Checking..."
        connected, text = mgr.check_status()
        self.assertEqual((connected, text), (False, "Checking..."))
        self.assertEqual(len(ex.status_requests), 1)

        # In-flight: second call must NOT spawn another request
        mgr.check_status()
        self.assertEqual(len(ex.status_requests), 1)

        # Fresh payload arrives -> cached and emitted
        ex.status_ready.emit({"connected": True, "text": "Connected", "ips": ["100.64.0.1"], "raw_data": {}})
        cached = mgr.cache.get("status")
        self.assertEqual(cached["connected"], True)
        self.assertIn((True, "Connected"), got)

        # Cache hit: served from cache, no new request
        ex.status_requests.clear()
        connected, text = mgr.check_status()
        self.assertEqual((connected, text), (True, "Connected"))
        self.assertEqual(len(ex.status_requests), 0)

    def test_request_ping_routes_to_executor(self):
        ex = FakeExecutor()
        mgr = make_manager(executor=ex)
        mgr.request_ping("100.64.0.5")
        self.assertEqual(len(ex.cli_requests), 1)
        self.assertEqual(ex.cli_requests[0][0], "ping:100.64.0.5")


if __name__ == "__main__":
    unittest.main()
