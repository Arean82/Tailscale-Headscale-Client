# os_specific/command_executor.py
# This module provides a function to execute shell commands in a cross-platform manner.

import sys
import subprocess

def execute_command(cmd, require_sudo=False, output_callback=None, error_log_callback=None):
    """
    Executes a shell command and returns its output.
    Handles OS-specific process creation flags and elevation.

    Args:
        cmd (list): The command and its arguments as a list.
        require_sudo (bool): If True, attempts to elevate privileges (pkexec on Linux).
        output_callback (callable): A function to call for displaying command output.
        error_log_callback (callable): A function to call for logging errors.
    """
    startupinfo = None
    if sys.platform == "win32":
        # On Windows, hide the console window for subprocesses
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    
    if require_sudo and sys.platform.startswith("linux"):
        if output_callback:
            output_callback("Elevated command: using pkexec.")
        # For Linux, use pkexec to prompt for graphical password for sudo commands
        cmd = ["pkexec"] + cmd
    elif require_sudo and sys.platform == "win32":
        # On Windows, Tailscale commands often require administrator privileges.
        # We rely on Tailscale's internal elevation prompt or the user running
        # the application with administrator rights. subprocess.run doesn't
        # have a direct, cross-platform 'runas' equivalent that captures output.
        if output_callback:
            output_callback("Windows commands requiring elevation usually prompt or need an elevated terminal.")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo)
        return result.stdout + result.stderr
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
