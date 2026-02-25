# gui/traffic_popup.py
# This module defines the TrafficPopup class, which displays traffic statistics in a popup window.

import tkinter as tk
import customtkinter as ctk
from logic.net_stats import get_tailscale_stats
from gui.utils import format_bytes
from datetime import datetime
from logic import db_manager # Import the new database manager

class TrafficPopup(ctk.CTkToplevel):
    def __init__(self, master, prev_stats, profile_name): # Add profile_name here
        super().__init__(master)
        if hasattr(master, 'icon_image'):
            self.iconphoto(False, master.icon_image)

        self.title("Traffic Stats")
        self.geometry("240x220") # Adjusted slightly for CTk padding
        self.resizable(False, False)

        self.attributes("-topmost", True)

        self.prev_stats = prev_stats
        self.current_stats = get_tailscale_stats()
        self.profile_name = profile_name # Store the profile name
        
        ctk.CTkLabel(self, text="Traffic Statistics", font=("Segoe UI", 12, "bold")).pack(pady=(10, 5))

        self.label = ctk.CTkLabel(self, text="", font=("Courier New", 11),
                               anchor='w', justify='left')
        self.label.pack(padx=20)

        # Label for daily total traffic
        self.daily_total_label = ctk.CTkLabel(self, text="", font=("Courier New", 11, "bold"),
                                           anchor='w', justify='left', text_color="#3b8ed0")
        self.daily_total_label.pack(padx=20, pady=(5, 10))

        self.show_stats()

        # Add a Close button
        self.close_button = ctk.CTkButton(self, text="Close", command=self.destroy, width=100)
        self.close_button.pack(pady=10) 


    def show_stats(self):
        if not self.current_stats:
            self.label.configure(text="No traffic data available.")
            self.daily_total_label.configure(text="")
            return

        # Log current cumulative stats to the database
        db_manager.insert_traffic_data(self.profile_name, self.current_stats.bytes_sent, self.current_stats.bytes_recv)

        if not self.prev_stats:
            self.label.configure(text="No previous data to compare.")
            self.daily_total_label.configure(text="")
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
        self.label.configure(text=stats_text)

        daily_total_text = (
            f"Daily Sent    : {formatted_daily_sent}\n"
            f"Daily Recv    : {formatted_daily_recv}"
        )
        self.daily_total_label.configure(text=daily_total_text)