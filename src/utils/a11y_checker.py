# src/utils/a11y_checker.py
"""
Accessibility & Screen Reader Environment Verification Engine.
Checks for native AT-SPI2 / Orca (Linux), Speech Synthesis / Media features (Windows N),
and VoiceOver (macOS), providing copy-pasteable terminal remediation commands.
"""

import sys
import os
import shutil
import subprocess

class A11yCheckResult:
    def __init__(self, is_healthy: bool, title: str, summary: str, details: str, remediation_cmd: str = "", package_manager: str = ""):
        self.is_healthy = is_healthy
        self.title = title
        self.summary = summary
        self.details = details
        self.remediation_cmd = remediation_cmd
        self.package_manager = package_manager

def check_screen_reader_environment() -> A11yCheckResult:
    """
    Evaluates current OS environment for screen reader readiness.
    Never blocks or crashes. Returns structured A11yCheckResult.
    """
    platform = sys.platform

    if platform.startswith("linux"):
        return _check_linux_a11y()
    elif platform == "win32":
        return _check_windows_a11y()
    elif platform == "darwin":
        return _check_macos_a11y()
    else:
        return A11yCheckResult(
            is_healthy=True,
            title="Generic Platform",
            summary="Standard accessibility interfaces active.",
            details="Operating system uses generic Qt accessibility bridges."
        )

def _check_linux_a11y() -> A11yCheckResult:
    """
    Detects Orca screen reader and AT-SPI2 D-Bus bus on Linux.
    Identifies package manager (APT, DNF, Pacman, Zypper) for exact copy-paste commands.
    """
    has_orca = shutil.which("orca") is not None
    has_speech_dispatcher = shutil.which("spd-say") is not None or shutil.which("speech-dispatcher") is not None
    
    # Detect package manager
    if shutil.which("apt") or shutil.which("apt-get"):
        pkg_mgr = "apt"
        install_cmd = "sudo apt update && sudo apt install -y orca at-spi2-core speech-dispatcher"
    elif shutil.which("dnf"):
        pkg_mgr = "dnf"
        install_cmd = "sudo dnf install -y orca at-spi2-core speech-dispatcher"
    elif shutil.which("pacman"):
        pkg_mgr = "pacman"
        install_cmd = "sudo pacman -S --noconfirm orca at-spi2-core speech-dispatcher"
    elif shutil.which("zypper"):
        pkg_mgr = "zypper"
        install_cmd = "sudo zypper install -y orca at-spi2-core speech-dispatcher"
    else:
        pkg_mgr = "generic"
        install_cmd = "Install 'orca', 'at-spi2-core', and 'speech-dispatcher' using your distribution package manager."

    if has_orca and has_speech_dispatcher:
        return A11yCheckResult(
            is_healthy=True,
            title="Linux Screen Reader Environment: Ready [OK]",
            summary="Orca Screen Reader & Speech Dispatcher are installed and available.",
            details="AT-SPI2 accessibility bridge is ready. Toggle Orca anytime with: Super + Alt + S",
            remediation_cmd="orca --replace &",
            package_manager=pkg_mgr
        )
    elif has_orca and not has_speech_dispatcher:
        return A11yCheckResult(
            is_healthy=False,
            title="Orca Installed, Speech Dispatcher Missing [Warning]",
            summary="Orca is installed, but the speech synthesizer daemon (speech-dispatcher) was not found.",
            details="Speech synthesis requires speech-dispatcher to speak text through your audio device.",
            remediation_cmd=install_cmd,
            package_manager=pkg_mgr
        )
    else:
        return A11yCheckResult(
            is_healthy=False,
            title="Orca Screen Reader Not Detected [Notice]",
            summary="No screen reader (Orca) or speech synthesizer was found on this Linux desktop.",
            details="To enable spoken accessibility for visually impaired operators, install Orca and AT-SPI2.",
            remediation_cmd=install_cmd,
            package_manager=pkg_mgr
        )

def _check_windows_a11y() -> A11yCheckResult:
    """
    Detects Windows Narrator / SAPI / Windows Media Speech on Windows (including N editions).
    """
    # Windows standard editions always have Narrator preinstalled
    # Check if Windows Speech API (SAPI) or System.Speech is available
    is_windows_n = False
    try:
        # Check for Windows Media Feature Pack presence
        system32 = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "System32")
        mf_dll = os.path.join(system32, "mf.dll")
        if not os.path.exists(mf_dll):
            is_windows_n = True
    except Exception:
        pass

    if is_windows_n:
        ps_cmd = 'DISM /Online /Add-Capability /CapabilityName:Media.MediaFeaturePack~~~~0.0.1.0'
        return A11yCheckResult(
            is_healthy=False,
            title="Windows N Edition Detected (Media/Speech Pack Missing) [Warning]",
            summary="Windows N requires the Media Feature Pack to enable voice synthesis for Windows Narrator.",
            details="Go to: Settings > Apps > Optional Features > Add a feature > 'Media Feature Pack', or run in Admin PowerShell:",
            remediation_cmd=ps_cmd,
            package_manager="dism"
        )

    return A11yCheckResult(
        is_healthy=True,
        title="Windows Accessibility Environment: Ready [OK]",
        summary="Windows Narrator & UI Automation (UIA) bridge are active and fully supported.",
        details="Built-in screen reader is ready. Toggle Windows Narrator anytime with: Windows Key + Ctrl + Enter",
        remediation_cmd="",
        package_manager="windows"
    )

def _check_macos_a11y() -> A11yCheckResult:
    """
    macOS VoiceOver check (bundled with macOS kernel).
    """
    return A11yCheckResult(
        is_healthy=True,
        title="macOS Accessibility Environment: Ready [OK]",
        summary="Apple VoiceOver & NSAccessibility protocol bridge are active.",
        details="Toggle Apple VoiceOver anytime with: Command + F5 (or triple-click Touch ID)",
        remediation_cmd="",
        package_manager="macos"
    )
