from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QPushButton, QTextBrowser

from ...core.tailscale import get_tailscale_path
from .simple_dialogs import BaseUiDialog


class DiagnosticsDialog(BaseUiDialog):
    def __init__(self, parent=None):
        super().__init__("diagnostics.ui", parent)
        self.setFixedSize(580, 440)
        
        # Resolve UI elements
        self.textDiagnostics = self.ui.findChild(QTextBrowser, "textDiagnostics")
        self.btnRunDiagnostics = self.ui.findChild(QPushButton, "btnRunDiagnostics")
        self.btnCheckA11y = self.ui.findChild(QPushButton, "btnCheckA11y")
        self.btnClose = self.ui.findChild(QPushButton, "btnClose")
        
        # Setup QProcess
        self.proc = QProcess(self)
        self.proc.readyReadStandardOutput.connect(self._on_stdout_ready)
        self.proc.readyReadStandardError.connect(self._on_stderr_ready)
        self.proc.finished.connect(self._on_process_finished)
        
        # Connect signals
        if self.btnRunDiagnostics:
            self.btnRunDiagnostics.clicked.connect(self._run_netcheck)
        if self.btnCheckA11y:
            self.btnCheckA11y.clicked.connect(self._check_a11y)
        if self.btnClose:
            self.btnClose.clicked.connect(self.accept)

        # Accessibility (EN 301 549 11.2.1.1 / WCAG 1.1.1 Non-text Content)
        diag_a11y = [
            (self.textDiagnostics, "Diagnostics Output Console",
             "Read-only console showing Tailscale netcheck results and accessibility diagnostics."),
            (self.btnRunDiagnostics, "Run Netcheck Button",
             "Runs the Tailscale network diagnostics and prints the report below."),
            (self.btnCheckA11y, "Check Screen Reader Button",
             "Verifies that assistive technology components are installed and active."),
            (self.btnClose, "Close Diagnostics Button",
             "Dismisses the diagnostics dialog."),
        ]
        for widget, name, description in diag_a11y:
            if widget:
                widget.setAccessibleName(name)
                widget.setAccessibleDescription(description)

    def _check_a11y(self):
        from ...utils.a11y_checker import check_screen_reader_environment
        res = check_screen_reader_environment()
        
        if self.textDiagnostics:
            self.textDiagnostics.clear()
            self.textDiagnostics.append(f"=== {res.title} ===\n")
            self.textDiagnostics.append(f"Status: {res.summary}\n")
            self.textDiagnostics.append(f"Details: {res.details}\n")
            if res.remediation_cmd:
                self.textDiagnostics.append("--------------------------------------------------")
                self.textDiagnostics.append("Terminal Installation / Activation Command:")
                self.textDiagnostics.append(f"  {res.remediation_cmd}\n")
                self.textDiagnostics.append("--------------------------------------------------")
                self.textDiagnostics.append("(You can copy and run the command above in your terminal.)")

    def _run_netcheck(self):
        if self.btnRunDiagnostics:
            self.btnRunDiagnostics.setText("Analyzing...")
            self.btnRunDiagnostics.setEnabled(False)
            
        if self.textDiagnostics:
            self.textDiagnostics.clear()
            self.textDiagnostics.append("--- Initializing Tailscale Netcheck Asynchronously ---\n")
            
        self.proc.start(get_tailscale_path(), ["netcheck"])

    def _on_stdout_ready(self):
        output = self.proc.readAllStandardOutput().data().decode(errors="ignore")
        if self.textDiagnostics:
            self.textDiagnostics.insertPlainText(output)

    def _on_stderr_ready(self):
        err = self.proc.readAllStandardError().data().decode(errors="ignore")
        if self.textDiagnostics:
            self.textDiagnostics.insertPlainText(err)

    def _on_process_finished(self, exit_code, exit_status):
        if self.btnRunDiagnostics:
            self.btnRunDiagnostics.setText("Run Netcheck")
            self.btnRunDiagnostics.setEnabled(True)
            
        if self.textDiagnostics:
            self.textDiagnostics.append(f"\n--- Analysis Complete (Exit Code: {exit_code}) ---")

    def closeEvent(self, event):
        if self.proc.state() != QProcess.NotRunning:
            self.proc.terminate()
            self.proc.waitForFinished(500)
        super().closeEvent(event)
