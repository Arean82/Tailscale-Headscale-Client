import sys
import os

def set_autostart(enabled: bool):
    """Enable or disable application run at OS startup across Windows, Linux, and macOS."""
    app_name = "TailscaleClientPro"
    # Get absolute path to the main.py or executable running
    import main
    exec_path = os.path.abspath(main.__file__)
    
    # If running as python script, we want to launch it with python interpreter
    if exec_path.endswith(".py"):
        command = f'"{sys.executable}" "{exec_path}"'
    else:
        command = f'"{exec_path}"'

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
                    pass
            winreg.CloseKey(key)
        except Exception:
            pass

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
            except Exception:
                pass
        else:
            if os.path.exists(desktop_file):
                try:
                    os.remove(desktop_file)
                except Exception:
                    pass

    elif sys.platform == "darwin":
        launch_agents_dir = os.path.expanduser("~/Library/LaunchAgents")
        plist_file = os.path.join(launch_agents_dir, f"com.tailscale.clientpro.plist")
        
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
            except Exception:
                pass
        else:
            if os.path.exists(plist_file):
                try:
                    os.remove(plist_file)
                except Exception:
                    pass
