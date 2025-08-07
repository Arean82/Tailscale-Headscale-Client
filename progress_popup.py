import tkinter as tk
from tkinter import ttk

class ProgressPopup(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.overrideredirect(True)  # Remove window decorations (title bar, borders)
        self.attributes("-topmost", True)  # Keep the window on top of others

        self.geometry("+0+0") # Initial position, will be updated later

        self.frame = ttk.Frame(self, padding="5 5 5 5", relief="raised")
        self.frame.pack(expand=True, fill="both")

        self.label = ttk.Label(self.frame, text="", font=("Segoe UI", 9), foreground="blue")
        self.label.pack(padx=10, pady=5)

        self.update_id = None # To store the ID for after method to clear text

        self.withdraw() # Hide initially

    def show_progress(self, message, step):
        """
        Updates the progress popup with a message and a checkmark if done.
        :param message: The message to display.
        :param step: 1 for in-progress (dot), 2 for complete (checkmark), 0 to clear.
        """
        if self.update_id:
            self.after_cancel(self.update_id)
            self.update_id = None

        if step == 0: # Clear message
            self.label.config(text="", foreground="blue")
            self.withdraw() # Hide the popup
            return

        self.deiconify() # Show the popup
        self.lift() # Bring to front

        if step == 1: # In progress
            self.label.config(text=f"• {message}", foreground="blue")
        elif step == 2: # Completed
            self.label.config(text=f"✔ {message}", foreground="green")
            # Automatically hide the popup after a short delay for completed messages
            self.update_id = self.after(2000, self.withdraw)

        self._position_popup()

    def _position_popup(self):
        """Positions the popup in the bottom right corner of the parent window."""
        parent_x = self.master.winfo_x()
        parent_y = self.master.winfo_y()
        parent_width = self.master.winfo_width()
        parent_height = self.master.winfo_height()

        self.update_idletasks() # Ensure geometry is calculated

        popup_width = self.winfo_width()
        popup_height = self.winfo_height()

        # Position in bottom-right of the parent
        x = parent_x + parent_width - popup_width - 20 # 20 pixels padding from right
        y = parent_y + parent_height - popup_height - 20 # 20 pixels padding from bottom

        self.geometry(f"+{x}+{y}")

    def hide(self):
        self.withdraw()

    def destroy(self):
        if self.update_id:
            self.after_cancel(self.update_id)
        super().destroy()