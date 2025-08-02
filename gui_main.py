# gui_main.py
# This module contains the main GUI application logic for the MAPView VPN Client.

import tkinter as tk
from tkinter import ttk, messagebox, PhotoImage
import os
import sys # Keep sys for sys._MEIPASS and sys.exit()
# Removed: import win32event, win32api, win32con as their functionality is now in vpn_logic.py
from utils import format_bytes, center_window


from vpn_logic import (
    acquire_mutex, release_mutex, check_tailscale_installed,
    initialize_app_storage, get_tab_dir, load_tab_names,
    save_tab_names, load_last_selected_tab_id, save_last_selected_tab_id,
    write_log, get_file_path, TAB_NAMES_FILE
)

from gui_tabs import ClientTab # Ensure gui_tabs.py imports TailscaleClient from tailscaleclient.py

class TabbedClientApp:
    MAX_TABS = 5 # Maximum Profile Limit. To increase change the value
    def __init__(self, master):
        print(">> TabbedClientApp init start")
        self.master = master
        self.icon_image = getattr(master, 'icon_image', None)
        self.master.title("MAPView VPN Client")
        
        # Set geometry based on OS
        if sys.platform == "win32":
            self.master.geometry("380x200+100+100") # Windows specific size
        elif sys.platform.startswith("linux"):
            self.master.geometry("400x250+100+100") # Linux specific size (slightly larger)
        else:
            self.master.geometry("380x200")+100+100 # Default for other OS
        print(">> Geometry set")

        self.master.resizable(False, False)
        self.master.protocol("WM_DELETE_WINDOW", self.on_close_app) # Corrected protocol call

        self._bgcolor = '#d9d9d9' # Main application background color
        self.master.configure(background=self._bgcolor) # Main window background
        self._create_menu_bar()  # Add the global menu here
        
        # Acquire the mutex at application startup
        acquired = acquire_mutex()
        if acquired is False:
            messagebox.showwarning("Already Running", "Another instance of MAPView VPN Client is already running.")
            sys.exit(0)
        elif acquired is None:
            messagebox.showerror("Error", "Could not acquire system mutex (another instance might be running or error occurred).")
            sys.exit(1)
        print(">> Mutex acquired")

        if not check_tailscale_installed():
            messagebox.showerror("Error", "Tailscale CLI not found. Please install Tailscale.")
            sys.exit(1)
        print(">> Tailscale check done")

        self.style = ttk.Style()
        self.style.theme_use('default') # Use default theme for better cross-platform look
        print(">> Styles configured")

        # General TButton style (flat for most buttons)
        self.style.configure("TButton",
                            font=('Segoe UI', 9, 'bold'),
                            padding=6,
                            relief="flat",
                            background=self._bgcolor,
                            foreground='black'
                           )
        self.style.map("TButton",
                       background=[('active', '#c9c9c9'), ('!disabled', self._bgcolor), ('disabled', '#cccccc')], # Added disabled state
                       foreground=[('active', 'black'), ('!disabled', 'black'), ('disabled', '#888888')] # Added disabled state
                      )

        # Specific button styles for visual distinction (Connect, Disconnect, Logout)
        self.style.configure("Connect.TButton", background='#4CAF50', foreground='white') # Green
        self.style.map("Connect.TButton",
                       background=[('active', '#45a049'), ('!disabled', '#4CAF50'), ('disabled', '#a5d6a7')], # Lighter green when disabled
                       foreground=[('active', 'white'), ('!disabled', 'white'), ('disabled', '#ffffff')] # White text, potentially lighter for contrast
                      )

        self.style.configure("Disconnect.TButton", background='#f44336', foreground='white') # Red
        self.style.map("Disconnect.TButton",
                       background=[('active', '#da190b'), ('!disabled', '#f44336'), ('disabled', '#ef9a9a')], # Lighter red when disabled
                       foreground=[('active', 'white'), ('!disabled', 'white'), ('disabled', '#ffffff')]
                      )

        self.style.configure("Logout.TButton", background='#FF9800', foreground='white') # Orange
        self.style.map("Logout.TButton",
                       background=[('active', '#fb8c00'), ('!disabled', '#FF9800'), ('disabled', '#ffcc80')], # Lighter orange when disabled
                       foreground=[('active', 'white'), ('!disabled', 'white'), ('disabled', '#ffffff')]
                      )
        
        # New style Click Button
        self.style.configure("ClickButton.TButton",
                            font=('Segoe UI', 7, 'normal'),
                            padding=4,  # Slightly more padding
                            relief="raised",  # Raised relief for a 3D/border effect
                            background="#d0eaff",   # Light blue tint
                            foreground="#003366",  # Dark blue text for contrast
                            borderwidth=1  # Explicit border
                            )

        self.style.map("ClickButton.TButton",
                    background=[
                        ('active', '#707070'),   # On hover
                        ('pressed', '#505050')   # On click
                    ],
                    foreground=[
                        ('active', 'white'),
                        ('pressed', 'white')
                    ],
                    relief=[
                        ('pressed', 'sunken')
                    ]
                    )

        # New style for "Add New Profile" and "Remove Current Profile" buttons
        self.style.configure("ActionButton.TButton",
                             font=('Segoe UI', 8, 'bold'),
                             padding=6, # Slightly more padding
                             relief="raised", # Raised relief for a 3D/border effect
                             background="#a0a0a0", # A slightly darker grey
                             foreground="black",
                             borderwidth=1 # Explicit border
                            )
        self.style.map("ActionButton.TButton",
                       background=[('active', '#707070'), # Darker when active (hover)
                                   ('pressed', '#505050'), # Even darker when actually pressed for click effect
                                   ('!disabled', "#a0a0a0"),
                                   ('disabled', '#cccccc')], # Lighter grey when disabled
                       foreground=[('active', 'white'), # White text on active/pressed
                                   ('pressed', 'white'),
                                   ('!disabled', 'black'),
                                   ('disabled', '#888888')], # Lighter text for disabled
                       relief=[('pressed', 'sunken'), ('disabled', 'flat')] # Flat relief when disabled
                      )

        # TEntry style
        self.style.configure("TEntry",
                            fieldbackground="white",
                            foreground="black",
                            relief="sunken"
                           )
        # Add disabled state for TEntry background
        self.style.map("TEntry",
                       fieldbackground=[('disabled', '#e0e0e0')] # Light grey background for disabled entry
                      )

        # TLabel style
        self.style.configure("TLabel",
                            background=self._bgcolor,
                            foreground="black"
                           )

        # Configure the TNotebook widget itself
        self.style.configure("TNotebook", background=self._bgcolor, borderwidth=0)
        self.style.layout("TNotebook", [("TNotebook.client", {"sticky": "nswe"})])
        print(">> Notebook initialized")
        
        # Configure the individual tabs within the TNotebook
        self.style.configure("TNotebook.Tab",
                        background=self._bgcolor, # Tab background color
                        foreground='black', # Tab text color
                        padding=[6, 3], # Horizontal and vertical padding for tabs
                        font=('Segoe UI', 9, 'bold'),
                        borderwidth=0,
                        relief="flat",
                        focuscolor="none"
                       )

        # Map colors for different states of a TNotebook.Tab
        self.style.map("TNotebook.Tab",
                  background=[("selected", '#c9c9c9'), # Lighter grey for selected tab
                              ("active", '#e0e0e0'),   # Slightly different hover background
                              ("!disabled", self._bgcolor),
                              ("disabled", '#f0f0f0')], # Even lighter grey for disabled tab
                  foreground=[("selected", 'black'),
                              ("active", 'black'),
                              ("!disabled", 'black'),
                              ("disabled", '#a0a0a0')] # Lighter text for disabled tab
                 )


        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(padx=10, pady=(10, 0), fill='both', expand=True) # Fill and expand with window

        self.tabs = {}
        print(">> Loading tab names")
        self.tab_id_to_name = load_tab_names()
        print(f">> Loaded tab names: {self.tab_id_to_name}")
        self.next_tab_id = 1
        if self.tab_id_to_name:
            self.next_tab_id = max(self.tab_id_to_name.keys()) + 1

        self.connected_tab_id = None

        if not self.tab_id_to_name:
            print(">> No tabs found, prompting for first tab name")
            self._prompt_for_first_tab_name()
        else:
            for tab_id in sorted(self.tab_id_to_name.keys()):
                tab_name = self.tab_id_to_name[tab_id]
                print(f">> Loading tab: {tab_id} - {tab_name}")    
                self.add_new_tab(tab_name=tab_name, existing_tab_id=tab_id)

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        self.update_tab_states()

    def _create_menu_bar(self):
        menu_bar = tk.Menu(self.master)
    
        # File Menu
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Exit", command=self.on_close_app)
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
        ttk.Label(about_popup, text="© 2025 Tailscale VPN Client (unofficial)").pack()

        ttk.Button(about_popup, text="Close", command=about_popup.destroy, style='ActionButton.TButton').pack(pady=10)


    def _prompt_for_first_tab_name(self):
        print(">> _prompt_for_first_tab_name called")
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
            messagebox.showwarning("Not Allowed", f"Please logout from the currently active profile '{current_tab_name}' before removing it.")
            return

        if messagebox.askyesno("Remove PROFILE", f"Are you sure you want to remove the profile '{current_tab_name}'?", parent=self.master):
            try:
                url_file = get_file_path("MAPView_VPN_url", current_tab_name)
                key_file = get_file_path("MAPView_VPN_key", current_tab_name)
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
        for tab_instance in self.tabs.values():
            if tab_instance.client.logged_in:
                messagebox.showwarning("Not Allowed", "Please logout from all active connections before closing the application.")
                return
        try:
            for tab_id, tab_name in self.tab_id_to_name.items():
                tab_dir = get_tab_dir(tab_name)
                # Check if directory exists and is empty before attempting to remove
                if os.path.exists(tab_dir) and not os.listdir(tab_dir):
                    try:
                        os.rmdir(tab_dir)
                        write_log(f"Removed empty tab directory: {tab_dir}", level="INFO")
                    except Exception as e:
                        write_log(f"Error removing empty tab directory {tab_dir}: {e}", level="ERROR")

            if not self.tabs and os.path.exists(TAB_NAMES_FILE):
                os.remove(TAB_NAMES_FILE)
                write_log(f"Removed empty tab_names.json file.", level="INFO")

            # Release the mutex before destroying the master window
            release_mutex(None)
        except Exception as e:
            write_log(f"Error during app shutdown: {e}", level="ERROR")
        self.master.destroy()



