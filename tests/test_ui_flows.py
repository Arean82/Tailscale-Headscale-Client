"""UI flow coverage for the dashboard: the connect/disconnect toggle, profile
switching, credential editing and the key-expiry badge.

DashboardView is a plain widget (unlike MainWindow, which cannot be built
headless), so these tests drive the real class with a stub coordinator and
assert on observable behaviour: coordinator calls, button state, labels.
"""

import os
import sys
import unittest
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])

#: Stands in for a pre-auth key. Not credential-shaped on purpose: a tskey-auth-…
#: literal in the tree trips GitHub secret scanning, and the UI passes this value
#: straight through to the coordinator, which is faked here anyway.
PRE_AUTH_VALUE = "fixture-pre-auth-value"

from src.core.models import AppSettings, Profile
from src.ui.dashboard import DashboardView


class FakeDb:
    def __init__(self):
        self.flushed = 0

    def flush_buffer(self):
        self.flushed += 1

    def get_daily_total(self, profile, date=None):
        return 0, 0

    def get_daily_history(self, profile, days=10):
        return []


class FakeCoordinator(QObject):
    """Stands in for StateCoordinator: records the calls the UI makes."""

    connection_status_changed = Signal(bool, str)

    def __init__(self, cached_status=None, any_connected=False):
        super().__init__()
        self.calls = []
        self.cached_status = cached_status
        self.any_connected = any_connected
        self.cache = SimpleNamespace(get=lambda key: self.cached_status)

    def connect_vpn(self, **kwargs):
        self.calls.append(("connect_vpn", kwargs))

    def logout(self, profile_name=None):
        self.calls.append(("logout", profile_name))

    def switch_profile(self, native_profile, profile_name=None):
        self.calls.append(("switch_profile", native_profile, profile_name))

    def check_status(self, force=False):
        return False, "Disconnected"

    def check_status_sync(self, timeout=4):
        return self.any_connected, "Running" if self.any_connected else "Stopped"

    def get_stats(self):
        return None


def make_view(profile=None, settings=None, cached_status=None, any_connected=False):
    settings = settings or AppSettings()
    manager = SimpleNamespace(db=FakeDb(), settings=settings, profiles={}, save_profiles=lambda: None)
    if profile:
        manager.profiles[profile.name] = profile
    coordinator = FakeCoordinator(cached_status=cached_status, any_connected=any_connected)
    view = DashboardView(manager, coordinator, profile=profile)
    return view, coordinator, manager


