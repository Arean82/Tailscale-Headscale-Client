# gui/readme_viewer.py
# This module defines the ReadmeViewer class, which displays the contents of the README.md file in a simple window. It reads the README.md file from the root of the project and shows it in a scrollable text area with basic formatting for headers and code blocks.  

import customtkinter as ctk
import tkinter as tk
import os
from .common import COLORS, FONTS # Use relative import

class ReadmeViewer(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("README")
        self.geometry("800x600")
        self.resizable(False, False)
        
        # Keep window on top
        self.attributes("-topmost", True)
        self.lift()
        self.focus_force()

        frame = ctk.CTkFrame(self, fg_color=COLORS["bg_dark"])
        frame.pack(fill="both", expand=True, padx=10, pady=(10, 5))

        self.text_area = tk.Text(
            frame, 
            bg=COLORS["bg_dark"], 
            fg=COLORS["fg_light"], 
            font=FONTS["body"], 
            wrap="word",
            bd=0, highlightthickness=0, padx=20, pady=20
        )
        self.text_area.pack(side="left", fill="both", expand=True)
        
        scrollbar = ctk.CTkScrollbar(frame, command=self.text_area.yview)
        scrollbar.pack(side="right", fill="y")
        self.text_area.configure(yscrollcommand=scrollbar.set)

        self._setup_markdown_tags()
        self.load_readme()
        
        ctk.CTkButton(self, text="Close", command=self.destroy, width=120, fg_color=COLORS["accent"]).pack(pady=10)

    def _setup_markdown_tags(self):
        base_f = FONTS["body"][0]
        base_s = FONTS["body"][1]
        self.text_area.tag_configure("h1", font=(base_f, base_s + 12, "bold"), foreground=COLORS["blue"])
        self.text_area.tag_configure("h2", font=(base_f, base_s + 6, "bold"), foreground=COLORS["green"])
        self.text_area.tag_configure("h3", font=(base_f, base_s + 2, "bold"), foreground=COLORS["gold"])
        self.text_area.tag_configure("bold", font=(base_f, base_s, "bold"), foreground="white")

    def load_readme(self):
        # Look for README.md in root (one level up)
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "README.md"))
        
        if not os.path.exists(path):
            self.text_area.insert("1.0", "README.md not found in root directory.")
            return

        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("### "):
                    self.text_area.insert("end", stripped[4:] + "\n", "h3")
                elif stripped.startswith("## "):
                    self.text_area.insert("end", stripped[3:] + "\n", "h2")
                elif stripped.startswith("# "):
                    self.text_area.insert("end", stripped[2:] + "\n", "h1")
                elif stripped.startswith("* "):
                    self.text_area.insert("end", " • " + stripped[2:] + "\n")
                else:
                    self.text_area.insert("end", line)
        
        self.text_area.configure(state="disabled")