# gui/license_viewer.py
# This module defines the LicenseViewer class, which displays the contents of the LICENSE file in a simple window. It reads the LICENSE file from the root of the project and shows it in a scrollable text area.   

import customtkinter as ctk
import os

class LicenseViewer(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("License")
        self.geometry("500x400")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        
        self.lift()
        self.focus_force()
        self.after(10, lambda: self.transient(parent))

        self.text_area = ctk.CTkTextbox(
            self, 
            fg_color="#1e1e1e", 
            text_color="#d4d4d4", 
            wrap="word"
        )
        self.text_area.pack(fill="both", expand=True, padx=10, pady=(10, 5))

        self.load_license()
        
        ctk.CTkButton(self, text="Close", command=self.destroy, width=120, fg_color="#007acc").pack(pady=10)

    def load_license(self):
        # Step out of /gui/ to the root to find LICENSE
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        path = os.path.join(base_dir, "LICENSE")
        
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self.text_area.insert("1.0", f.read())
        else:
            self.text_area.insert("1.0", "LICENSE file not found in root directory.")
            
        self.text_area.configure(state="disabled")