class TestConnectionToggle(unittest.TestCase):
    """The flow a Headscale user hits first."""

    def test_import_time_application_is_still_alive(self):
        """DashboardView can only be built while the shared QApplication lives."""
        self.assertIs(QApplication.instance(), _app)

    def test_disconnected_click_connects_with_the_profile_credentials(self):
        profile = Profile(name="HQ", login_server="https://hs.example.com", auth_key=PRE_AUTH_VALUE)
        view, coordinator, _ = make_view(profile)
        view.update_status(False, "Disconnected")

        view.toggle_connection()

        self.assertEqual([c[0] for c in coordinator.calls], ["connect_vpn"])
        kwargs = coordinator.calls[0][1]
        self.assertEqual(kwargs["login_server"], "https://hs.example.com")
        self.assertEqual(kwargs["auth_key"], PRE_AUTH_VALUE)
        self.assertEqual(kwargs["profile_name"], "HQ")
        self.assertFalse(kwargs["use_sso"])

    def test_click_while_connected_logs_out(self):
        profile = Profile(name="HQ", login_server="https://hs.example.com")
        view, coordinator, _ = make_view(profile)
        view.update_status(True, "Connected")
        self.assertEqual(view.btnVpnAction.text(), "Logout")

        view.toggle_connection()

        self.assertEqual(coordinator.calls, [("logout", "HQ")])

    def test_switch_to_another_session_prompts_before_connecting(self):
        """Switching away from an active session must ask first, and honour 'No'."""
        from PySide6.QtWidgets import QMessageBox

        profile = Profile(name="HQ", login_server="https://hs.example.com")
        view, coordinator, _ = make_view(profile, any_connected=True)
        view.update_status(False, "Disconnected")

        with patch.object(QMessageBox, "question", return_value=QMessageBox.No) as prompt:
            view.toggle_connection()

        prompt.assert_called_once()
        self.assertEqual(coordinator.calls, [], "connected after the user declined")

        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            view.toggle_connection()
        self.assertEqual([c[0] for c in coordinator.calls], ["connect_vpn"])

    def test_sso_profile_connects_without_a_key(self):
        profile = Profile(name="HQ", login_server="https://hs.example.com", auth_mode="google")
        view, coordinator, _ = make_view(profile)
        view.update_status(False, "Disconnected")

        view.toggle_connection()

        kwargs = coordinator.calls[0][1]
        self.assertTrue(kwargs["use_sso"])

    def test_advanced_flags_only_travel_when_the_feature_is_enabled(self):
        profile = Profile(name="HQ", login_server="https://hs.example.com", exit_node="exit-1",
                          routes="10.0.0.0/24", enable_ssh=True)

        view, coordinator, _ = make_view(profile, settings=AppSettings(advanced_features=False))
        view.update_status(False, "Disconnected")
        view.toggle_connection()
        plain = coordinator.calls[0][1]
        self.assertEqual(plain["exit_node"], "")
        self.assertEqual(plain["routes"], "")
        self.assertFalse(plain["ssh"])

        view, coordinator, _ = make_view(profile, settings=AppSettings(advanced_features=True))
        view.update_status(False, "Disconnected")
        view.toggle_connection()
        advanced = coordinator.calls[0][1]
        self.assertEqual(advanced["exit_node"], "exit-1")
        self.assertEqual(advanced["routes"], "10.0.0.0/24")
        self.assertTrue(advanced["ssh"])

    def test_native_profile_switches_instead_of_connecting(self):
        profile = Profile(name="HQ", login_server="https://hs.example.com", native_profile="corp")
        view, coordinator, _ = make_view(profile, settings=AppSettings(advanced_features=True))
        view.update_status(False, "Disconnected")

        view.toggle_connection()

        self.assertEqual(coordinator.calls[0][0], "switch_profile")
        self.assertEqual(coordinator.calls[0][1], "corp")
        self.assertEqual(coordinator.calls[0][2], "HQ")


class TestStatusRendering(unittest.TestCase):
    def test_connected_state(self):
        view, _, _ = make_view(Profile(name="HQ"))
        view.update_status(True, "Connected")
        self.assertEqual(view.labelStatus.text(), "🟢 Connected")
        self.assertEqual(view.btnVpnAction.text(), "Logout")
        self.assertTrue(view.btnVpnAction.isEnabled())

    def test_pending_approval_disables_connecting(self):
        view, _, _ = make_view(Profile(name="HQ"))
        view.update_status(False, "Pending Admin Approval")
        self.assertIn("Pending Admin Approval", view.labelStatus.text())
        self.assertFalse(view.btnVpnAction.isEnabled())
        self.assertEqual(view.btnVpnAction.text(), "Awaiting Approval...")

    def test_checking_does_not_downgrade_a_connected_tab(self):
        view, _, _ = make_view(Profile(name="HQ"))
        view.update_status(True, "Connected")
        view.update_status(False, "Checking...")
        self.assertEqual(view.labelStatus.text(), "🟢 Connected")

    def test_disconnected_state_allows_connecting(self):
        view, _, _ = make_view(Profile(name="HQ"))
        view.update_status(False, "Disconnected")
        self.assertEqual(view.btnVpnAction.text(), "Connect")
        self.assertTrue(view.btnVpnAction.isEnabled())


