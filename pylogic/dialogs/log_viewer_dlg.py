# pylogic/dialogs/log_viewer_dlg.py
# PySide6 port of gui/log_viewer.py

import os

from PySide6.QtWidgets import QDialog, QVBoxLayout, QMessageBox
from PySide6.QtGui import QTextCharFormat, QColor, QTextCursor
from PySide6.QtCore import Qt

from pylogic.ui_helpers import load_ui
from logic.logger import get_global_log_dir


class LogViewerDialog(QDialog):
    def __init__(self, parent=None, filename="", display_title=""):
        super().__init__(parent)

        self.log_file         = os.path.join(get_global_log_dir(), filename)
        self.display_title    = display_title
        self._last_search_pos = 0   # cursor position for incremental search

        self.ui = load_ui("pygui/dialogs/log_viewer.ui", parent=self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)

        self.setWindowTitle(f"Log: {display_title}")
        self.resize(820, 660)

        # Widget refs
        self.labelTitle  = self.ui.labelTitle
        self.searchEntry = self.ui.searchEntry
        self.btnSearch   = self.ui.btnSearch
        self.btnClear    = self.ui.btnClear
        self.btnRefresh  = self.ui.btnRefresh
        self.textWidget  = self.ui.textWidget

        self.labelTitle.setText(display_title)

        # Connections
        self.btnSearch.clicked.connect(self._search_text)
        self.searchEntry.returnPressed.connect(self._search_text)
        self.btnRefresh.clicked.connect(self._read_content)
        self.btnClear.clicked.connect(self._clear_log)

        self._read_content()

    # ------------------------------------------------------------------

    def _read_content(self):
        self.textWidget.clear()
        self._last_search_pos = 0

        if not os.path.exists(self.log_file):
            self.textWidget.setPlainText(
                f"[Log file not found or logging is disabled:\n{self.log_file}]"
            )
            return

        # Colour formats
        fmt_info    = QTextCharFormat()
        fmt_info.setForeground(QColor("#4CAF50"))
        fmt_warn    = QTextCharFormat()
        fmt_warn.setForeground(QColor("#FFC107"))
        fmt_error   = QTextCharFormat()
        fmt_error.setForeground(QColor("#F44336"))
        fmt_default = QTextCharFormat()

        cursor = self.textWidget.textCursor()

        try:
            with open(self.log_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    up = line.upper()
                    if "ERROR" in up:
                        fmt = fmt_error
                    elif "WARNING" in up:
                        fmt = fmt_warn
                    elif "INFO" in up:
                        fmt = fmt_info
                    else:
                        fmt = fmt_default
                    cursor.insertText(line, fmt)
        except Exception as e:
            cursor.insertText(f"Failed to read log: {e}")

        # Auto-scroll to end
        self.textWidget.moveCursor(QTextCursor.End)

    def _search_text(self):
        query = self.searchEntry.text()
        if not query:
            return

        # Search forward from current position; wrap around if not found
        found = self.textWidget.find(query)
        if not found:
            # Wrap: move to top and try again
            self.textWidget.moveCursor(QTextCursor.Start)
            self.textWidget.find(query)

    def _clear_log(self):
        reply = QMessageBox.question(
            self, "Confirm", "Clear this log file?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                open(self.log_file, "w").close()
                self._read_content()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
