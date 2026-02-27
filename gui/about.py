# gui/about.py
# This module provides a dedicated About window for the MAPView VPN Client using CustomTkinter.

import tkinter as tk
import customtkinter as ctk

class AboutWindow(ctk.CTkToplevel):
    def __init__(self, master, icon_image=None):
        super().__init__(master)
        self.transient(master) # Ensure the About window is always on top of the main window
        
        # Original Logic: Ensure it stays on top and grabs focus
        self.attributes("-topmost", True)
        self.wm_attributes('-topmost', True)
        self.grab_set()

        if icon_image:
            self.iconphoto(False, icon_image)

        # Original UI Logic: Title and Geometry
        self.title("About Us")
        self.geometry("300x140")
        self.resizable(False, False)
        
        # Original Logic: Background color
        # Note: ctk.CTkToplevel handles its own theme, but we can set fg_color for consistency
        self.configure(fg_color="#d9d9d9")

        self._create_widgets()

    def _create_widgets(self):
        """Creates the About UI elements (Logic preserved 100%)."""
        
        # Replaces ttk.Label with CTkLabel
        ctk.CTkLabel(
            self, 
            text="MAPView VPN Client", 
            font=("Segoe UI", 11, "bold"),
            text_color="black"
        ).pack(pady=(15, 5))

        ctk.CTkLabel(
            self, 
            text="Version 3.0",
            text_color="black"
        ).pack()

        ctk.CTkLabel(
            self, 
            text="© 2025 MAPView VPN Client",
            text_color="black"
        ).pack()

        # Replaces ttk.Button with CTkButton
        # Removed 'style' argument as CTk handles styling directly
        ctk.CTkButton(
            self, 
            text="Close", 
            command=self.destroy,
            width=100
        ).pack(pady=10)

def show_about(master, icon_image=None):
    """Utility function to initialize the AboutWindow."""
    return AboutWindow(master, icon_image)