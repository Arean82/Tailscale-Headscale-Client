import sys
import subprocess
import webbrowser
import re
import os
import platform

print("[DEBUG] command_executor.py loaded")

def open_browser(url):
    try:
        if platform.system() == "Windows":
            try:
                os.startfile(url)
            except OSError:
                subprocess.run(["cmd", "/c", "start", "", url], shell=True)
        else:
            webbrowser.open(url)
    except Exception as e:
        print(f"[ERROR] Failed to open browser: {e}")

def execute_command(cmd, require_sudo=False, output_callback=None, error_log_callback=None):
    print("[DEBUG] execute_command called with:", cmd)
    startupinfo = None
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    if require_sudo and sys.platform.startswith("linux"):
        if output_callback:
            output_callback("Elevated command: using pkexec.")
        cmd = ["pkexec"] + cmd
    elif require_sudo and sys.platform == "win32":
        if output_callback:
            output_callback("Windows commands requiring elevation usually prompt or need an elevated terminal.")

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, startupinfo=startupinfo)

        output_lines = []
        url_opened = False

        for line in process.stdout:
            print(f"[DEBUG] Line from Tailscale: {repr(line)}")
            if output_callback:
                output_callback(line.rstrip())
            output_lines.append(line)

            # Strip only leading/trailing whitespace for matching
            trimmed_line = line.strip()

            # Match a URL, even if it’s the only thing on a line with spaces
            if not url_opened and "https://" in trimmed_line:
                match = re.search(r'https://\S+', trimmed_line)
                if match:
                    url = match.group(0)
                    print(f"[DEBUG] Detected URL: {url}")
                    open_browser(url)
                    url_opened = True  # Prevent opening more than once

        process.wait()
        return ''.join(output_lines)

    except FileNotFoundError:
        error_msg = "Error: Command not found. Ensure the executable is installed and in your PATH."
        if error_log_callback:
            error_log_callback(f"FileNotFoundError for command '{' '.join(cmd)}': {error_msg}", level="ERROR")
        return error_msg
    except Exception as e:
        error_msg = f"Error running command: {e}"
        if error_log_callback:
            error_log_callback(f"Exception running command '{' '.join(cmd)}': {e}", level="ERROR")
        return error_msg
