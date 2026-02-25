# gui/settings.py
# This module provides a dedicated settings window for the MAPView VPN Client using CustomTkinter.

import tkinter as tk
import customtkinter as ctk
from logic.vpn_logic import load_settings, save_settings

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master, icon_image=None):
        super().__init__(master)
        
        self.title("Settings")
        self.geometry("240x120")
        self.resizable(False, False)
        
        # Keep window on top and grab focus
        self.attributes("-topmost", True)
        self.grab_set()
        
        if icon_image:
            self.iconphoto(False, icon_image)

        # Original logic for loading settings
        self.settings = load_settings()
        self.auto_connect_var = tk.BooleanVar(value=self.settings.get("auto_connect", False))

        self._create_widgets()

    def _create_widgets(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(expand=True, fill="both", padx=20, pady=10)

        # Checkbox logic
        self.chk = ctk.CTkCheckBox(
            container, 
            text="Enable Auto-connect", 
            variable=self.auto_connect_var, 
            command=self._on_toggle
        )
        self.chk.pack(pady=(10, 20))

        # Close button
        self.close_btn = ctk.CTkButton(
            container, 
            text="Close", 
            command=self.destroy,
            width=100
        )
        self.close_btn.pack()

    def _on_toggle(self):
        # Original logic for saving toggled settings
        self.settings["auto_connect"] = self.auto_connect_var.get()
        save_settings(self.settings)

def show_settings(master, icon_image=None):
    return SettingsWindow(master, icon_image)