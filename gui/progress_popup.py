# gui/progress_popup.py

import tkinter as tk
import customtkinter as ctk # Migrate to CustomTkinter

class ProgressPopup(ctk.CTkToplevel): # Inherit from CTkToplevel
    def __init__(self, parent):
        super().__init__(parent)
        self.overrideredirect(True)
        self.attributes("-topmost", True)

        self.geometry("+0+0") 

        # CTkFrame handles colors via fg_color, not styles
        self.frame = ctk.CTkFrame(self, corner_radius=10, border_width=2)
        self.frame.pack(expand=True, fill="both")

        # Use text_color instead of foreground
        self.label = ctk.CTkLabel(self.frame, text="", font=("Segoe UI", 11), text_color="#3b8ed0")
        self.label.pack(padx=10, pady=5)

        self.update_id = None 

        self.withdraw() 

    def show_progress(self, message, step):
        """
        Updates the progress popup with a message and a checkmark if done.
        """
        if self.update_id:
            self.after_cancel(self.update_id)
            self.update_id = None

        if step == 0: 
            # Use configure instead of config
            self.label.configure(text="", text_color="#3b8ed0")
            self.withdraw() 
            return

        self.deiconify() 
        self.lift() 

        if step == 1: # In progress
            self.label.configure(text=f"• {message}", text_color="#3b8ed0")
        elif step == 2: # Completed
            self.label.configure(text=f"✔ {message}", text_color="#2eb82e")
            self.update_id = self.after(2000, self.withdraw)

        self._position_popup()

    def _position_popup(self):
        """Positions the popup in the bottom right corner of the parent window."""
        parent_x = self.master.winfo_x()
        parent_y = self.master.winfo_y()
        parent_width = self.master.winfo_width()
        parent_height = self.master.winfo_height()

        self.update_idletasks() 

        popup_width = self.winfo_width()
        popup_height = self.winfo_height()

        # Position in bottom-right of the parent
        x = parent_x + parent_width - popup_width - 20 
        y = parent_y + parent_height - popup_height - 20 

        self.geometry(f"+{x}+{y}")

    def hide(self):
        self.withdraw()

    def destroy(self):
        if self.update_id:
            self.after_cancel(self.update_id)
        super().destroy()