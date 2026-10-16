import os
import tempfile
import unittest

from src.utils.dns_fallback import _edit_hosts, is_admin, run_cli_if_requested


class TestDnsFallback(unittest.TestCase):
    def setUp(self):
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, encoding="utf-8") as tmp:
            tmp.write("127.0.0.1 localhost\n::1 localhost\n")
            self.hosts_path = tmp.name

    def tearDown(self):
        if os.path.exists(self.hosts_path):
            os.remove(self.hosts_path)

    def test_is_admin_does_not_crash(self):
        res = is_admin()
        self.assertIsInstance(res, bool)

    def test_edit_hosts_apply_and_remove(self):
        # Apply entry
        ok = _edit_hosts("vpn.example.com", "100.64.0.1", hosts_path=self.hosts_path)
        self.assertTrue(ok)

        with open(self.hosts_path, encoding="utf-8") as f:
            content = f.read()
        self.assertIn("100.64.0.1 vpn.example.com # Headscale Auto-Fallback", content)

        # Update entry
        ok = _edit_hosts("vpn.example.com", "100.64.0.2", hosts_path=self.hosts_path)
        self.assertTrue(ok)
        with open(self.hosts_path, encoding="utf-8") as f:
            content = f.read()
        self.assertIn("100.64.0.2 vpn.example.com # Headscale Auto-Fallback", content)
        self.assertNotIn("100.64.0.1", content)

        # Remove entry
        ok = _edit_hosts("vpn.example.com", None, hosts_path=self.hosts_path)
        self.assertTrue(ok)
        with open(self.hosts_path, encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("vpn.example.com", content)

    def test_run_cli_if_requested_ignored_on_normal_startup(self):
        self.assertIsNone(run_cli_if_requested(["main.py"]))
        self.assertIsNone(run_cli_if_requested(["main.py", "--self-test"]))


if __name__ == "__main__":
    unittest.main()
