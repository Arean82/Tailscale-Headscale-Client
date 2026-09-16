import logging
import os

from PySide6.QtCore import QFile, Qt, Signal
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QDialog,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from ...utils.logger import SignalLogHandler

LEVEL_COLORS = {
    "error": "#F44336",
    "warning": "#FFC107",
    "debug": "#9C27B0",
    "info": "#4CAF50",
}


def classify_line(line):
    """Classifies a log line for colouring and filtering. Shared by the file
    reader and the live stream so both behave identically."""
    upper = line.upper()
    if "ERROR" in upper or "CRITICAL" in upper or "EXCEPTION" in upper:
        return "error"
    if "WARNING" in upper or "WARN" in upper:
        return "warning"
    if "DEBUG" in upper:
        return "debug"
    return "info"


class LogViewerDialog(QDialog):
    # Records arriving from the logging system (possibly from worker threads);
    # Qt queues the emission to this dialog's thread automatically.
    record_received = Signal(str)

    def __init__(self, log_path, display_name, parent=None):
        super().__init__(parent)
        self.log_file = log_path
        self.display_name = display_name
        self._live_handler = None
        
        self.setWindowTitle(f"Log: {display_name}")
        self.setFixedSize(900, 650)
        
        # Load UI
        loader = QUiLoader()
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        ui_path = os.path.join(base_dir, "pygui", "dialogs", "log_viewer.ui")
        ui_file = QFile(ui_path)
        ui_file.open(QFile.ReadOnly)
        self.ui = loader.load(ui_file)
        ui_file.close()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)
        
        # Widget refs
        self.searchEntry = self.ui.findChild(QLineEdit, "searchEntry")
        self.btnSearch   = self.ui.findChild(QPushButton, "searchBtn")
        self.btnRefresh  = self.ui.findChild(QPushButton, "refreshBtn")
        self.btnClear    = self.ui.findChild(QPushButton, "clearBtn")
        self.textBrowser = self.ui.findChild(QTextBrowser, "textBrowser")
        self.btnClose    = self.ui.findChild(QPushButton, "closeBtn")
        self.btnExport   = self.ui.findChild(QPushButton, "exportBtn")
        
        self.btnInfo     = self.ui.findChild(QPushButton, "infoBtn")
        self.btnWarn     = self.ui.findChild(QPushButton, "warningBtn")
        self.btnError    = self.ui.findChild(QPushButton, "errorBtn")
        self.btnDebug    = self.ui.findChild(QPushButton, "debugBtn")

        # Accessibility (EN 301 549 11.2.1.1 / WCAG 1.1.1 Non-text Content)
        log_a11y = [
            (self.searchEntry, "Log Search Filter Input", "Enter query text to highlight occurrences in the log stream."),
            (self.btnSearch, "Execute Log Search Button", "Searches and highlights matching terms in the active log viewer."),
            (self.btnRefresh, "Refresh Logs Button", "Reloads the latest log file records from disk."),
            (self.btnClear, "Clear Logs Button", "Flushes all buffered log entries from the display."),
            (self.textBrowser, "Log Output Stream", "Console displaying colored diagnostic, connection, and error messages."),
            (self.btnClose, "Close Log Viewer Button", "Dismisses the log viewer dialog."),
            (self.btnExport, "Export Logs Button", "Saves the currently visible log output to a text file."),
            (self.btnInfo, "Filter INFO Level Toggle", "Toggles visibility of INFO level log entries."),
            (self.btnWarn, "Filter WARN Level Toggle", "Toggles visibility of WARNING level log entries."),
            (self.btnError, "Filter ERROR Level Toggle", "Toggles visibility of ERROR level log entries."),
            (self.btnDebug, "Filter DEBUG Level Toggle", "Toggles visibility of DEBUG level log entries."),
        ]
        for w, name, desc in log_a11y:
            if w:
                w.setAccessibleName(name)
                w.setAccessibleDescription(desc)

        # Connections
        if self.btnSearch: self.btnSearch.clicked.connect(self._search_text)
        if self.searchEntry: self.searchEntry.returnPressed.connect(self._search_text)
        if self.btnRefresh: self.btnRefresh.clicked.connect(self._read_content)
        if self.btnClear: self.btnClear.clicked.connect(self._clear_log)
        if self.btnClose: self.btnClose.clicked.connect(self.accept)
        if self.btnExport: self.btnExport.clicked.connect(self._export_logs)
        
        if self.btnInfo: self.btnInfo.toggled.connect(self._read_content)
        if self.btnWarn: self.btnWarn.toggled.connect(self._read_content)
        if self.btnError: self.btnError.toggled.connect(self._read_content)
        if self.btnDebug: self.btnDebug.toggled.connect(self._read_content)

        self._read_content()
        self._attach_live_tail()

    # ------------------------------------------------------------------
    # Live tailing
    # ------------------------------------------------------------------

    def _attach_live_tail(self):
        """Stream new records as they are emitted.

        Without this the viewer only reflects what was on disk when it opened
        (or when Refresh was pressed). Handlers are attached to the app logger,
        which is the parent of every application/UI logger, matching exactly
        what the rotating file handler writes.
        """
        if self._live_handler is not None:
            return
        self.record_received.connect(self._append_live_line)
        self._live_handler = SignalLogHandler(self.record_received.emit)
        logging.getLogger("TailscaleClient").addHandler(self._live_handler)

    def _detach_live_tail(self):
        if self._live_handler is not None:
            logging.getLogger("TailscaleClient").removeHandler(self._live_handler)
            self._live_handler = None

    def _level_enabled(self, level):
        toggle = {
            "error": self.btnError,
            "warning": self.btnWarn,
            "debug": self.btnDebug,
            "info": self.btnInfo,
        }[level]
        return bool(toggle is None or toggle.isChecked())

    def _format_for(self, level):
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(LEVEL_COLORS[level]))
        return fmt

    def _append_live_line(self, line):
        if not self.textBrowser:
            return
        level = classify_line(line)
        if not self._level_enabled(level):
            return

        scrollbar = self.textBrowser.verticalScrollBar()
        follow = scrollbar.value() >= scrollbar.maximum() - 4

        cursor = self.textBrowser.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(line + "\n", self._format_for(level))
        if follow:
            self.textBrowser.moveCursor(QTextCursor.End)
            scrollbar.setValue(scrollbar.maximum())

    def _read_content(self):
        if not self.textBrowser: return
        self.textBrowser.clear()

        if not os.path.exists(self.log_file):
            self.textBrowser.setPlainText(f"[Log file not found: {self.log_file}]")
            return

        cursor = self.textBrowser.textCursor()

        try:
            with open(self.log_file, encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                
            tail_lines = lines[-1000:] if len(lines) > 1000 else lines
            
            cursor.beginEditBlock()
            for line in tail_lines:
                    level = classify_line(line)
                    if not self._level_enabled(level):
                        continue
                    cursor.insertText(line, self._format_for(level))
            cursor.endEditBlock()
        except OSError as e:
            cursor.insertText(f"Failed to read log: {e}")

        self.textBrowser.moveCursor(QTextCursor.End)

    def _search_text(self):
        if not self.textBrowser: return
        query = self.searchEntry.text()
        if not query: return
        found = self.textBrowser.find(query)
        if not found:
            self.textBrowser.moveCursor(QTextCursor.Start)
            self.textBrowser.find(query)

    def _clear_log(self):
        reply = QMessageBox.question(self, "Confirm", "Clear this log file?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                open(self.log_file, "w").close()
                self._read_content()
            except OSError as e:
                QMessageBox.critical(self, "Error", str(e))

    def _export_logs(self):
        import zipfile

        from PySide6.QtWidgets import QFileDialog
        
        save_path, _ = QFileDialog.getSaveFileName(self, "Export Logs", os.path.expanduser("~/TailscaleClientPro_Logs.zip"), "ZIP Files (*.zip)")
        if not save_path:
            return
            
        try:
            log_dir = os.path.dirname(self.log_file)
            with zipfile.ZipFile(save_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(log_dir):
                    for file in files:
                        if file.endswith(('.log', '.txt')):
                            full_file_path = os.path.join(root, file)
                            arcname = os.path.relpath(full_file_path, log_dir)
                            zipf.write(full_file_path, arcname)
                            
            QMessageBox.information(self, "Export Successful", f"All logs have been successfully bundled and exported to:\n{save_path}")
        except (OSError, zipfile.BadZipFile) as e:
            QMessageBox.critical(self, "Export Failed", f"An error occurred while exporting logs:\n{e}")

    def showEvent(self, event):
        """Inherit theme styling from parent window upon display."""
        win = self.window()
        if win and hasattr(win, "_apply_theme_to_dialog"):
            win._apply_theme_to_dialog(self)
        else:
            parent = self.parent()
            while parent:
                if hasattr(parent, "_apply_theme_to_dialog"):
                    parent._apply_theme_to_dialog(self)
                    break
                parent = parent.parent() if hasattr(parent, "parent") else None
        super().showEvent(event)

    def closeEvent(self, event):
        """Stop streaming before the dialog goes away (no dangling handlers)."""
        self._detach_live_tail()
        super().closeEvent(event)

    def keyPressEvent(self, event):
        """Ensure Escape dismisses LogViewerDialog (EN 301 549 11.2.1.2 - No Keyboard Trap)."""
        if event.key() == Qt.Key_Escape:
            self.accept()
            event.accept()
            return
        super().keyPressEvent(event)
