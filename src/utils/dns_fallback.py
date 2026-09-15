import ctypes
import os
import sys

HOSTS_FILE = r"C:\Windows\System32\drivers\etc\hosts"

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except (AttributeError, OSError):
        return False

def _edit_hosts(domain, ip=None):
    try:
        with open(HOSTS_FILE) as f:
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
            
        with open(HOSTS_FILE, 'w') as f:
            f.writelines(new_lines)
            
        return True
    except (OSError, UnicodeError):
        return False

def apply_fallback(domain, ip):
    """
    Attempts to map a domain to an IP in the system hosts file.
    Uses 'check-first' UAC logic to elevate only if necessary.
    """
    import socket

    # If the domain already resolves to the target IP, no edit is needed.
    try:
        if socket.gethostbyname(domain) == ip:
            return True
    except (socket.gaierror, socket.herror, OSError):
        # DNS resolution failed: this is exactly the emergency the fallback
        # exists for — pin the domain via the hosts file instead of giving up.
        pass

    # Try silent edit first
    try:
        with open(HOSTS_FILE, 'a'):
            pass # just checking write access
        if _edit_hosts(domain, ip):
            return True
    except (PermissionError, OSError):
        # Requires Administrator elevation; fall through to UAC invocation
        pass
        
    # Needs elevation; the ShellExecuteW "runas" helper exists only on Windows
    if sys.platform != "win32":
        return False
    return _elevate(["apply", domain, ip])

def remove_fallback(domain):
    """
    Removes the domain mapping from the system hosts file.
    """
    # Try silent first
    try:
        with open(HOSTS_FILE, 'a'):
            pass
        if _edit_hosts(domain, None):
            return True
    except (PermissionError, OSError):
        # Requires Administrator elevation; fall through to UAC invocation
        pass

    if sys.platform != "win32":
        return False
    return _elevate(["remove", domain])


def _elevate(args):
    """Relaunches this program elevated via UAC to perform a hosts-file CLI action.

    Frozen builds re-invoke the packaged executable; main.py routes its
    --dns-fallback arguments before the GUI or single-instance lock start.
    """
    quoted = " ".join(f'"{a}"' for a in args)
    if getattr(sys, "frozen", False):
        executable, params = sys.executable, f"--dns-fallback {quoted}"
    else:
        executable = sys.executable
        params = f'"{os.path.abspath(__file__)}" {quoted}'
    # ShellExecuteW returns > 32 if successful
    ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, params, None, 0)
    return int(ret) > 32


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
