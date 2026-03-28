# pylogic/dialogs/progress_dlg.py
# PySide6 port of gui/progress_popup.py
# Frameless, always-on-top progress indicator anchored to the bottom-right
# of the parent window.  All show/hide is done on the GUI thread (called via
# Signal from tab_controller).

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt, QTimer


class ProgressWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Frameless, always on top, never steals focus
        self.setWindowFlags(
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        # Layout
        frame = QFrame(self)
        frame.setStyleSheet(
            "QFrame { border: 1px solid #888; border-radius: 8px; "
            "background-color: palette(window); }"
        )
        inner = QVBoxLayout(frame)
        inner.setContentsMargins(12, 6, 12, 6)

        self.label = QLabel("", frame)
        self.label.setStyleSheet("color: #3b8ed0; font-size: 11pt; border: none;")
        inner.addWidget(self.label)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(frame)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

        self.hide()

    # ------------------------------------------------------------------

    def show_progress(self, message: str, step: int) -> None:
        """
        step == 0  → hide
        step == 1  → in-progress (blue bullet)
        step == 2  → completed   (green tick, auto-hide after 2 s)
        """
        self._hide_timer.stop()

        if step == 0:
            self.hide()
            return

        if step == 1:
            self.label.setText(f"• {message}")
            self.label.setStyleSheet("color: #3b8ed0; font-size: 11pt; border: none;")
        elif step == 2:
            self.label.setText(f"✔ {message}")
            self.label.setStyleSheet("color: #2eb82e; font-size: 11pt; border: none;")
            self._hide_timer.start(2000)

        self.adjustSize()
        self._reposition()
        self.show()

    def _reposition(self) -> None:
        """Anchors the widget to the bottom-right corner of the top-level window."""
        top = self.window()
        if top is None or top is self:
            return
        geo    = top.geometry()
        pw, ph = self.width(), self.height()
        x = geo.x() + geo.width()  - pw - 20
        y = geo.y() + geo.height() - ph - 20
        self.move(x, y)

    def hide(self):
        self._hide_timer.stop()
        super().hide()
