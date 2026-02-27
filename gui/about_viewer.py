# gui/about_viewer.py
# This module defines the AboutViewer class, which displays information about the MAPView VPN Client in a simple window.    

import customtkinter as ctk
from gui.common import COLORS, FONTS

class AboutViewer(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.transient(parent)    
        self.title("About Us")
        self.geometry("400x300")
        self.resizable(False, False)
        
        self.lift()
        self.focus_force()
        self.transient(parent)

        # Center Content
        self.logo_label = ctk.CTkLabel(
            self, 
            text="MAPView VPN", 
            font=(FONTS["body"][0], 24, "bold"),
            text_color=COLORS["blue"]
        )
        self.logo_label.pack(pady=(30, 10))

        self.version_label = ctk.CTkLabel(
            self, 
            text="Version 1.0.0", 
            font=FONTS["mono"]
        )
        self.version_label.pack()

        self.desc_label = ctk.CTkLabel(
            self, 
            text="A high-performance VPN client\nbuilt with Python and Tailscale.",
            font=FONTS["body"],
            justify="center"
        )
        self.desc_label.pack(pady=20)

        ctk.CTkButton(
            self, 
            text="Close", 
            command=self.destroy,
            width=100,
            fg_color=COLORS["accent"]
        ) .pack(pady=20)