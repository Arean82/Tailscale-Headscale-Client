# gui/change_credentials_popup.py
# This module provides a popup dialog for changing VPN credentials, allowing users to switch between auth key and SSO.

import os
import sys
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk  # Integrated CustomTkinter
from gui.utils import center_window
from PIL import Image, ImageTk 
from logic.vpn_logic import get_auth_mode, save_auth_mode

def resource_path(relative_path): 
    """Get absolute path to resource, works for dev and PyInstaller EXE"""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def show_change_credentials_popup(master, tab_name, current_url, current_key, save_callback, bg_color=None, icon_image=None):
    # If bg_color is passed as default hex from old call, we let CTk handle theme instead
    popup_width = 240 # Adjusted slightly for CTk padding
    popup_height = 240
    
    popup = ctk.CTkToplevel(master)
    popup.title(f"Set VPN Credentials - '{tab_name}'")
    popup.geometry(f"{popup_width}x{popup_height}")
    popup.resizable(False, False)
    
    # center_window remains compatible as it takes the window object
    center_window(master, popup, popup_width, popup_height)
    
    popup.grab_set()
    popup.wm_attributes('-topmost', True)

    if icon_image:
        popup.iconphoto(False, icon_image)

    try:
        # Maintaining exact original image logic
        key_icon = ImageTk.PhotoImage(Image.open(resource_path("assets/key_icon.png")).resize((16, 16)))
        sso_icon = ImageTk.PhotoImage(Image.open(resource_path("assets/google_icon.png")).resize((16, 16)))
        save_icon = ImageTk.PhotoImage(Image.open(resource_path("assets/save_logo.png")).resize((24, 24)))
        cancel_icon = ImageTk.PhotoImage(Image.open(resource_path("assets/cancel_icon.png")).resize((24, 24)))
    except Exception:
        key_icon = sso_icon = save_icon = cancel_icon = None

    # Load previously saved auth mode
    saved_mode = get_auth_mode(tab_name)
    use_sso = tk.BooleanVar(value=(saved_mode == "google"))

    # --- Layout using grid (Logic preserved 1:1) ---
    container = ctk.CTkFrame(popup, fg_color="transparent")
    container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    popup.columnconfigure(0, weight=1)
    popup.rowconfigure(0, weight=1)

    # Header
    ctk.CTkLabel(container, text="Authentication Method", font=('Segoe UI', 10, 'bold')).grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 4))

    icon_label = ctk.CTkLabel(container, image=key_icon, text="")
    icon_label.grid(row=1, column=0, sticky='w')

    switch = ctk.CTkCheckBox(container, text="Use SSO", variable=use_sso, command=lambda: animate_transition())
    switch.grid(row=1, column=1, sticky='w')

    # Frame holder logic preserved
    frame_holder = ctk.CTkFrame(container, fg_color="transparent")
    frame_holder.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(10, 5))
    frame_holder.grid_propagate(False)
    container.columnconfigure(0, weight=1)
    container.columnconfigure(1, weight=1)
    frame_holder.columnconfigure(0, weight=1)

    frame_holder.configure(height=80)

    # Auth Frame
    auth_frame = ctk.CTkFrame(frame_holder, fg_color="transparent")
    auth_frame.columnconfigure(0, weight=1)
    ctk.CTkLabel(auth_frame, text="VPN Server URL:", font=("Segoe UI", 11)).grid(row=0, column=0, sticky='w')
    url_entry_auth = ctk.CTkEntry(auth_frame)
    url_entry_auth.insert(0, current_url)
    url_entry_auth.grid(row=1, column=0, sticky='we', pady=(0, 5))
    ctk.CTkLabel(auth_frame, text="Authentication Key:", font=("Segoe UI", 11)).grid(row=2, column=0, sticky='w')
    key_entry = ctk.CTkEntry(auth_frame, show="*")
    key_entry.insert(0, current_key)
    key_entry.grid(row=3, column=0, sticky='we')

    # SSO Frame
    sso_frame = ctk.CTkFrame(frame_holder, fg_color="transparent")
    sso_frame.columnconfigure(0, weight=1)
    ctk.CTkLabel(sso_frame, text="VPN Server URL:", font=("Segoe UI", 11)).grid(row=0, column=0, sticky='w')
    url_entry_sso = ctk.CTkEntry(sso_frame)
    url_entry_sso.insert(0, current_url)
    url_entry_sso.grid(row=1, column=0, sticky='we', pady=(0, 5))
    ctk.CTkLabel(sso_frame, text="A browser will open for SSO login.", text_color="gray", font=("Segoe UI", 10)).grid(row=2, column=0, sticky='w')

    # Place logic for animation (Exact same implementation)
    auth_frame.place(x=0, y=0, relwidth=1, relheight=1)
    sso_frame.place(x=popup_width, y=0, relwidth=1, relheight=1)

    # Buttons
    button_frame = ctk.CTkFrame(container, fg_color="transparent")
    button_frame.grid(row=3, column=0, columnspan=2, pady=(10, 5))

    button_frame.columnconfigure((0, 1), weight=1)

    btn_cancel = ctk.CTkButton(
        button_frame,
        image=cancel_icon,
        text="",
        command=popup.destroy,
        width=40,
        fg_color="transparent",
        hover_color=("#dbdbdb", "#2b2b2b")
    )
    btn_cancel.image = cancel_icon
    btn_cancel.grid(row=0, column=0, padx=(0, 15), sticky="e")

    btn_save = ctk.CTkButton(
        button_frame,
        image=save_icon,
        text="",
        command=lambda: save(),
        width=40,
        fg_color="transparent",
        hover_color=("#dbdbdb", "#2b2b2b")
    )
    btn_save.image = save_icon

    btn_save.grid(row=0, column=1, sticky="w")

    animating = False

    def animate_transition():
        nonlocal animating
        if animating:
            return
        animating = True
        to_sso = use_sso.get()

        icon_label.configure(image=sso_icon if to_sso else key_icon)

        incoming = sso_frame if to_sso else auth_frame
        outgoing = auth_frame if to_sso else sso_frame
        incoming.lift()

        start = 0
        end = -popup_width if to_sso else popup_width
        direction = -1 if to_sso else 1
        step = 20

        def slide(i=0):
            nonlocal animating
            offset = i * step * direction
            outgoing.place_configure(x=offset)
            incoming.place_configure(x=offset + popup_width * (-direction))
            if abs(offset) < popup_width:
                popup.after(10, lambda: slide(i + 1))
            else:
                outgoing.place_configure(x=popup_width)
                incoming.place_configure(x=0)
                animating = False

        slide()

    def add_tooltip(widget, text):
        # Tooltip logic preserved 1:1
        tooltip = tk.Toplevel(popup) 
        tooltip.withdraw()
        tooltip.overrideredirect(True)
        tooltip.attributes("-topmost", True)

        label = tk.Label(
            tooltip, text=text,
            background="lightyellow",
            borderwidth=1, relief="solid",
            font=("Segoe UI", 8)
        )
        label.pack()

        def show_tooltip(event):
            tooltip.geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
            tooltip.deiconify()

        def hide_tooltip(event):
            tooltip.withdraw()

        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)

    add_tooltip(btn_save, "Save credentials")
    add_tooltip(btn_cancel, "Cancel")

    def save():
        # logic preserved 1:1
        url = url_entry_sso.get().strip() if use_sso.get() else url_entry_auth.get().strip()
        key = "" if use_sso.get() else key_entry.get().strip()

        if not url:
            messagebox.showwarning("Missing Data", "VPN URL is required.")
            return

        mode = "google" if use_sso.get() else "auth_key"
        save_callback(url, key, mode)
        save_auth_mode(tab_name, mode)
        popup.destroy()
        master.lift()
        messagebox.showinfo("Saved", f"Credentials saved for '{tab_name}'.")

    if use_sso.get():
        auth_frame.place_configure(x=popup_width)
        sso_frame.place_configure(x=0)
        icon_label.configure(image=sso_icon)    
        
    popup.bind("<Return>", lambda e: save())
    popup.bind("<Escape>", lambda e: popup.destroy())