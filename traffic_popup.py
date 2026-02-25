# traffic_popup.py
# This module defines the TrafficPopup class, which displays traffic statistics in a popup window.

import tkinter as tk
from tkinter import ttk
from net_stats import get_tailscale_stats
from utils import format_bytes
from datetime import datetime
import db_manager # Import the new database manager

class TrafficPopup(tk.Toplevel):
    def __init__(self, master, prev_stats, profile_name): # Add profile_name here
        super().__init__(master)
        if hasattr(master, 'icon_image'):
            self.iconphoto(False, master.icon_image)

        self.title("Traffic Stats")
        self.geometry("220x198") # Increased height to accommodate daily total
        self.resizable(False, False)

        # Get the current background color from the master app instance
        # Assumes master.master is the root window, and it has _bgcolor attribute
        bg_color = getattr(master, '_bgcolor', "#f0f0f0") 
        self.configure(background=bg_color)

        style = ttk.Style(self)
        style.theme_use(style.theme_use()) # Re-apply current theme to this Toplevel
                                           # This ensures Custom.TLabel style is picked up

        # Customize ttk.Label style (will be picked up from the active theme)
        style.configure("Custom.TLabel", background=bg_color)

        self.prev_stats = prev_stats
        self.current_stats = get_tailscale_stats()
        self.profile_name = profile_name # Store the profile name
        
        ttk.Label(self, text="Traffic Statistics", font=("Segoe UI", 10, "bold"),
                  style="Custom.TLabel").pack(pady=(10, 5))

        self.label = ttk.Label(self, text="", font=("Courier New", 9),
                               anchor='w', justify='left', style="Custom.TLabel")
        self.label.pack(padx=20)

        # Label for daily total traffic
        self.daily_total_label = ttk.Label(self, text="", font=("Courier New", 9, "bold"),
                                           anchor='w', justify='left', style="Custom.TLabel", foreground="blue")
        self.daily_total_label.pack(padx=20, pady=(5, 10))

        self.show_stats()

        # Add a Close button
        self.close_button = ttk.Button(self, text="Close", command=self.destroy, style='ActionButton.TButton')
        self.close_button.pack(pady=10) # Add some padding


    def show_stats(self):
        if not self.current_stats:
            self.label.config(text="No traffic data available.")
            self.daily_total_label.config(text="")
            return

        # Log current cumulative stats to the database
        db_manager.insert_traffic_data(self.profile_name, self.current_stats.bytes_sent, self.current_stats.bytes_recv)

        if not self.prev_stats:
            self.label.config(text="No previous data to compare.")
            self.daily_total_label.config(text="")
            return

        sent = self.current_stats.bytes_sent - self.prev_stats.bytes_sent
        recv = self.current_stats.bytes_recv - self.prev_stats.bytes_recv

        formatted_sent = format_bytes(sent)
        formatted_recv = format_bytes(recv)
        formatted_total_sent = format_bytes(self.current_stats.bytes_sent)
        formatted_total_recv = format_bytes(self.current_stats.bytes_recv)

        # Get daily total from DB
        daily_sent, daily_recv = db_manager.get_daily_total_traffic(self.profile_name)
        formatted_daily_sent = format_bytes(daily_sent)
        formatted_daily_recv = format_bytes(daily_recv)

        stats_text = (
            f"Sent (Current): {formatted_sent}\n"
            f"Recv (Current): {formatted_recv}\n"
            f"Total Sent    : {formatted_total_sent}\n"
            f"Total Recv    : {formatted_total_recv}"
        )
        self.label.config(text=stats_text)

        daily_total_text = (
            f"Daily Sent    : {formatted_daily_sent}\n"
            f"Daily Recv    : {formatted_daily_recv}"
        )
        self.daily_total_label.config(text=daily_total_text)