def start_gui():
    print(">> start_gui called")
    initialize_app_storage()
    print(">> storage initialized")

    root = tk.Tk()
    root.title("MAPView VPN Client")
    root.geometry("400x300+100+100")  # Force the window on-screen
    print(">> root window created")

    try:
        # Use absolute path relative to this script
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        bundled_icon_path = os.path.join(base_dir, "icon.png")

        if os.path.exists(bundled_icon_path):
            icon_image = PhotoImage(file=bundled_icon_path)
            root.iconphoto(False, icon_image)
            root.icon_image = icon_image  # Preserve reference
        else:
            write_log(f"Icon file not found for Tkinter window: {bundled_icon_path}", level="WARNING")
    except Exception as e:
        write_log(f"Error setting Tkinter window icon: {e}", level="ERROR")


    app = TabbedClientApp(root)
    print(">> TabbedClientApp initialized")

    last_tab_id = load_last_selected_tab_id()
    if last_tab_id is not None and last_tab_id in app.tabs:
        for tab_index, tab_frame_id in enumerate(app.notebook.tabs()):
            tab_widget = app.notebook.nametowidget(tab_frame_id)
            if hasattr(tab_widget, 'tab_id') and tab_widget.tab_id == last_tab_id:
                app.notebook.select(tab_frame_id)
                app.update_tab_states()
                break
    else:
        if app.notebook.tabs():
            app.notebook.select(app.notebook.tabs()[0])
            app.update_tab_states()

    root.protocol("WM_DELETE_WINDOW", app.on_close_app)
    print(">> Entering mainloop")
    root.mainloop()
    print(">> GUI exited")

