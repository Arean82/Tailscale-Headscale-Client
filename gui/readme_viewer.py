# gui/readme_viewer.py
# This module defines the ReadmeViewer class, which displays the contents of the README.md file in a simple window. It reads the README.md file from the root of the project and shows it in a scrollable text area with basic formatting for headers and code blocks.  

import customtkinter as ctk
import tkinter as tk
import os
import re
from .common import COLORS, FONTS

class ReadmeViewer(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("README")
        self.geometry("800x600")
        
        # Ensure window stays on top
        self.attributes("-topmost", True)
        self.lift()
        self.focus_force()
        self.after(10, lambda: self.transient(parent))

        # Container Frame
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

        self._setup_tags()
        self.load_readme()
        
        ctk.CTkButton(self, text="Close", command=self.destroy, width=120, fg_color=COLORS["accent"]).pack(pady=10)

    def _setup_tags(self):
        base_font = FONTS["body"][0]
        base_size = FONTS["body"][1]
        # Header Tags
        self.text_area.tag_configure("h1", font=(base_font, base_size + 12, "bold"), foreground=COLORS["blue"])
        self.text_area.tag_configure("h2", font=(base_font, base_size + 6, "bold"), foreground=COLORS["green"])
        self.text_area.tag_configure("h3", font=(base_font, base_size + 2, "bold"), foreground=COLORS["gold"])
        # Body and Inline Tags
        self.text_area.tag_configure("bold", font=(base_font, base_size, "bold"), foreground="#FFFFFF")
        self.text_area.tag_configure("code_block", font=FONTS["mono"], background="#252526", foreground=COLORS["orange"])

    def load_readme(self):
        # Correct path to root from gui/ folder
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "README.md"))
        if not os.path.exists(path):
            self.text_area.insert("1.0", "README.md not found.")
            return

        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line in lines:
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

        # Apply bold formatting for **text**
        self._parse_bold_tags()
        self.text_area.configure(state="disabled")

    def _parse_bold_tags(self):
        """Finds **text** patterns and applies the 'bold' tag while removing the asterisks."""
        while True:
            idx = self.text_area.search(r"\*\*(.*?)\*\*", "1.0", stopindex="end", regexp=True)
            if not idx: break
            
            # Find exact end of the match
            match_text = self.text_area.get(idx, f"{idx} lineend")
            match_obj = re.search(r"\*\*(.*?)\*\*", match_text)
            if not match_obj: break
            
            content = match_obj.group(1)
            full_match_len = len(match_obj.group(0))
            
            # Delete the **content** and insert content with bold tag
            self.text_area.delete(idx, f"{idx}+{full_match_len}c")
            self.text_area.insert(idx, content, "bold")