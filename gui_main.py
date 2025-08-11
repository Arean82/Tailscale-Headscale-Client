# gui_main.py
# This module contains the main GUI application logic for the Tailscale VPN Client.

import tkinter as tk
from tkinter import ttk, messagebox, PhotoImage
import os
import sys # Keep sys for sys._MEIPASS and sys.exit()
# Removed: import win32event, win32api, win32con as their functionality is now in vpn_logic.py
from utils import format_bytes, center_window
from styles import setup_styles


from vpn_logic import (
    acquire_mutex, release_mutex, check_tailscale_installed,
    initialize_app_storage, get_tab_dir, load_tab_names, auto_connect_if_enabled, load_settings, save_settings,
    save_tab_names, load_last_selected_tab_id, save_last_selected_tab_id,
    write_log, get_file_path, TAB_NAMES_FILE
)

from gui_tabs import ClientTab # Ensure gui_tabs.py imports TailscaleClient from tailscaleclient.py

class TabbedClientApp:
    MAX_TABS = 5 # Maximum Profile Limit. To increase change the value
    def __init__(self, master):
        print("[DEBUG] >> TabbedClientApp init start")
        self.master = master
        self.icon_image = getattr(master, 'icon_image', None)
        self.master.title("Tailscale VPN Client")
        print("[DEBUG] >> Title set to 'Tailscale VPN Client'")
        
        # Set geometry based on OS
        if sys.platform == "win32":
            self.master.geometry("380x200+100+100") # Windows specific size
        elif sys.platform.startswith("linux"):
            self.master.geometry("400x250+100+100") # Linux specific size (slightly larger)
        else:
            self.master.geometry("380x200")+100+100 # Default for other OS
        print("[DEBUG] >> Geometry set")

        self.master.resizable(False, False)
        self.master.protocol("WM_DELETE_WINDOW", self.on_close_app) # Corrected protocol call

        self._bgcolor = '#d9d9d9' # Main application background color
        self.master.configure(background=self._bgcolor) # Main window background
        self._create_menu_bar()  # Add the global menu here
        
        # Acquire the mutex at application startup
        acquired = acquire_mutex()
        if acquired is False:
            messagebox.showwarning("Already Running", "Another instance of Tailscale VPN Client is already running.")
            sys.exit(0)
        elif acquired is None:
            messagebox.showerror("Error", "Could not acquire system mutex (another instance might be running or error occurred).")
            sys.exit(1)
        print("[DEBUG] >> Mutex acquired")

        if not check_tailscale_installed():
            messagebox.showerror("Error", "Tailscale CLI not found. Please install Tailscale.")
            sys.exit(1)
        print("[DEBUG] >> Tailscale check done")

        self.style = ttk.Style()
        self.style.theme_use('default') # Use default theme for better cross-platform look
        print("[DEBUG] >> Styles configured")

        # Initialize and apply styles
        self.style = setup_styles(self._bgcolor)

        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(padx=10, pady=(10, 0), fill='both', expand=True) # Fill and expand with window

        self.tabs = {}
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
            for tab_id in sorted(self.tab_id_to_name.keys()):
                tab_name = self.tab_id_to_name[tab_id]
                print(f"[DEBUG] >> Loading tab: {tab_id} - {tab_name}")    
                self.add_new_tab(tab_name=tab_name, existing_tab_id=tab_id)

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        self.update_tab_states()

    def _create_menu_bar(self):
        menu_bar = tk.Menu(self.master)
    
        # File Menu
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Exit", command=self.on_close_app)
        file_menu.add_command(label="Settings", command=self.open_settings_window)
        menu_bar.add_cascade(label="File", menu=file_menu)

        # Profile Menu
        profile_menu = tk.Menu(menu_bar, tearoff=0)
        profile_menu.add_command(label="Add New Profile", command=self.on_add_new_tab_click)
        profile_menu.add_command(label="Remove Current Profile", command=self.remove_current_tab)
        menu_bar.add_cascade(label="Profile", menu=profile_menu)
        
        # Store buttons for enabling/disabling dynamically
        self.profile_menu = profile_menu

        # Help Menu
        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="About Us", command=self.show_about)
        menu_bar.add_cascade(label="Help", menu=help_menu)

        self.master.config(menu=menu_bar)

    def open_settings_window(self):
        settings_win = tk.Toplevel(self.master)
        settings_win.title("Settings")
        settings_win.geometry("200x90")
        settings_win.grab_set() 

        # Load current setting
        self.settings = load_settings()
        # Create a BooleanVar for auto_connect
        auto_connect_var = tk.BooleanVar(value=self.settings.get("auto_connect", False))    

        def on_toggle():
            self.settings["auto_connect"] = auto_connect_var.get()
            save_settings(self.settings)
    
        # Label + Checkbox
        # tk.Label(settings_win, text="Auto-connect on startup:").pack(pady=(20, 5))
        chk = tk.Checkbutton(settings_win, text="Enable Auto-connect", variable=auto_connect_var, command=on_toggle)
        chk.pack(pady=(0, 20))

        # Close button
        #tk.Button(settings_win, text="Close", command=settings_win.destroy).pack()
        ttk.Button(settings_win, text="Close", command=settings_win.destroy, style='ActionButton.TButton').pack()


    def show_about(self):
        about_popup = tk.Toplevel(self.master)
        if hasattr(self.master, 'icon_image'):
            about_popup.iconphoto(False, self.master.icon_image)

        about_popup.title("About Us")
        about_popup.geometry("300x140")
        about_popup.resizable(False, False)
        about_popup.configure(background="#d9d9d9")
        about_popup.wm_attributes('-topmost', True)
        about_popup.grab_set()


        ttk.Label(about_popup, text="Tailscale VPN Client", font=("Segoe UI", 11, "bold")).pack(pady=(15, 5))
        ttk.Label(about_popup, text="Version 3.0").pack()
        ttk.Label(about_popup, text="© 2025 Tailscale VPN Client").pack()

        ttk.Button(about_popup, text="Close", command=about_popup.destroy, style='ActionButton.TButton').pack(pady=10)


    def _prompt_for_first_tab_name(self):
        print("[DEBUG] >> _prompt_for_first_tab_name called")
        popup_width = 200
        popup_height = 130
        popup = tk.Toplevel(self.master)
        if hasattr(self.master, 'icon_image'):
            popup.iconphoto(False, self.master.icon_image)

        popup.title("Enter Tab Name")
        center_window(self.master, popup, popup_width, popup_height) # Center relative to main window        
        popup.configure(background=self._bgcolor)
        popup.resizable(False, False)
        popup.geometry(f"{popup_width}x{popup_height}+{self.master.winfo_x() + 50}+{self.master.winfo_y() + 50}")
        popup.grab_set()
        popup.protocol("WM_DELETE_WINDOW", self.master.destroy)
        popup.lift()
        popup.focus_force()
        popup.wm_attributes('-topmost', True)

        # Create a frame to center align the widgets
        frame = ttk.Frame(popup)
        frame.pack(expand=True)
        
        # Center-aligned label
        ttk.Label(frame, text="Please enter a PROFILE Name\nfor this connection:", justify='center', anchor='center').pack(pady=10)
        
        # Center-aligned entry
        name_entry = ttk.Entry(frame, width=40, justify='center')  # <-- justify added
        name_entry.pack()
        name_entry.focus_set()

        def create_first_tab():
            tab_name = name_entry.get().strip()
            if not tab_name:
                messagebox.showwarning("Input Error", "PROFILE Name cannot be empty.", parent=popup)
                return
            if tab_name in self.tab_id_to_name.values():
                messagebox.showwarning("Duplicate Name", "The PROFILE Name you have entered already exists. Please choose a different name.", parent=popup)
                return

            try:
                test_dir = get_tab_dir(tab_name)
                os.makedirs(test_dir, exist_ok=True)
                popup.destroy()
                self.master.lift() # Bring main window to front after popup closes
                self.add_new_tab(tab_name=tab_name)
            except ValueError as ve:
                messagebox.showerror("Invalid Name", f"Invalid tab name: {ve}", parent=popup)
            except Exception as e:
                messagebox.showerror("Error", f"Could not create directory for tab: {e}", parent=popup)

        create_button = ttk.Button(popup, text="Create New PROFILE", command=create_first_tab,  style='ActionButton.TButton')
        create_button.pack(pady=10)

    def on_add_new_tab_click(self):
        if len(self.tabs) >= self.MAX_TABS:
            messagebox.showwarning("Tab Limit", f"Maximum {self.MAX_TABS} tabs allowed.")
            return

        popup_width = 300
        popup_height = 150
        
        popup = tk.Toplevel(self.master)
        if hasattr(self.master, 'icon_image'):
            popup.iconphoto(False, self.master.icon_image)

        popup.title("Enter New Profile Name")
        center_window(self.master, popup, popup_width, popup_height) # Center relative to main window
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
                messagebox.showwarning("Input Error", "A Profile with this name already exists. Please choose a different name.", parent=popup)
                return

            try:
                test_dir = get_tab_dir(tab_name)
                os.makedirs(test_dir, exist_ok=True)
                popup.destroy()
                self.master.lift() # Bring main window to front after popup closes
                self.add_new_tab(tab_name=tab_name)
            except ValueError as ve:
                messagebox.showerror("Invalid Name", f"Invalid tab name: {ve}", parent=popup)
            except Exception as e:
                messagebox.showerror("Error", f"Could not create directory for tab: {e}", parent=popup)

        create_button = ttk.Button(popup, text="Create New PROFILE", command=add_new_tab_with_name, style='ActionButton.TButton')
        create_button.pack(pady=10)

    def remove_current_tab(self):
        if not self.tabs:
            messagebox.showinfo("Info", "No profiles to remove.")
            return

        current_tab_index = self.notebook.index(self.notebook.select())
        # Ensure that current_tab_index is valid
        if current_tab_index < 0:
            messagebox.showinfo("Info", "No PROFILE selected to remove.")
            return

        current_tab_id = list(self.tabs.keys())[current_tab_index]
        current_tab_name = self.tab_id_to_name[current_tab_id]

        if self.connected_tab_id == current_tab_id:
            messagebox.showwarning("WARNING !", f"Please logout from the currently active profile '{current_tab_name}' before removing it.")
            return

        if messagebox.askyesno("Remove PROFILE", f"Are you sure you want to remove the profile '{current_tab_name}'?", parent=self.master):
            try:
                url_file = get_file_path("Tailscale_VPN_url", current_tab_name)
                key_file = get_file_path("Tailscale_VPN_key", current_tab_name)
                if os.path.exists(url_file):
                    os.remove(url_file)
                if os.path.exists(key_file):
                    os.remove(key_file)
                tab_dir = get_tab_dir(current_tab_name)
                if os.path.exists(tab_dir) and not os.listdir(tab_dir):
                    os.rmdir(tab_dir)
                    write_log(f"Removed empty tab directory: {tab_dir}", level="INFO")
            except Exception as e:
                write_log(f"Error removing files for tab '{current_tab_name}': {e}", level="ERROR")
                messagebox.showwarning("File Deletion Error", f"Could not remove all associated files: {e}")

            self.notebook.forget(self.notebook.select())
            del self.tabs[current_tab_id]
            del self.tab_id_to_name[current_tab_id]
            save_tab_names(self.tab_id_to_name)
            write_log(f"Removed tab: '{current_tab_name}' (ID: {current_tab_id})", level="INFO")

            if not self.tabs:
                self._prompt_for_first_tab_name()
            else:
                self.notebook.select(0) # Select the first tab after removal

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
            messagebox.showerror("Directory Error", f"Could not create directory for tab: '{tab_name}':\n{e}")
            return
        
        frame = ClientTab(self.notebook, self, new_tab_id, tab_name)
        self.notebook.add(frame, text=tab_name)
        self.tabs[new_tab_id] = frame
        self.tab_id_to_name[new_tab_id] = tab_name

        save_tab_names(self.tab_id_to_name)

        self.notebook.select(frame)
        self.update_tab_states()

    def set_connected_tab(self, tab_id):
        self.connected_tab_id = tab_id
        self.update_tab_states()

    def clear_connected_tab(self):
        self.connected_tab_id = None
        self.update_tab_states()

    def update_tab_states(self, event=None):
        current_tab_widget = None
        try:
            # Get the currently selected tab's widget
            selected_tab_id_name = self.notebook.select()
            if selected_tab_id_name:
                current_tab_widget = self.notebook.nametowidget(selected_tab_id_name)
        except tk.TclError:
            pass # No tab selected or notebook empty

        for tab_id, tab_instance in self.tabs.items():
            if tab_id == self.connected_tab_id:
                # If this tab is connected, enable its UI and ensure it's selectable
                tab_instance.enable_tab_ui()
                self.notebook.tab(tab_instance, state='normal')
            else:
                # If another tab is connected, disable this tab's UI and make it unselectable
                if self.connected_tab_id is not None:
                    tab_instance.disable_tab_ui()
                    self.notebook.tab(tab_instance, state='disabled')
                else:
                    # No tab is connected, enable/disable based on whether it's the active tab
                    self.notebook.tab(tab_instance, state='normal')
                    if tab_instance == current_tab_widget:
                        tab_instance.enable_tab_ui()
                    else:
                        tab_instance.disable_tab_ui()

        # Update the menu items based on the current state of tabs
        if hasattr(self, 'profile_menu'):
            # Disable "Add New Profile" if a tab is connected or max tabs reached
            if self.connected_tab_id is not None or len(self.tabs) >= self.MAX_TABS:
                self.profile_menu.entryconfig("Add New Profile", state='disabled')
            else:
                self.profile_menu.entryconfig("Add New Profile", state='normal')

            # Disable "Remove Current Profile" if no tabs or current tab is connected
            if not self.tabs:
                self.profile_menu.entryconfig("Remove Current Profile", state='disabled')
            else:
                try:
                    current_tab_index = self.notebook.index(self.notebook.select())
                    current_tab_id = list(self.tabs.keys())[current_tab_index]
                    if current_tab_id == self.connected_tab_id:
                        self.profile_menu.entryconfig("Remove Current Profile", state='disabled')
                    else:
                        self.profile_menu.entryconfig("Remove Current Profile", state='normal')
                except Exception:
                    self.profile_menu.entryconfig("Remove Current Profile", state='disabled')



    def on_tab_changed(self, event):
        self.update_tab_states()
        try:
            # Get the currently selected tab's ID and save it
            selected_tab_index = self.notebook.index(self.notebook.select())
            selected_widget = self.notebook.nametowidget(self.notebook.tabs()[selected_tab_index])
            for tab_id, tab_instance in self.tabs.items():
                if selected_widget == tab_instance:
                    save_last_selected_tab_id(tab_id)
                    break
        except tk.TclError:
            pass # No tab selected, or error getting widget

    def on_close_app(self):
        print("[DEBUG] on_close_app triggered")

        for tab_name, tab_instance in self.tabs.items():
            print(f"[DEBUG] Checking connection status for tab: {tab_name}")
            if tab_instance.client.logged_in:
                print(f"[DEBUG] Tab '{tab_name}' is still connected. Blocking close.")
                messagebox.showwarning("WARNING !", "Please logout from all active connections before closing the application.")
                return

        try:
            for tab_id, tab_name in self.tab_id_to_name.items():
                print(f"[DEBUG] Checking directory for tab: {tab_name}")
                tab_dir = get_tab_dir(tab_name)
                if os.path.exists(tab_dir) and not os.listdir(tab_dir):
                    try:
                        os.rmdir(tab_dir)
                        print(f"[DEBUG] Removed empty directory: {tab_dir}")
                        write_log(f"Removed empty tab directory: {tab_dir}", level="INFO")
                    except Exception as e:
                        print(f"[DEBUG] Error removing directory: {e}")
                        write_log(f"Error removing empty tab directory {tab_dir}: {e}", level="ERROR")

            if not self.tabs and os.path.exists(TAB_NAMES_FILE):
                os.remove(TAB_NAMES_FILE)
                print("[DEBUG] Removed tab_names.json file")
                write_log(f"Removed empty tab_names.json file.", level="INFO")

            release_mutex(None)
            print("[DEBUG] Released mutex")

        except Exception as e:
            print(f"[DEBUG] Exception during shutdown: {e}")
            write_log(f"Error during app shutdown: {e}", level="ERROR")

        print("[DEBUG] Destroying GUI window")
        self.master.destroy()

