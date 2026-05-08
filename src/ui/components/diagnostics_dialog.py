import os
from PySide6.QtWidgets import QDialog, QPushButton, QTextBrowser, QMessageBox
from PySide6.QtCore import QProcess, Qt
from .simple_dialogs import BaseUiDialog
from ...core.tailscale import get_tailscale_path

class DiagnosticsDialog(BaseUiDialog):
    def __init__(self, parent=None):
        super().__init__("diagnostics.ui", parent)
        self.setFixedSize(580, 440)
        
        # Resolve UI elements
        self.textDiagnostics = self.ui.findChild(QTextBrowser, "textDiagnostics")
        self.btnRunDiagnostics = self.ui.findChild(QPushButton, "btnRunDiagnostics")
        self.btnClose = self.ui.findChild(QPushButton, "btnClose")
        
        # Setup QProcess
        self.proc = QProcess(self)
        self.proc.readyReadStandardOutput.connect(self._on_stdout_ready)
        self.proc.readyReadStandardError.connect(self._on_stderr_ready)
        self.proc.finished.connect(self._on_process_finished)
        
        # Connect signals
        if self.btnRunDiagnostics:
            self.btnRunDiagnostics.clicked.connect(self._run_netcheck)
        if self.btnClose:
            self.btnClose.clicked.connect(self.accept)

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
