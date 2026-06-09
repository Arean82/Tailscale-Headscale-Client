import os
import sys
import ctypes

HOSTS_FILE = r"C:\Windows\System32\drivers\etc\hosts"

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def _edit_hosts(domain, ip=None):
    try:
        with open(HOSTS_FILE, 'r') as f:
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
    except Exception as e:
        return False

def apply_fallback(domain, ip):
    """
    Attempts to map a domain to an IP in the system hosts file.
    Uses 'check-first' UAC logic to elevate only if necessary.
    """
    # Check if domain already maps to this IP
    try:
        import socket
        if socket.gethostbyname(domain) == ip:
            return True # Already resolving correctly, no need to touch hosts
    except Exception:
        pass

    # Try silent edit first
    try:
        with open(HOSTS_FILE, 'a') as f:
            pass # just checking write access
        if _edit_hosts(domain, ip):
            return True
    except PermissionError:
        pass
        
    # Needs elevation
    script_path = os.path.abspath(__file__)
    # ShellExecuteW returns > 32 if successful
    ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script_path}" apply "{domain}" "{ip}"', None, 0)
    return int(ret) > 32

def remove_fallback(domain):
    """
    Removes the domain mapping from the system hosts file.
    """
    # Try silent first
    try:
        with open(HOSTS_FILE, 'a') as f:
            pass
        if _edit_hosts(domain, None):
            return True
    except PermissionError:
        pass
        
    script_path = os.path.abspath(__file__)
    ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script_path}" remove "{domain}"', None, 0)
    return int(ret) > 32

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        action = sys.argv[1]
        domain = sys.argv[2]
        ip = sys.argv[3] if len(sys.argv) > 3 else None
        
        if action == "apply" and ip:
            _edit_hosts(domain, ip)
        elif action == "remove":
            _edit_hosts(domain, None)
