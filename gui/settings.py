# gui/settings.py
# This module provides a dedicated settings window for the TAILSCALE VPN Client using CustomTkinter.

import tkinter as tk
import customtkinter as ctk
import os
import sys
import subprocess
from tkinter import messagebox

from logic.vpn_logic import load_settings, save_settings

# Import both the directory getter AND the setup function we just created
from logic.logger import get_global_log_dir, refresh_all_loggers, clear_global_logs

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master, icon_image=None):
        super().__init__(master)
        self.transient(master)
        self.title("Settings")
        self.geometry("320x220") 
        self.resizable(False, False)
        
        self.attributes("-topmost", True)
        self.grab_set()
        
        if icon_image:
            self.iconphoto(False, icon_image)

        self.settings = load_settings()
        self.auto_connect_var = tk.BooleanVar(value=self.settings.get("auto_connect", False))
        self.enable_logs_var = tk.BooleanVar(value=self.settings.get("enable_logs", False))

        self._create_widgets()

    def _create_widgets(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(expand=True, fill="both", padx=20, pady=10)

        self.chk = ctk.CTkCheckBox(
            container, 
            text="Enable Auto-connect", 
            variable=self.auto_connect_var, 
            command=self._on_toggle
        )
        self.chk.pack(pady=(5, 10))

        self.log_chk = ctk.CTkCheckBox(
            container, 
            text="Enable Global App Logs", 
            variable=self.enable_logs_var, 
            command=self._on_log_toggle
        )
        self.log_chk.pack(pady=(5, 5))

        self.log_details_frame = ctk.CTkFrame(container, fg_color="transparent")
        
        self.current_log_dir = get_global_log_dir()
        
        self.log_path_label = ctk.CTkLabel(
            self.log_details_frame, 
            text=f"Path: {self.current_log_dir}", 
            font=("Arial", 10),
            text_color="gray",
            wraplength=280
        )
        self.log_path_label.pack(pady=(0, 5))

        self.open_log_btn = ctk.CTkButton(
            self.log_details_frame, 
            text="Open Log Folder", 
            command=self._open_log_folder,
            height=24,
            width=120
        )
        self.open_log_btn.pack(pady=(0, 10))

        self._update_log_ui()

        self.close_btn = ctk.CTkButton(
            container, 
            text="Close", 
            command=self.destroy,
            width=100
        )
        self.close_btn.pack(side="bottom", pady=(10, 0))

    def _on_toggle(self):
        self.settings["auto_connect"] = self.auto_connect_var.get()
        save_settings(self.settings)

    def _on_log_toggle(self):
        # If the user is unchecking the box (turning logs off)
        if not self.enable_logs_var.get():
            confirm = messagebox.askokcancel(
                "Disable & Delete Logs", 
                "Disabling logs will permanently delete all existing log files in the GlobalLogs folder.\n\nAre you sure you want to proceed?"
            )            
            if not confirm:
                # User clicked Cancel. Revert the checkbox back to checked.
                self.enable_logs_var.set(True)
                return  # Stop execution here
                
            # If user clicked OK, safely release and delete the files
            clear_global_logs()

        # 1. Save the new setting to the JSON file
        self.settings["enable_logs"] = self.enable_logs_var.get()
        save_settings(self.settings)
        
        # 2. Update the UI to show/hide the path and button
        self._update_log_ui()
        
        # 3. Reload all global loggers immediately
        refresh_all_loggers()

    def _update_log_ui(self):
        if self.enable_logs_var.get():
            self.log_details_frame.pack(fill="x")
        else:
            self.log_details_frame.pack_forget()

    def _open_log_folder(self):
        if sys.platform == "win32":
            os.startfile(self.current_log_dir)
        elif sys.platform == "darwin":  
            subprocess.Popen(["open", self.current_log_dir])
        else:  
            subprocess.Popen(["xdg-open", self.current_log_dir])

    
    

def show_settings(master, icon_image=None):
    return SettingsWindow(master, icon_image)