# gui/gui_tabs.py
# This module defines the ClientTab class, which represents a single tab in the VPN client GUI. Each tab allows the user to connect to a VPN server, view connection status, and monitor traffic stats. The class interacts with the TailscaleClient to manage VPN connections and uses the global logger to log important events and errors. The code includes tooltips for better user experience and handles both SSO and key-based authentication modes. 

import os
import sys
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import threading
import time
import webbrowser

# Local imports
from gui.sso import run_sso_login
from logic.net_stats import get_tailscale_stats
from logic.statuscheck import wait_until_connected
from logic.vpn_logic import (
     get_auth_mode, is_sso_mode, save_url, save_key, load_saved_url, load_saved_key, write_profile_log
)
from gui.tailscaleclient import TailscaleClient
from gui.utils import format_bytes, center_window, add_tooltip
import logic.db_manager as db_manager 
from gui.change_credentials_popup import show_change_credentials_popup
from gui.progress_popup import ProgressPopup
from gui.traffic_popup import TrafficPopup

# IMPORT OUR GLOBAL LOGGER
from logic.logger import app_logger

class ClientTab(ctk.CTkFrame): 
    # ... [Keep __init__, _show_messagebox_popup, on_change_credentials_click, is_sso_mode, _save_credentials, vpn_status_change as they are] ...
    def __init__(self, parent_notebook, app_instance, tab_id, tab_name):
        super().__init__(parent_notebook, fg_color="transparent") 
        self.app_instance = app_instance
        self.tab_id = tab_id
        self.tab_name = tab_name

        self.login_server_var = tk.StringVar(value=load_saved_url(self.tab_name))
        self.auth_key_var = tk.StringVar(value=load_saved_key(self.tab_name))
        
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text="TAILSCALE VPN URL    :").grid(row=0, column=0, sticky='w', pady=(5, 2), padx=5)
        self.Entry1 = ctk.CTkEntry(self, textvariable=self.login_server_var, font=("Courier New", 12))
        self.Entry1.grid(row=0, column=1, sticky='ew', pady=(5, 2), padx=(0, 5))

        self.Entry1_1 = ctk.CTkEntry(self, textvariable=self.auth_key_var, font=("Courier New", 12), show="*")

        self.Label2 = ctk.CTkLabel(self, text="🔴 Disconnected", text_color="red", font=("Segoe UI", 13, "bold"), anchor='w')
        self.Label2.grid(row=3, column=0, sticky='w', pady=(5, 5), padx=5)

        self.change_cred_btn = ctk.CTkButton(
            self,
            text="Change Credentials",
            command=self.on_change_credentials_click, 
            width=140
        )
        self.change_cred_btn.grid(row=3, column=1, sticky='e', pady=(5, 5), padx=(0, 5))

        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.button_frame.grid(row=4, column=0, columnspan=2, sticky='ew', pady=(5, 10))

        self.vpn_action_btn = ctk.CTkButton(
            self.button_frame,
            text="Connect",
            command=self.vpn_status_change,
            fg_color="#4CAF50", 
            hover_color="#45a049"
        )
        self.vpn_action_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        self.show_stats_btn = ctk.CTkButton(
            self.button_frame, 
            text="Show Traffic Stats", 
            command=self.open_traffic_popup,
            fg_color="#666666" 
        )
        self.show_stats_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        self.traffic_label = ctk.CTkLabel(self, text="Traffic: Sent 0 B / Received 0 B", font=("Courier New", 11), anchor='w')
        self.traffic_label.grid(row=5, column=0, columnspan=2, sticky='w', padx=5)

        self.progress_popup = ProgressPopup(self.master.master)
        self.progress_popup.withdraw() 

        self.prev_stats = None
        self._monitoring = False

        add_tooltip(self.Entry1, "Enter your VPN URL (e.g. https://vpn.example.com)", self)
        add_tooltip(self.Entry1_1, "Enter the authentication key", self)
        add_tooltip(self.change_cred_btn, "Change VPN Settings", self)
        add_tooltip(self.show_stats_btn, "View Network stats", self)
        add_tooltip(self.Label2, "VPN connection status", self)
        add_tooltip(self.traffic_label, "Live traffic data (updated every 3 seconds)", self)
        add_tooltip(self.vpn_action_btn, "Connect to VPN", self)

        self.client = TailscaleClient(
            output_callback=self._print_output,
            status_callback=self._update_status_label,
            connected_callback=self._post_connect_ui,
            logged_out_callback=self.notify_app_logged_out,
            post_disconnect_callback=self._post_disconnect_ui,
            post_logout_callback=self._post_logout_ui,
            progress_callback=self._update_progress_label,
            message_popup_callback=self._show_messagebox_popup
        )

        if self.auth_key_var.get() and self.login_server_var.get():
            self.vpn_action_btn.configure(state='normal')
        else:
            self.vpn_action_btn.configure(state='disabled')  
            self.vpn_action_btn.update_idletasks()  
        
        self._update_change_credentials_button_state()

    def _show_messagebox_popup(self, title, message):
        messagebox.showinfo(title, message)

    def on_change_credentials_click(self):
        from gui.change_credentials_popup import show_change_credentials_popup
        show_change_credentials_popup(
            master=self,
            tab_name=self.tab_name,
            current_url=self._get_saved_url(),
            current_key=self._get_saved_key(),
            save_callback=self._save_credentials,
            icon_image=self.master.icon_image if hasattr(self.master, "icon_image") else None
        )

    def _get_saved_url(self):
        return load_saved_url(self.tab_name)

    def _get_saved_key(self):
        return load_saved_key(self.tab_name)

    def is_sso_mode(self):
        from logic.vpn_logic import get_file_path
        mode_file = get_file_path("auth_mode", self.tab_name)
        if os.path.exists(mode_file):
            with open(mode_file, "r") as f:
                return f.read().strip() == "google"
        return False  

    def _save_credentials(self, url, key, mode):
        from logic.vpn_logic import save_url, save_key, write_log, get_file_path
        save_url(url, self.tab_name)
        save_key(key, self.tab_name)
        try:
            mode_file = get_file_path("auth_mode", self.tab_name)
            with open(mode_file, "w") as f:
                f.write(mode)
        except Exception as e:
            app_logger.error(f"Error saving auth mode for '{self.tab_name}': {e}")

    def vpn_status_change(self):
        if self.client.connected:
            self.on_disconnect_and_cleanup()
        else:
            self.on_connect()

    # ---> THIS IS THE CRITICAL FIX <---
    def _print_output(self, text):
        text = text.strip()
        if not text:
            return
            
        # 1. Log every piece of output from Tailscale into the global logger
        app_logger.debug(f"[{self.tab_name}] {text}")

        # 2. Check for URL to open browser
        saved_url = load_saved_url(self.tab_name).strip()
        if saved_url and saved_url in text:
            try:
                webbrowser.open(text)
            except Exception as e:
                app_logger.error(f"Failed to open browser: {e}")

    # ... [Keep all other methods the same: _update_status_label, on_connect, etc.] ...
    def _update_status_label(self, text, color):     
        self.Label2.configure(text=text, text_color=color)
        if any(x in text.lower() for x in ["connected", "disconnected", "error", "failed"]):
            self.vpn_action_btn.configure(state='normal')

    def _update_progress_label(self, message, step):
        self.progress_popup.show_progress(message, step)

    def _post_connect_ui(self):
        self.vpn_action_btn.configure(
            text="Logout", 
            fg_color='#f44336', 
            hover_color='#da190b'
        )
        if hasattr(self.vpn_action_btn, "tooltip_label"):
            self.vpn_action_btn.tooltip_label.configure(text="Disconnect and Logout from VPN")
            
        self.Entry1.configure(state='disabled')
        self.Entry1_1.configure(state='disabled')
        self.app_instance.set_connected_tab(self.tab_id)
        self._update_change_credentials_button_state()

    def on_connect(self):
        server = self.login_server_var.get().strip()
        key = self.auth_key_var.get().strip()

        self.Entry1.configure(state='disabled')
        self.Entry1_1.configure(state='disabled')
        self.vpn_action_btn.configure(state='disabled')  
        self.vpn_action_btn.update_idletasks()
        self._update_change_credentials_button_state()

        if is_sso_mode(self.tab_name):
            cmd = ["tailscale", "up", f"--login-server={server}", "--accept-routes"]

            def on_sso_connected():
                self.client.logged_in = True  
                self.client.connected = True  
                self._post_connect_ui()
                self._print_output("[INFO] SSO login completed and connected.")
                self._update_status_label("🟢 Connected", "green")

            run_sso_login(
                cmd,
                expected_url_part=server,
                output_callback=self._print_output,
                error_callback=lambda e: self._print_output(f"[SSO ERROR] {e}"),
                success_callback=on_sso_connected 
            )

            def poll_and_update_gui():
                if wait_until_connected():
                    self._print_output("[INFO] SSO login completed and connected.")
                    self.client.connected = True  
                    self._post_connect_ui()
                    self._update_status_label("🟢 Connected", "green")
                else:
                    self._print_output("[ERROR] SSO login timeout or failure.")
                    self._update_status_label("❌ SSO login failed or timed out", "red")
                    self.enable_tab_ui()

            threading.Thread(target=poll_and_update_gui, daemon=True).start()

        else:
            self.client.connect(key, server, self.tab_name)
    
        from logic.net_stats import get_tailscale_stats
        self.prev_stats = get_tailscale_stats()
        self._monitoring = True
        threading.Thread(target=self._monitor_traffic_loop, daemon=True).start()
    
    def _post_disconnect_ui(self):
        self.vpn_action_btn.configure(state='normal')
        self.Entry1.configure(state='normal')
        self.Entry1_1.configure(state='normal')
        if self.app_instance.connected_tab_id == self.tab_id:
            self.app_instance.clear_connected_tab()
        self._update_change_credentials_button_state()
        self.prev_stats = None

    def on_logout(self):
        self.on_disconnect_and_cleanup()

    def on_disconnect_and_cleanup(self):
        self.vpn_action_btn.configure(state='disabled')  
        self.vpn_action_btn.update_idletasks()  

        self.client.disconnect(self.tab_name)

    def _post_logout_ui(self):
        self.vpn_action_btn.configure(
            text="Connect", 
            fg_color='#4CAF50', 
            hover_color='#45a049'
        )
        if hasattr(self.vpn_action_btn, "tooltip_label"):
            self.vpn_action_btn.tooltip_label.configure(text="Connect to VPN") 
            
        self.Entry1.configure(state='normal')
        self.Entry1_1.configure(state='normal')
        self.Label2.configure(text="🔴 Disconnected", text_color="red") 
        
        if self.app_instance.connected_tab_id == self.tab_id:
            self.app_instance.clear_connected_tab()
        self._update_change_credentials_button_state()

    def _save_new_credentials(self, new_url, new_key, mode):
        save_url(new_url, self.tab_name)
        save_key(new_key, self.tab_name)
        self.login_server_var.set(new_url)
        self.auth_key_var.set(new_key)

        from logic.vpn_logic import get_file_path
        try:
            mode_file = get_file_path("auth_mode", self.tab_name)
            with open(mode_file, "w") as f:
                f.write(mode)
        except Exception as e:
            app_logger.error(f"Error saving auth mode for '{self.tab_name}': {e}")

        if new_url and (new_key or mode == "google"):
            self.vpn_action_btn.configure(state='normal')
        else:
            self.vpn_action_btn.configure(state='disabled')  
            self.vpn_action_btn.update_idletasks()  

    def _poll_connection_status_after_sso(self, timeout=60):
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.client.is_connected():  
                self._post_connect_ui()
                return
            time.sleep(2)

        self._update_status_label("❌ SSO login timed out", "red")
        self.enable_tab_ui()

    def _update_change_credentials_button_state(self):
        if not self.client.connected and not self.client.logged_in:
            self.change_cred_btn.grid(row=3, column=1, sticky='e', pady=(5, 5), padx=(0, 5))
            self.change_cred_btn.configure(state='normal')
            self.Entry1_1.configure(state='normal')
        else:
            self.change_cred_btn.grid_forget()
            self.Entry1.configure(state='disabled')
            self.Entry1_1.configure(state='disabled')

    def disable_tab_ui(self):
        self.Entry1.configure(state='disabled')
        self.Entry1_1.configure(state='disabled')
        self.vpn_action_btn.configure(state='disabled')  
        self.vpn_action_btn.update_idletasks()  

        self._update_change_credentials_button_state()

    def enable_tab_ui(self):
        if self.client.connected:
            self.vpn_action_btn.configure(
                text='Logout',
                fg_color='#f44336',     
                hover_color='#da190b',
                state='normal'
            )
        elif self.client.logged_in:
            self.vpn_action_btn.configure(
                text='Connect',
                fg_color='#4CAF50',     
                hover_color='#45a049',
                state='normal'
            )
        else:
            self.vpn_action_btn.configure(
                text='Connect',
                fg_color='#4CAF50',
                hover_color='#45a049',
                state='normal'
            )
            self.Entry1.configure(state='normal')
            self.Entry1_1.configure(state='normal')

        self._update_change_credentials_button_state()

    def notify_app_logged_out(self):
        self.app_instance.clear_connected_tab()
        self.enable_tab_ui()
  
    def open_traffic_popup(self):
        if not self.client.connected:
            messagebox.showinfo("VPN Status", "VPN is not connected.")
            return

        TrafficPopup(self.master.master, self.prev_stats, self.tab_name)
        self.prev_stats = get_tailscale_stats()

    def _monitor_traffic_loop(self):
        while self._monitoring:
            stats = get_tailscale_stats()
            if stats and self.prev_stats:
                sent = stats.bytes_sent - self.prev_stats.bytes_sent
                recv = stats.bytes_recv - self.prev_stats.bytes_recv
                self.traffic_label.configure(text=f"Traffic: Sent {format_bytes(sent)} / Received {format_bytes(recv)}")
            time.sleep(3)