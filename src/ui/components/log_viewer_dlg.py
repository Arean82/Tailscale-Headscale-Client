import os
import sys
from PySide6.QtWidgets import QDialog, QVBoxLayout, QMessageBox, QPushButton, QLineEdit, QTextBrowser, QCheckBox, QProgressBar, QWidget
from PySide6.QtGui import QTextCharFormat, QColor, QTextCursor
from PySide6.QtCore import Qt
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile

class LogViewerDialog(QDialog):
    def __init__(self, log_path, display_name, parent=None):
        super().__init__(parent)
        self.log_file = log_path
        self.display_name = display_name
        
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

    def _read_content(self):
        if not self.textBrowser: return
        self.textBrowser.clear()

        if not os.path.exists(self.log_file):
            self.textBrowser.setPlainText(f"[Log file not found: {self.log_file}]")
            return

        # Colour formats
        fmt_info    = QTextCharFormat()
        fmt_info.setForeground(QColor("#4CAF50"))
        fmt_warn    = QTextCharFormat()
        fmt_warn.setForeground(QColor("#FFC107"))
        fmt_error   = QTextCharFormat()
        fmt_error.setForeground(QColor("#F44336"))
        fmt_debug   = QTextCharFormat()
        fmt_debug.setForeground(QColor("#9C27B0"))
        fmt_default = QTextCharFormat()
        fmt_default.setForeground(QColor("#ffffff"))

        cursor = self.textBrowser.textCursor()
        
        show_info  = self.btnInfo.isChecked() if self.btnInfo else True
        show_warn  = self.btnWarn.isChecked() if self.btnWarn else True
        show_error = self.btnError.isChecked() if self.btnError else True
        show_debug = self.btnDebug.isChecked() if self.btnDebug else True

        try:
            with open(self.log_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                
            tail_lines = lines[-1000:] if len(lines) > 1000 else lines
            
            cursor.beginEditBlock()
            for line in tail_lines:
                    up = line.upper()
                    
                    is_error = "ERROR" in up or "CRITICAL" in up or "EXCEPTION" in up
                    is_warn  = "WARNING" in up or "WARN" in up
                    is_debug = "DEBUG" in up
                    is_info  = "INFO" in up and not (is_error or is_warn or is_debug)
                    
                    if not (is_error or is_warn or is_debug or is_info):
                        is_info = True

                    if is_error and not show_error: continue
                    if is_warn and not show_warn: continue
                    if is_debug and not show_debug: continue
                    if is_info and not show_info: continue

                    if is_error: fmt = fmt_error
                    elif is_warn: fmt = fmt_warn
                    elif is_debug: fmt = fmt_debug
                    else: fmt = fmt_info
                    
                    cursor.insertText(line, fmt)
            cursor.endEditBlock()
        except Exception as e:
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
            except Exception as e:
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
                        if file.endswith('.log') or file.endswith('.txt'):
                            full_file_path = os.path.join(root, file)
                            arcname = os.path.relpath(full_file_path, log_dir)
                            zipf.write(full_file_path, arcname)
                            
            QMessageBox.information(self, "Export Successful", f"All logs have been successfully bundled and exported to:\n{save_path}")
        except Exception as e:
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

    def keyPressEvent(self, event):
        """Ensure Escape dismisses LogViewerDialog (EN 301 549 11.2.1.2 - No Keyboard Trap)."""
        if event.key() == Qt.Key_Escape:
            self.accept()
            event.accept()
            return
        super().keyPressEvent(event)
