# gui_tabs.py
# This module defines the ClientTab class for managing VPN connections in a GUI application.

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from net_stats import get_tailscale_stats
from vpn_logic import (
    save_url, save_key, load_saved_url, load_saved_key, write_profile_log
)
from tailscaleclient import TailscaleClient
from datetime import datetime
from traffic_popup import TrafficPopup
from utils import format_bytes, center_window
import db_manager # Import the new database manager
from change_credentials_popup import show_change_credentials_popup
from progress_popup import ProgressPopup # Import the new ProgressPopup
from utils import add_tooltip


class ClientTab(ttk.Frame):
    def __init__(self, parent_notebook, app_instance, tab_id, tab_name):
        super().__init__(parent_notebook, padding=10) # ttk.Frame uses 'padding'
        self.app_instance = app_instance
        self.tab_id = tab_id
        self.tab_name = tab_name

        self.login_server_var = tk.StringVar(value=load_saved_url(self.tab_name))
        self.auth_key_var = tk.StringVar(value=load_saved_key(self.tab_name))
        
        # New: Input for Ping IP
        #self.ping_ip_var = tk.StringVar(value="100.64.0.3") # Default value

        self.grid_columnconfigure(0, weight=0) # Label column, no extra space
        self.grid_columnconfigure(1, weight=1) # Entry column, takes extra space

        # Row 0: Headscale Login Server URL
        
        ttk.Label(self, text="MAPView VPN URL    :").grid(row=0, column=0, sticky='w', pady=(5, 2))
        self.Entry1 = ttk.Entry(self, textvariable=self.login_server_var, font="-family {Courier New} -size 10")
        self.Entry1.grid(row=0, column=1, sticky='ew', pady=(5, 2), padx=(0, 5))
        self.Entry1.configure(state='normal')

        # Row 1: Authentication Key
        self.Entry1_1 = ttk.Entry(self, textvariable=self.auth_key_var, font="-family {Courier New} -size 10", show="*")

        # Row 2: Ping IP
        #ttk.Label(self, text="Ping Test IP        :").grid(row=2, column=0, sticky='w', pady=2)
        #self.ping_ip_entry = ttk.Entry(self, textvariable=self.ping_ip_var, font="-family {Courier New} -size 10")
        #self.ping_ip_entry.grid(row=2, column=1, sticky='ew', pady=2, padx=(0, 5))

        # Row 3: Status Label and Change Credentials Button
        self.Label2 = ttk.Label(self, text="🔴 Disconnected", foreground="red", font="-family {Segoe UI} -size 10 -weight bold", anchor='w')
        self.Label2.grid(row=3, column=0, sticky='w', pady=(5, 5))

        self.change_cred_btn = ttk.Button(
            self,
            text="Change Credentials",
            command=lambda: show_change_credentials_popup(
                self, 
                self.tab_name, 
                self.login_server_var.get(), 
                self.auth_key_var.get(), 
                self._save_new_credentials,
                bg_color=self.app_instance._bgcolor, # Pass the current theme's background color
                icon_image=getattr(self.app_instance, 'icon_image', None)
            ),
            style='ClickButton.TButton'
        )
        self.change_cred_btn.grid(row=3, column=1, sticky='e', pady=(5, 5), padx=(0, 5))


        # Row 4: Button Frame
        self.button_frame = tk.Frame(self, background=self.app_instance._bgcolor) # Use app's _bgcolor
        self.button_frame.grid(row=4, column=0, columnspan=2, sticky='ew', pady=(5, 10))

        self.vpn_action_btn = ttk.Button(
            self.button_frame,
            text="Connect",
            command=self.vpn_status_change,
            style='Connect.TButton'
        )
        self.vpn_action_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        self.show_stats_btn = ttk.Button(self.button_frame, text="Show Traffic Stats", command=self.open_traffic_popup, style='ActionButton.TButton')
        self.show_stats_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        # Status labels for traffic
        self.traffic_label = ttk.Label(self, text="Traffic: Sent 0 B / Received 0 B", font="-family {Courier New} -size 9", anchor='w')
        self.traffic_label.grid(row=5, column=0, columnspan=2, sticky='w')

        # Initialize the progress popup
        self.progress_popup = ProgressPopup(self.master.master)
        self.progress_popup.withdraw() # Ensure it's hidden initially


        self.prev_stats = None
        self._monitoring = False

        # Tooltips for entries and buttons
        add_tooltip(self.Entry1, "Enter your VPN URL (e.g. https://vpn.example.com)", self)
        add_tooltip(self.Entry1_1, "Enter the authentication key", self)
        #add_tooltip(self.vpn_action_btn, "Connect or Logout from VPN", self)
        add_tooltip(self.change_cred_btn, "Change VPN Settings", self)
        add_tooltip(self.show_stats_btn, "View Network stats", self)
        add_tooltip(self.Label2, "VPN connection status", self)
        add_tooltip(self.traffic_label, "Live traffic data (updated every 3 seconds)", self)
        add_tooltip(self.vpn_action_btn, "Connect to VPN", self)

        # Pass callbacks to TailscaleClient
        self.client = TailscaleClient(
            output_callback=self._print_output,
            status_callback=self._update_status_label,
            connected_callback=self._post_connect_ui,
            logged_out_callback=self.notify_app_logged_out,
            post_disconnect_callback=self._post_disconnect_ui,
            post_logout_callback=self._post_logout_ui,
            progress_callback=self._update_progress_label,
            message_popup_callback=self._show_messagebox_popup # Pass new callback
        )

        # Initial state setup
        if self.auth_key_var.get() and self.login_server_var.get():
            self.vpn_action_btn.configure(state='normal')
        else:
            self.vpn_action_btn.configure(state='disabled')  # ✅ Prevent re-click
            self.vpn_action_btn.update_idletasks()  # Optional: visually reflects the state immediately

        
        self._update_change_credentials_button_state()

    def _show_messagebox_popup(self, title, message):
        """Callback to show a standard Tkinter messagebox as a popup."""
        messagebox.showinfo(title, message)

    def on_change_credentials_click(self):
        from change_credentials_popup import show_change_credentials_popup

        show_change_credentials_popup(
            master=self,
            tab_name=self.tab_name,
            current_url=self._get_saved_url(),
            current_key=self._get_saved_key(),
            save_callback=self._save_credentials,
            icon_image=self.master.icon_image if hasattr(self.master, "icon_image") else None
        )

    def is_sso_mode(self):
        from vpn_logic import get_file_path
        import os
    
        mode_file = get_file_path("auth_mode", self.tab_name)
        if os.out_exists(mode_file):
            with open(mode_file, "r") as f:
                return f.read().strip() == "google"
        return False  # Default to auth key mode


    def _save_credentials(self, url, key, mode):
        from vpn_logic import save_url, save_key, write_log, get_file_path

        save_url(url, self.tab_name)
        save_key(key, self.tab_name)

        # Save the auth mode to a file
        try:
            mode_file = get_file_path("auth_mode", self.tab_name)
            with open(mode_file, "w") as f:
                f.write(mode)
        except Exception as e:
            write_log(f"Error saving auth mode for '{self.tab_name}': {e}", level="ERROR")


    def vpn_status_change(self):
        if self.client.connected:
            self.on_disconnect_and_cleanup()
        else:
            self.on_connect()

    def _print_output(self, text):
        pass

    def _update_status_label(self, text, color):
        self.Label2.configure(text=text, foreground=color)
        
        # Re-enable Connect button on any state change
        if any(x in text.lower() for x in ["connected", "disconnected", "error", "failed"]):
            self.vpn_action_btn.configure(state='normal')

    def _update_progress_label(self, message, step):
        """Updates the progress popup with message and adds a checkmark if step is complete."""
        self.progress_popup.show_progress(message, step)

    def _post_connect_ui(self):
        self.vpn_action_btn.configure(text="Logout", style='Logout.TButton')
        self.vpn_action_btn.tooltip_label.config(text="Disconnect and Logout from VPN")
        self.Entry1.configure(state='disabled')
        self.Entry1_1.configure(state='disabled')
        #self.ping_ip_entry.configure(state='disabled') # Keep disabled after connect
        self.app_instance.set_connected_tab(self.tab_id)
        self._update_change_credentials_button_state()

    def on_connect(self):
        server = self.login_server_var.get().strip()
        key = self.auth_key_var.get().strip()

        self.Entry1.configure(state='disabled')
        self.Entry1_1.configure(state='disabled')
        self.vpn_action_btn.configure(state='disabled')  # ✅ Prevent re-click
        self.vpn_action_btn.update_idletasks()  # Optional: visually reflects the state immediately

        self._update_change_credentials_button_state()

        # Start Tailscale connection
        self.client.connect(key, server, self.tab_name)

        from net_stats import get_tailscale_stats
        self.prev_stats = get_tailscale_stats()
        self._monitoring = True
        threading.Thread(target=self._monitor_traffic_loop, daemon=True).start()


        
    def _post_disconnect_ui(self):
        self.vpn_action_btn.configure(state='normal')
        self.Entry1.configure(state='normal')
        self.Entry1_1.configure(state='normal')
        #self.ping_ip_entry.configure(state='normal') # Enable ping IP entry on disconnect
        if self.app_instance.connected_tab_id == self.tab_id:
            self.app_instance.clear_connected_tab()
        self._update_change_credentials_button_state()
        self.prev_stats = None

    def on_logout(self):
        self.on_disconnect_and_cleanup()

    def on_disconnect_and_cleanup(self):
        self.vpn_action_btn.configure(state='disabled')  # ✅ Prevent re-click
        self.vpn_action_btn.update_idletasks()  # Optional: visually reflects the state immediately

        self.client.disconnect(self.tab_name)

    def _post_logout_ui(self):
        self.vpn_action_btn.configure(text="Connect", style='Connect.TButton')
        self.vpn_action_btn.tooltip_label.config(text="Connect to VPN")
        self.Entry1.configure(state='normal')
        self.Entry1_1.configure(state='normal')
        #self.ping_ip_entry.configure(state='normal') # Enable ping IP entry on logout
        self.Label2.configure(text="🔴 Disconnected", foreground="red")
        if self.app_instance.connected_tab_id == self.tab_id:
            self.app_instance.clear_connected_tab()
        self._update_change_credentials_button_state()

    def _save_new_credentials(self, new_url, new_key, mode):
        save_url(new_url, self.tab_name)
        save_key(new_key, self.tab_name)
        self.login_server_var.set(new_url)
        self.auth_key_var.set(new_key)

        # Save auth mode (google or auth_key)
        from vpn_logic import get_file_path, write_log
        try:
            mode_file = get_file_path("auth_mode", self.tab_name)
            with open(mode_file, "w") as f:
                f.write(mode)
        except Exception as e:
            write_log(f"Error saving auth mode for '{self.tab_name}': {e}", level="ERROR")

        if new_url and (new_key or mode == "google"):
            self.vpn_action_btn.configure(state='normal')
        else:
            self.vpn_action_btn.configure(state='disabled')  # ✅ Prevent re-click
            self.vpn_action_btn.update_idletasks()  # Optional: visually reflects the state immediately



    def _update_change_credentials_button_state(self):
        if not self.client.connected and not self.client.logged_in:
            self.change_cred_btn.grid(row=3, column=1, sticky='e', pady=(5, 5), padx=(0, 5))
            self.change_cred_btn.configure(state='normal')
            self.Entry1.configure(state='disabled')
            self.Entry1_1.configure(state='normal')
            #self.ping_ip_entry.configure(state='normal') # Keep enabled when change creds is shown
        else:
            self.change_cred_btn.grid_forget()
            self.Entry1.configure(state='disabled')
            self.Entry1_1.configure(state='disabled')
            #self.ping_ip_entry.configure(state='disabled') # Disable when change creds is hidden


    def disable_tab_ui(self):
        self.Entry1.configure(state='disabled')
        self.Entry1_1.configure(state='disabled')
        #self.ping_ip_entry.configure(state='disabled') # Disable ping IP entry
        self.vpn_action_btn.configure(state='disabled')  # ✅ Prevent re-click
        self.vpn_action_btn.update_idletasks()  # Optional: visually reflects the state immediately

        self._update_change_credentials_button_state()

    def enable_tab_ui(self):
        if self.client.connected:
            self.vpn_action_btn.configure(
                text='Logout',
                style='Logout.TButton',
                state='normal'
            )

        elif self.client.logged_in:
            self.vpn_action_btn.configure(
                text='Connect',
                style='Connect.TButton',
                state='normal'
            )

        else:
            self.vpn_action_btn.configure(
                text='Connect',
                style='Connect.TButton',
                state='normal'
            )
            # Only enable these if not connected/logged in
            self.Entry1.configure(state='normal')
            self.Entry1_1.configure(state='normal')
            #self.ping_ip_entry.configure(state='normal')


        self._update_change_credentials_button_state()

    def notify_app_logged_out(self):
        self.app_instance.clear_connected_tab()
        self.enable_tab_ui()
  
    def open_traffic_popup(self):
        if not self.client.connected:
            messagebox.showinfo("VPN Status", "VPN is not connected.")
            return

        # Pass the current app's background color to the popup
        TrafficPopup(self.master.master, self.prev_stats, self.tab_name)
        self.prev_stats = get_tailscale_stats()

    def _monitor_traffic_loop(self):
        while self._monitoring:
            stats = get_tailscale_stats()
            if stats and self.prev_stats:
                sent = stats.bytes_sent - self.prev_stats.bytes_sent
                recv = stats.bytes_recv - self.prev_stats.bytes_recv
                self.traffic_label.config(text=f"Traffic: Sent {format_bytes(sent)} / Received {format_bytes(recv)}")
            time.sleep(3)
