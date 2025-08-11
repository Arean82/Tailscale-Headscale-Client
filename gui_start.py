from tkinter import Tk, PhotoImage
import tkinter as tk
import sys 
import os
from config import APP_DATA_DIR, LOG_DIR
from utils import write_log, center_window
from vpn_logic import load_last_selected_tab_id, initialize_app_storage
from gui_main import TabbedClientApp

def start_gui():
    print("[DEBUG] >> start_gui called")
    initialize_app_storage()
    print("[DEBUG] >> storage initialized")

    root = tk.Tk()
    root.title("Tailscale VPN Client")
    root.geometry("400x300+100+100")  # Force the window on-screen
    print("[DEBUG] >> root window created")

    try:
        # Use absolute path relative to this script
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        bundled_icon_path = os.path.join(base_dir, "icon.png")

        if os.path.exists(bundled_icon_path):
            icon_image = PhotoImage(file=bundled_icon_path)
            root.iconphoto(False, icon_image)
            root.icon_image = icon_image  # Preserve reference
        else:
            write_log(f"Icon file not found for Tkinter window: {bundled_icon_path}", level="WARNING")
    except Exception as e:
        write_log(f"Error setting Tkinter window icon: {e}", level="ERROR")

    app = TabbedClientApp(root)
    print("[DEBUG] >> TabbedClientApp initialized")

    # Restore last selected tab
    last_tab_id = load_last_selected_tab_id()
    if last_tab_id is not None and last_tab_id in app.tabs:
        for tab_index, tab_frame_id in enumerate(app.notebook.tabs()):
            tab_widget = app.notebook.nametowidget(tab_frame_id)
            if hasattr(tab_widget, 'tab_id') and tab_widget.tab_id == last_tab_id:
                app.notebook.select(tab_frame_id)
                app.update_tab_states()
                # Auto-connect if the tab has connect_vpn
                if hasattr(tab_widget, "connect_vpn"):
                    root.after(500, tab_widget.connect_vpn)
                break
    else:
        if app.notebook.tabs():
            first_tab_widget = app.notebook.nametowidget(app.notebook.tabs()[0])
            app.notebook.select(app.notebook.tabs()[0])
            app.update_tab_states()
            # Auto-connect on first tab
            if hasattr(first_tab_widget, "connect_vpn"):
                root.after(500, first_tab_widget.connect_vpn)

    root.protocol("WM_DELETE_WINDOW", app.on_close_app)
    print("[DEBUG] >> Entering mainloop")
    root.mainloop()
    print("[DEBUG] >> GUI exited")

