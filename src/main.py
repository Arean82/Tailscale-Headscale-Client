import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QFile, QTextStream

from .core.manager import Manager
from .core.tailscale import TailscaleManager
from .ui.main_window import MainWindow
from .utils.logger import setup_logger

def main():
    # App Data Path
    if sys.platform == "win32":
        app_dir = os.path.join(os.environ.get('APPDATA'), "Tailscale_VPN_Client_Pro")
    else:
        app_dir = os.path.join(os.path.expanduser("~"), ".local", "share", "Tailscale_VPN_Client_Pro")
    
    os.makedirs(app_dir, exist_ok=True)
    
    # Initialize Logger
    log_file = os.path.join(app_dir, "app.log")
    logger = setup_logger("TailscaleClient", log_file)
    logger.info("Application starting...")
    
    app = QApplication(sys.argv)
    app.setApplicationName("Tailscale Client Pro")
    
    # Initialize Core
    manager = Manager(app_dir)
    ts_manager = TailscaleManager()

    
    # Initialize Main Window
    window = MainWindow(manager, ts_manager)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