class TestKeyExpiryBadge(unittest.TestCase):
    """The badge logic that used to be debug-print territory."""

    def _status(self, expiry):
        return {"connected": True, "text": "Connected", "ips": ["100.64.0.1"],
                "raw_data": {"Self": {"KeyExpiry": expiry}}}

    def _badge(self, expiry):
        view, _, _ = make_view(Profile(name="HQ"), cached_status=self._status(expiry))
        view.update_status(True, "Connected")
        return view.labelExpiry.text()

    def _expiry_in(self, days):
        """A timestamp `days` from now, with a half-day margin so delta.days
        (which truncates) is exactly the requested number."""
        return (datetime.now(UTC) + timedelta(days=days, hours=12)).isoformat()

    def test_expired_key(self):
        self.assertIn("Expired", self._badge((datetime.now(UTC) - timedelta(days=2)).isoformat()))

    def test_expiring_soon_is_flagged_red(self):
        self.assertIn("Expires in 5 days", self._badge(self._expiry_in(5)))

    def test_medium_term_key_is_flagged_amber(self):
        text = self._badge(self._expiry_in(12))
        self.assertIn("Core Auth Session", text)
        self.assertIn("Expires in 12 days", text)

    def test_healthy_key_reports_remaining_days(self):
        text = self._badge(self._expiry_in(45))
        self.assertIn("Key Active", text)
        self.assertIn("45 days", text)

    def test_missing_or_malformed_expiry_clears_the_badge(self):
        self.assertEqual(self._badge(""), "")
        self.assertEqual(self._badge("not-a-timestamp"), "")

    def test_badge_clears_when_disconnected(self):
        view, _, _ = make_view(Profile(name="HQ"),
                               cached_status=self._status((datetime.now(UTC) + timedelta(days=9)).isoformat()))
        view.update_status(True, "Connected")
        self.assertTrue(view.labelExpiry.text())
        view.update_status(False, "Disconnected")
        self.assertEqual(view.labelExpiry.text(), "")


class TestCredentialEditing(unittest.TestCase):
    def test_edited_credentials_and_fallback_ip_are_persisted(self):
        """Regression: the fallback IP used to be silently discarded on save."""
        profile = Profile(name="HQ", login_server="https://old.example.com", auth_key="old-key")
        view, _, manager = make_view(profile)
        saved = []
        manager.save_profiles = lambda: saved.append(True)

        class FakeDialog:
            def __init__(self, *a, **k):
                pass

            def exec(self):
                return 1

            def get_data(self):
                return {
                    "login_server": "https://new.example.com",
                    "auth_key": "new-key",
                    "auth_mode": "auth_key",
                    "enable_dns_fallback": True,
                    "last_known_ip": "192.0.2.10",
                }

        with patch("src.ui.components.profile_dialog.ProfileDialog", FakeDialog):
            view.change_credentials()

        self.assertEqual(profile.login_server, "https://new.example.com")
        self.assertEqual(profile.auth_key, "new-key")
        self.assertTrue(profile.enable_dns_fallback)
        self.assertEqual(profile.last_known_ip, "192.0.2.10")
        self.assertEqual(saved, [True], "changes were not persisted")
        self.assertEqual(view.lineEditUrl.text(), "https://new.example.com")

    def test_cancelled_dialog_changes_nothing(self):
        profile = Profile(name="HQ", login_server="https://old.example.com")
        view, _, manager = make_view(profile)
        saved = []
        manager.save_profiles = lambda: saved.append(True)

        class CancelDialog:
            def __init__(self, *a, **k):
                pass

            def exec(self):
                return 0

        with patch("src.ui.components.profile_dialog.ProfileDialog", CancelDialog):
            view.change_credentials()

        self.assertEqual(profile.login_server, "https://old.example.com")
        self.assertEqual(saved, [])


if __name__ == "__main__":
    unittest.main()


class TestProfileDialogValidation(unittest.TestCase):
    """The accessibility doc claims a URL-format rejection; this pins it."""

    def _dialog(self, url):
        from src.ui.components.profile_dialog import ProfileDialog
        dialog = ProfileDialog(None, None, manager=None)
        if dialog.url_auth:
            dialog.url_auth.setText(url)
        return dialog

    def test_http_and_https_urls_are_accepted(self):
        for url in ("https://headscale.company.com", "http://10.0.0.5:8080"):
            dialog = self._dialog(url)
            data = dialog.get_data()
            self.assertIsNotNone(data, f"{url} was rejected")
            self.assertEqual(data["login_server"], url)
            dialog.deleteLater()

    def test_url_without_scheme_is_rejected_with_guidance(self):
        dialog = self._dialog("headscale.company.com")
        with patch("PySide6.QtWidgets.QMessageBox.warning") as warn:
            data = dialog.get_data()
        self.assertIsNone(data, "a scheme-less URL was accepted")
        warn.assert_called_once()
        self.assertIn("HTTP or HTTPS", warn.call_args[0][2])
        dialog.deleteLater()

    def test_empty_url_is_rejected(self):
        dialog = self._dialog("")
        with patch("PySide6.QtWidgets.QMessageBox.warning") as warn:
            data = dialog.get_data()
        self.assertIsNone(data)
        self.assertIn("required", warn.call_args[0][2])
        dialog.deleteLater()
