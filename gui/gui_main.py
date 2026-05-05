# gui/gui_main.py
# This module contains the main GUI application logic for the TAILSCALE VPN Client.

from gui.utils import write_log
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk 
import os
import sys

# Local imports
from gui.utils import format_bytes, center_window
from gui.styles import setup_styles
from gui.darkstyle import setup_dark_styles 
from gui.themes import THEMES
from gui.gui_tabs import ClientTab 
from gui.license_viewer import LicenseViewer
from gui.readme_viewer import ReadmeViewer
from gui.settings import show_settings
from gui.about import show_about
from gui.tray_handler import TrayHandler
from logic.logger import app_logger

from logic.vpn_logic import (
    acquire_mutex, release_mutex, check_tailscale_installed,
    initialize_app_storage, get_tab_dir, load_tab_names, load_settings, save_settings,
    save_tab_names, load_last_selected_tab_id, save_last_selected_tab_id,
    get_file_path, TAB_NAMES_FILE, DataCache
)
from concurrent.futures import ThreadPoolExecutor

class TabbedClientApp:
    def __init__(self, master, theme_name=None):
        print("[DEBUG] >> TabbedClientApp init start")
        self.master = master
        self.tabs = {} # Initialize early to avoid theme update errors
    
        if theme_name is None:
            settings = load_settings()
            theme_name = settings.get("theme", "light")
        
        self.icon_image = getattr(master, 'icon_image', None)
        self.master.title("TAILSCALE VPN Client v4.2")
        print("[DEBUG] >> Title set to 'TAILSCALE VPN Client v4.2'")
        
        # Set geometry based on OS
        if sys.platform == "win32":
            self.master.geometry("380x200+100+100") # Windows specific size
        elif sys.platform.startswith("linux"):
            self.master.geometry("400x250+100+100") # Linux specific size (slightly larger)
        else:
            self.master.geometry("380x200+100+100") # Default for other OS
        print("[DEBUG] >> Geometry set")

        self.master.resizable(False, False)
        self.master.protocol("WM_DELETE_WINDOW", self.on_close_app)

        self.current_theme_name = theme_name
        self.current_theme = THEMES.get(theme_name if theme_name in THEMES else "dark")

        self._bgcolor = self.current_theme.get("bgcolor")
        self._fgcolor = self.current_theme.get("fgcolor")

        self.master.configure(background=self.current_theme["bgcolor"])

        self._create_menu_bar()  

        # Apply theme (handles system/dark/light and style setup)
        self.change_theme(theme_name)
        
        # Acquire the mutex at application startup
        acquired = acquire_mutex()
        if acquired is False:
            messagebox.showwarning("Already Running", "Another instance of TAILSCALE VPN Client is already running.")
            sys.exit(0)
        elif acquired is None:
            messagebox.showerror("Error", "Could not acquire system mutex.")
            sys.exit(1)
        print("[DEBUG] >> Mutex acquired")

        if not check_tailscale_installed():
            messagebox.showerror("Error", "Tailscale CLI not found. Please install Tailscale.")
            sys.exit(1)
        print("[DEBUG] >> Tailscale check done")

        self.style = ttk.Style()
        self.style.theme_use('default') 
        print("[DEBUG] >> Styles configured")

        # Tabview Initialization
        self.tabview = ctk.CTkTabview(self.master)
        self.tabview.pack(padx=10, pady=(10, 0), fill='both', expand=True)

        self.notebook = self.tabview
        
        print("[DEBUG] >> Loading tab names")
        self.tab_id_to_name = load_tab_names()
        print(f"[DEBUG] >> Loaded tab names: {self.tab_id_to_name}")
        self.next_tab_id = 1
        if self.tab_id_to_name:
            self.next_tab_id = max(self.tab_id_to_name.keys()) + 1

        self.connected_tab_id = None

        if not self.tab_id_to_name:
            print("[DEBUG] >> No tabs found, prompting for first tab name")
            self._prompt_for_first_tab_name()
        else:
            # High-performance parallel pre-loading of profile data
            print("[DEBUG] >> Pre-loading profile data in parallel")
            DataCache.preload_all_profiles()

            # Parallel tab initialization
            print("[DEBUG] >> Initializing tabs in parallel")
            sorted_tab_ids = sorted(self.tab_id_to_name.keys())
            
            # Since CTkTabview.add must be called on main thread, we parallelize the Data fetching 
            # and then add to GUI sequentially but with pre-cached data.
            for tab_id in sorted_tab_ids:
                tab_name = self.tab_id_to_name[tab_id]
                self.add_new_tab(tab_name=tab_name, existing_tab_id=tab_id)

        self.update_tab_states()

        # Initialize System Tray
        self._setup_tray()

        # Handle Auto-connect
        self._auto_connect_if_enabled()

    def _auto_connect_if_enabled(self):
        """Auto-connect VPN on startup if enabled in settings."""
        settings = load_settings()
        if not settings.get("auto_connect", False):
            return

        last_tab_id = load_last_selected_tab_id()
        if last_tab_id is not None and last_tab_id in self.tabs:
            tab_instance = self.tabs[last_tab_id]
            tab_name = tab_instance.tab_name
            self.tabview.set(tab_name)
            self.update_tab_states()
            if hasattr(tab_instance, "connect_vpn"):
                self.master.after(500, tab_instance.connect_vpn)
        else:
            # Fallback to first tab
            if self.tab_id_to_name:
                first_id = sorted(self.tab_id_to_name.keys())[0]
                first_name = self.tab_id_to_name[first_id]
                self.tabview.set(first_name)
                self.update_tab_states()
                first_tab_instance = self.tabs[first_id]
                if hasattr(first_tab_instance, "connect_vpn"):
                    self.master.after(500, first_tab_instance.connect_vpn)

    def _setup_tray(self):
        """Sets up the system tray integration."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "icon.png")
        if not os.path.exists(icon_path):
             icon_path = os.path.join(base_dir, "assets", "icon.png")
        
        self.tray_handler = TrayHandler(self, icon_path)
        self.tray_handler.run()
        
        # Bind the minimize event
        self.master.bind("<Unmap>", self._on_window_unmap)

    def _on_window_unmap(self, event):
        """Handles the window minimize event."""
        if self.master.state() == 'iconic':
            self.tray_handler.hide_to_tray()

    def _create_menu_bar(self):
        menu_bar = tk.Menu(self.master)
    
        # File Menu
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Exit", command=self.on_close_app)
        # Updated to use external Settings module
        file_menu.add_command(label="Settings", command=lambda: show_settings(self.master, self.icon_image))
        menu_bar.add_cascade(label="File", menu=file_menu)

        # Profile Menu
        profile_menu = tk.Menu(menu_bar, tearoff=0)
        profile_menu.add_command(label="Add New Profile", command=self.on_add_new_tab_click)
        profile_menu.add_command(label="Remove Current Profile", command=self.remove_current_tab)
        menu_bar.add_cascade(label="Profile", menu=profile_menu)
        
        self.profile_menu = profile_menu

        # Theme Menu
        self.theme_var = tk.StringVar(value=self.current_theme_name)
        theme_menu = tk.Menu(menu_bar, tearoff=0)
        theme_menu.add_radiobutton(label="Light Theme", variable=self.theme_var, value="light", command=lambda: self.change_theme("light"))
        theme_menu.add_radiobutton(label="Dark Theme", variable=self.theme_var, value="dark", command=lambda: self.change_theme("dark"))
        theme_menu.add_separator()
        theme_menu.add_radiobutton(label="System Default", variable=self.theme_var, value="system", command=lambda: self.change_theme("system"))
        menu_bar.add_cascade(label="Theme", menu=theme_menu)

        # Logs Menu
        logs_menu = tk.Menu(menu_bar, tearoff=0)
        # 'postcommand' makes it read the folder dynamically every time you click "Global Logs"
        self.global_logs_menu = tk.Menu(logs_menu, tearoff=0, postcommand=self._populate_global_logs_menu)
        logs_menu.add_cascade(label="Global logs", menu=self.global_logs_menu)
        menu_bar.add_cascade(label="Logs", menu=logs_menu)

        # Help Menu
        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="About Us", command=lambda: show_about(self.master, self.icon_image))
        menu_bar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="View License", command=self.show_license)
        help_menu.add_command(label="Readme", command=self.show_readme)
        
        self.master.config(menu=menu_bar)

    def change_theme(self, new_theme_name):
        if new_theme_name not in THEMES and new_theme_name != "system":
            print(f"Theme '{new_theme_name}' not found.")
            return

        self.current_theme_name = new_theme_name
        if hasattr(self, "theme_var"):
            self.theme_var.set(new_theme_name)
        
        if new_theme_name == "system":
            ctk.set_appearance_mode("system")
            # For system mode, we pick dark colors as default for internal logic, 
            # though CTK will handle the visual part.
            self.current_theme = THEMES["dark"]
        elif new_theme_name == "dark":
            ctk.set_appearance_mode("dark")
            self.current_theme = THEMES["dark"]
        else:
            ctk.set_appearance_mode("light")
            self.current_theme = THEMES["light"]

        self._bgcolor = self.current_theme["bgcolor"]
        self._fgcolor = self.current_theme["fgcolor"]

        if ctk.get_appearance_mode().lower() == "dark":
            self.style = setup_dark_styles(self.current_theme)
        else:
            self.style = setup_styles(self.current_theme)

        self.master.configure(background=self._bgcolor)

        # Update all existing tabs
        for tab_instance in self.tabs.values():
            if hasattr(tab_instance, "update_theme"):
                tab_instance.update_theme(self.current_theme)

        settings = load_settings()
        settings["theme"] = new_theme_name
        save_settings(settings)

    def show_license(self):
        if not hasattr(self, "lic_win") or not self.lic_win.winfo_exists():
            self.lic_win = LicenseViewer(self.master)
        else:
            self.lic_win.focus()

    def show_readme(self):
        """Restored logic to launch the standalone ReadmeViewer with theme support."""
        try:
            from gui.readme_viewer import ReadmeViewer
            # Pass the current theme name to ensure visual consistency
            ReadmeViewer(self.master, theme=self.current_theme_name)
        except Exception as e:
            from gui.utils import write_log
            write_log(f"Failed to launch README: {e}", level="ERROR")

    def _prompt_for_first_tab_name(self):
        print("[DEBUG] >> _prompt_for_first_tab_name called")
        popup_width = 200
        popup_height = 130
        popup = tk.Toplevel(self.master)
        if hasattr(self.master, 'icon_image'):
            popup.iconphoto(False, self.master.icon_image)

        popup.title("Enter Tab Name")
        center_window(self.master, popup, popup_width, popup_height)       
        popup.configure(background=self._bgcolor)
        popup.resizable(False, False)
        popup.geometry(f"{popup_width}x{popup_height}+{self.master.winfo_x() + 50}+{self.master.winfo_y() + 50}")
        popup.grab_set()
        popup.protocol("WM_DELETE_WINDOW", self.master.destroy)
        popup.lift()
        popup.focus_force()
        popup.wm_attributes('-topmost', True)

        frame = ttk.Frame(popup)
        frame.pack(expand=True)
        
        ttk.Label(frame, text="Please enter a PROFILE Name\nfor this connection:", justify='center', anchor='center').pack(pady=10)
        
        name_entry = ttk.Entry(frame, width=40, justify='center') 
        name_entry.pack()
        name_entry.focus_set()

        def create_first_tab():
            tab_name = name_entry.get().strip()
            if not tab_name:
                messagebox.showwarning("Input Error", "PROFILE Name cannot be empty.", parent=popup)
                return
            if tab_name in self.tab_id_to_name.values():
                messagebox.showwarning("Duplicate Name", "The PROFILE Name already exists.", parent=popup)
                return

            try:
                test_dir = get_tab_dir(tab_name)
                os.makedirs(test_dir, exist_ok=True)
                popup.destroy()
                self.master.lift()
                self.add_new_tab(tab_name=tab_name)
            except Exception as e:
                messagebox.showerror("Error", f"Could not create directory: {e}", parent=popup)

        create_button = ttk.Button(popup, text="Create New PROFILE", command=create_first_tab,  style='ActionButton.TButton')
        create_button.pack(pady=10)

    def on_add_new_tab_click(self):
        settings = load_settings()
        max_tabs = settings.get("max_tabs", 5)
        if len(self.tabs) >= max_tabs:
            messagebox.showwarning("Tab Limit", f"Maximum {max_tabs} profiles allowed. You can increase this in File > Settings.")
            return

        popup_width = 300
        popup_height = 150
        
        popup = tk.Toplevel(self.master)
        if hasattr(self.master, 'icon_image'):
            popup.iconphoto(False, self.master.icon_image)

        popup.title("Enter New Profile Name")
        center_window(self.master, popup, popup_width, popup_height) 
        popup.configure(background=self._bgcolor)
        popup.grab_set()
        popup.wm_attributes('-topmost', True)

        ttk.Label(popup, text="Enter a Profile Name").pack(pady=10)
        name_entry = ttk.Entry(popup, width=40)
        name_entry.pack()
        name_entry.focus_set()

        def add_new_tab_with_name():
            tab_name = name_entry.get().strip()
            if not tab_name:
                messagebox.showwarning("Input Error", "Profile Name cannot be empty.", parent=popup)
                return
            if tab_name in self.tab_id_to_name.values():
                messagebox.showwarning("Input Error", "Name already exists.", parent=popup)
                return

            try:
                test_dir = get_tab_dir(tab_name)
                os.makedirs(test_dir, exist_ok=True)
                popup.destroy()
                self.master.lift()
                self.add_new_tab(tab_name=tab_name)
            except Exception as e:
                messagebox.showerror("Error", f"Could not create directory: {e}", parent=popup)

        create_button = ttk.Button(popup, text="Create New PROFILE", command=add_new_tab_with_name, style='ActionButton.TButton')
        create_button.pack(pady=10)

    def remove_current_tab(self):
        if not self.tabs:
            messagebox.showinfo("Info", "No profiles to remove.")
            return

        current_tab_name = self.tabview.get()
        current_tab_id = next((k for k, v in self.tab_id_to_name.items() if v == current_tab_name), None)

        if self.connected_tab_id == current_tab_id:
            messagebox.showwarning("WARNING !", f"Please logout from profile '{current_tab_name}' first.")
            return

        if messagebox.askyesno("Remove PROFILE", f"Remove profile '{current_tab_name}'?", parent=self.master):
            try:
                url_file = get_file_path("Tailscale_VPN_url", current_tab_name)
                key_file = get_file_path("Tailscale_VPN_key", current_tab_name)
                if os.path.exists(url_file): os.remove(url_file)
                if os.path.exists(key_file): os.remove(key_file)
                tab_dir = get_tab_dir(current_tab_name)
                if os.path.exists(tab_dir) and not os.listdir(tab_dir):
                    os.rmdir(tab_dir)
                    write_log(f"Removed empty tab directory: {tab_dir}", level="INFO")
            except Exception as e:
                write_log(f"Error removing files: {e}", level="ERROR")

            self.tabview.delete(current_tab_name)
            del self.tabs[current_tab_id]
            del self.tab_id_to_name[current_tab_id]
            save_tab_names(self.tab_id_to_name)
            write_log(f"Removed tab: '{current_tab_name}'", level="INFO")

            if not self.tabs:
                self._prompt_for_first_tab_name()
            
            self.update_tab_states()

    def add_new_tab(self, tab_name, existing_tab_id=None):
        if existing_tab_id is None:
            new_tab_id = self.next_tab_id
            self.next_tab_id += 1
        else:
            new_tab_id = existing_tab_id

        try:
            os.makedirs(get_tab_dir(tab_name), exist_ok=True)
        except Exception as e:
            messagebox.showerror("Directory Error", f"Could not create directory: {e}")
            return
        
        self.tabview.add(tab_name)
        tab_frame = self.tabview.tab(tab_name)
        
        frame = ClientTab(tab_frame, self, new_tab_id, tab_name)
        frame.pack(fill="both", expand=True)
        
        self.tabs[new_tab_id] = frame
        self.tab_id_to_name[new_tab_id] = tab_name

        save_tab_names(self.tab_id_to_name)
        self.tabview.set(tab_name)
        self.update_tab_states()

    def set_connected_tab(self, tab_id):
        self.connected_tab_id = tab_id
        self.update_tab_states()

    def clear_connected_tab(self):
        self.connected_tab_id = None
        self.update_tab_states()

    def update_tab_states(self, event=None):
        # Implementation of tab switching protection logic
        if self.connected_tab_id is not None:
            self.profile_menu.entryconfig("Add New Profile", state='disabled')
        else:
            self.profile_menu.entryconfig("Add New Profile", state='normal')

    def on_close_app(self):
        print("[DEBUG] on_close_app triggered")
        for tab_instance in self.tabs.values():
            if tab_instance.client.logged_in:
                messagebox.showwarning("WARNING !", "Please logout from all connections first.")
                return

        try:
            if hasattr(self, 'tray_handler'):
                self.tray_handler.icon.stop()

            for tab_name in self.tab_id_to_name.values():
                tab_dir = get_tab_dir(tab_name)
                if os.path.exists(tab_dir) and not os.listdir(tab_dir):
                    os.rmdir(tab_dir)

            if not self.tabs and os.path.exists(TAB_NAMES_FILE):
                os.remove(TAB_NAMES_FILE)

            release_mutex(None)
            print("[DEBUG] Released mutex")

        except Exception as e:
            write_log(f"Error during app shutdown: {e}", level="ERROR")

        self.master.destroy()
    
    def _populate_global_logs_menu(self):
        """Dynamically populates the Global logs submenu with files from the log directory."""
        from logic.logger import get_global_log_dir
        import os
        from gui.log_viewer import LogViewer

        # Clear existing entries in the menu
        self.global_logs_menu.delete(0, tk.END)

        log_dir = get_global_log_dir()
        if not os.path.exists(log_dir):
            self.global_logs_menu.add_command(label="No logs found", state="disabled")
            return

        # Fetch only .log files
        log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
        
        if not log_files:
            self.global_logs_menu.add_command(label="No logs enabled/found", state="disabled")
            return

        # Add a command for each log file
        for log_file in sorted(log_files):
            # lambda f=log_file captures the current iteration value correctly
            self.global_logs_menu.add_command(
                label=log_file,
                command=lambda f=log_file: LogViewer(self.master, f, f)
            )
    