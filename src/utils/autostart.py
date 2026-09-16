import logging
import os
import sys

logger = logging.getLogger("TailscaleClient.Autostart")


def set_autostart(enabled: bool):
    """Enable or disable application run at OS startup across Windows, Linux, and macOS."""
    app_name = "TailscaleClientPro"
    exec_path = os.path.abspath(sys.argv[0])
    
    # If running as python script, launch it with the python interpreter
    command = f'"{sys.executable}" "{exec_path}"' if exec_path.endswith(".py") else f'"{exec_path}"'

    if sys.platform == "win32":
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            if enabled:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, command)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    # Key already deleted or never existed
                    return
            winreg.CloseKey(key)
        except OSError:
            # Insufficient registry privileges
            return

    elif sys.platform.startswith("linux"):
        autostart_dir = os.path.expanduser("~/.config/autostart")
        desktop_file = os.path.join(autostart_dir, f"{app_name}.desktop")
        
        if enabled:
            os.makedirs(autostart_dir, exist_ok=True)
            desktop_content = f"""[Desktop Entry]
Type=Application
Name=Tailscale Client Pro
Exec={command}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Comment=Start Tailscale Client Pro at startup
"""
            try:
                with open(desktop_file, "w", encoding="utf-8") as f:
                    f.write(desktop_content)
            except OSError:
                return
        else:
            if os.path.exists(desktop_file):
                try:
                    os.remove(desktop_file)
                except OSError:
                    return

    elif sys.platform == "darwin":
        launch_agents_dir = os.path.expanduser("~/Library/LaunchAgents")
        plist_file = os.path.join(launch_agents_dir, "com.tailscale.clientpro.plist")
        
        if enabled:
            os.makedirs(launch_agents_dir, exist_ok=True)
            # Split executable and script if run via python
            args_str = ""
            if exec_path.endswith(".py"):
                args_str = f"""        <string>{sys.executable}</string>
        <string>{exec_path}</string>"""
            else:
                args_str = f"        <string>{exec_path}</string>"
                
            plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.tailscale.clientpro</string>
    <key>ProgramArguments</key>
    <array>
{args_str}
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
"""
            try:
                with open(plist_file, "w", encoding="utf-8") as f:
                    f.write(plist_content)
            except OSError:
                return
            # Writing the plist alone only takes effect at the next login; load
            # the agent now so the toggle is immediate (and reload after edits).
            _launchctl("unload", plist_file)
            _launchctl("load", plist_file, "-w")
        else:
            if os.path.exists(plist_file):
                try:
                    os.remove(plist_file)
                except OSError:
                    return
            # Stop the already-loaded agent too, otherwise disabling the setting
            # would leave it running until the next login.
            _launchctl("unload", plist_file, "-w")


def _launchctl(action, plist_file, *extra):
    """Best-effort launchctl call; failures are logged, never raised."""
    import subprocess

    attempts = [["launchctl", action] + list(extra) + [plist_file]]  # legacy syntax, still widely supported
    if hasattr(os, "getuid"):  # POSIX only: the modern syntax needs the gui/<uid> domain
        modern_action = "bootstrap" if action == "load" else "bootout"
        attempts.append(["launchctl", modern_action, f"gui/{os.getuid()}", plist_file])

    for index, command in enumerate(attempts):
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False, shell=False)
        except (OSError, subprocess.SubprocessError) as e:
            logger.debug(f"launchctl {action} failed: {e}")
            continue
        if result.returncode == 0:
            return True
        # Only fall through to the modern syntax when the legacy form is rejected
        if index == 0:
            logger.debug(f"launchctl {action} (legacy) returned {result.returncode}: {result.stderr.strip()[:120]}")
    logger.debug(f"launchctl {action} did not succeed for {plist_file}")
    return False
