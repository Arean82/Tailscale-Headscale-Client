# gui/gui_start.py

from tkinter import PhotoImage
import customtkinter as ctk # Migrate to CustomTkinter
import tkinter as tk
import sys 
import os
from config import APP_DATA_DIR, LOG_DIR
from gui.utils import write_log, center_window
from logic.vpn_logic import load_last_selected_tab_id, initialize_app_storage
from gui.gui_main import TabbedClientApp

def start_gui():
    print("[DEBUG] >> start_gui called")
    initialize_app_storage()
    print("[DEBUG] >> storage initialized")

    # Use CTk instead of tk.Tk for full CustomTkinter compatibility
    root = ctk.CTk() 
    root.title("MAPView VPN Client")
    
    # Original logic for geometry preserved
    root.geometry("400x300+100+100")  
    print("[DEBUG] >> root window created")

    try:
        # Use absolute path relative to this script
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        bundled_icon_path = os.path.join(base_dir, "assets", "icon.png")

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

    # Restore last selected tab logic preserved 100%
    last_tab_id = load_last_selected_tab_id()

    # CustomTkinter iterate through tabs to find the one with the matching tab_id
    if last_tab_id is not None and last_tab_id in app.tabs:
        tab_instance = app.tabs[last_tab_id]
        tab_name = tab_instance.tab_name
        app.tabview.set(tab_name) # Select the tab
        app.update_tab_states()
        
        # Auto-connect if applicable
        if hasattr(tab_instance, "vpn_status_change"):
            root.after(500, tab_instance.vpn_status_change)
    else:
        # Default to the first available tab if tabs exist
        if app.tab_id_to_name:
            first_id = sorted(app.tab_id_to_name.keys())[0]
            first_name = app.tab_id_to_name[first_id]
            app.tabview.set(first_name)
            app.update_tab_states()
            
            first_tab_instance = app.tabs[first_id]
            if hasattr(first_tab_instance, "vpn_status_change"):
                root.after(500, first_tab_instance.vpn_status_change)

    root.protocol("WM_DELETE_WINDOW", app.on_close_app)
    print("[DEBUG] >> Entering mainloop")
    root.mainloop()
    print("[DEBUG] >> GUI exited")