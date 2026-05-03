# gui/tray_handler.py
# This module handles the system tray icon and menu for the application.

import threading
import pystray
from PIL import Image
import os
import sys

class TrayHandler:
    def __init__(self, app_instance, icon_path):
        self.app = app_instance
        self.icon_path = icon_path
        self.icon = None
        self._setup_tray()

    def _setup_tray(self):
        """Initializes the pystray icon and menu."""
        if not os.path.exists(self.icon_path):
            # Fallback to a simple pixel if icon not found
            image = Image.new('RGB', (64, 64), color=(73, 109, 137))
        else:
            image = Image.open(self.icon_path)

        menu = pystray.Menu(
            pystray.MenuItem("Show", self.show_window),
            pystray.MenuItem("Exit", self.exit_app)
        )

        self.icon = pystray.Icon("TailscaleClient", image, "Tailscale VPN Client", menu)

    def run(self):
        """Runs the tray icon in a separate thread."""
        threading.Thread(target=self.icon.run, daemon=True).start()

    def show_window(self, icon=None, item=None):
        """Restores the application window."""
        self.app.master.after(0, self.app.master.deiconify)
        self.app.master.after(0, self.app.master.focus_force)

    def exit_app(self, icon=None, item=None):
        """Exits the application."""
        self.icon.stop()
        self.app.master.after(0, self.app.on_close_app)

    def hide_to_tray(self):
        """Hides the main window."""
        self.app.master.withdraw()
