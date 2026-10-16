import ctypes
import os
import shutil
import subprocess
import sys

if sys.platform == "win32":
    HOSTS_FILE = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "drivers", "etc", "hosts")  # noqa: SIM112
else:
    HOSTS_FILE = "/etc/hosts"


def is_admin():
    if sys.platform == "win32":
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except (AttributeError, OSError):
            return False
    else:
        try:
            return os.geteuid() == 0
        except AttributeError:
            return False


def _edit_hosts(domain, ip=None, hosts_path=None):
    target_file = hosts_path or HOSTS_FILE
    try:
        with open(target_file, encoding="utf-8") as f:
            lines = f.readlines()

        # Remove existing entries for this domain
        new_lines = []
        for line in lines:
            if not line.strip().startswith('#'):
                parts = line.split()
                if len(parts) >= 2 and parts[1].lower() == domain.lower():
                    continue
            new_lines.append(line)

        # Add new if ip is provided
        if ip:
            if not new_lines or not new_lines[-1].endswith('\n'):
                new_lines.append('\n')
            new_lines.append(f"{ip} {domain} # Headscale Auto-Fallback\n")

        with open(target_file, 'w', encoding="utf-8") as f:
            f.writelines(new_lines)

        return True
    except (OSError, UnicodeError):
        return False


def apply_fallback(domain, ip, hosts_path=None):
    """Attempts to map a domain to an IP in the system hosts file.
    Uses 'check-first' elevation logic to elevate only if necessary.
    """
    import socket

    target_file = hosts_path or HOSTS_FILE

    # If the domain already resolves to the target IP, no edit is needed.
    try:
        if socket.gethostbyname(domain) == ip:
            return True
    except (socket.gaierror, socket.herror, OSError):
        pass

    # Try silent edit first
    try:
        with open(target_file, 'a', encoding="utf-8"):
            pass  # checking write access
        if _edit_hosts(domain, ip, target_file):
            return True
    except (PermissionError, OSError):
        pass

    # Needs elevation; automated background elevation via ShellExecuteW exists only on Windows.
    # On POSIX (Linux/macOS), elevation must be invoked explicitly (e.g. via pkexec/sudo CLI helper).
    if sys.platform != "win32":
        return False

    return _elevate(["apply", domain, ip])


def remove_fallback(domain, hosts_path=None):
    """Removes the domain mapping from the system hosts file."""
    target_file = hosts_path or HOSTS_FILE
    try:
        with open(target_file, 'a', encoding="utf-8"):
            pass
        if _edit_hosts(domain, None, target_file):
            return True
    except (PermissionError, OSError):
        pass

    if sys.platform != "win32":
        return False

    return _elevate(["remove", domain])


def _elevate(args):
    """Relaunches this program elevated via OS privilege escalation."""
    if sys.platform == "win32":
        quoted = " ".join(f'"{a}"' for a in args)
        if getattr(sys, "frozen", False):
            executable, params = sys.executable, f"--dns-fallback {quoted}"
        else:
            executable = sys.executable
            params = f'"{os.path.abspath(__file__)}" {quoted}'
        try:
            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, params, None, 0)
            return int(ret) > 32
        except (AttributeError, OSError):
            return False

    elif sys.platform == "darwin":
        # macOS: execute via osascript administrator privileges
        if getattr(sys, "frozen", False):
            inner_cmd = f"'{sys.executable}' --dns-fallback {' '.join(args)}"
        else:
            inner_cmd = f"'{sys.executable}' '{os.path.abspath(__file__)}' --dns-fallback {' '.join(args)}"
        apple_script = f'do shell script "{inner_cmd}" with administrator privileges'
        try:
            osascript_bin = shutil.which("osascript") or "osascript"
            res = subprocess.run([osascript_bin, "-e", apple_script], capture_output=True, text=True, check=False)
            return res.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    else:
        # Linux / POSIX: prioritize pkexec for graphical auth, fallback to sudo
        if getattr(sys, "frozen", False):
            cmd = [sys.executable, "--dns-fallback"] + list(args)
        else:
            cmd = [sys.executable, os.path.abspath(__file__), "--dns-fallback"] + list(args)

        if shutil.which("pkexec"):
            try:
                res = subprocess.run(["pkexec"] + cmd, capture_output=True, check=False)
                return res.returncode == 0
            except (OSError, subprocess.SubprocessError):
                pass

        if shutil.which("sudo"):
            try:
                res = subprocess.run(["sudo"] + cmd, capture_output=True, check=False)
                return res.returncode == 0
            except (OSError, subprocess.SubprocessError):
                pass

        return False


def run_cli_if_requested(argv=None):
    """Executes a --dns-fallback CLI request and returns an exit code.

    Returns None when this process was not launched as the fallback CLI
    (i.e. normal GUI startup), so the caller can continue booting.
    """
    argv = sys.argv if argv is None else argv
    if len(argv) < 3 or argv[1] != "--dns-fallback":
        return None
    action = argv[2]
    domain = argv[3] if len(argv) > 3 else ""
    ip = argv[4] if len(argv) > 4 else None
    if action == "apply" and domain and ip:
        return 0 if _edit_hosts(domain, ip) else 1
    if action == "remove" and domain:
        return 0 if _edit_hosts(domain, None) else 1
    return 2


if __name__ == "__main__":
    code = run_cli_if_requested()
    if code is None and len(sys.argv) >= 3 and sys.argv[1] in ("apply", "remove"):
        # Legacy source form: python dns_fallback.py apply <domain> <ip>
        code = run_cli_if_requested([sys.argv[0], "--dns-fallback"] + sys.argv[1:])
    sys.exit(0 if code is None else code)
