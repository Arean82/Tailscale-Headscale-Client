# change_credentials_popup.py
# This module provides a popup dialog for changing VPN credentials, allowing users to switch between

import tkinter as tk
from tkinter import ttk, messagebox
from utils import center_window
from PIL import Image, ImageTk 

def show_change_credentials_popup(master, tab_name, current_url, current_key, save_callback, bg_color="#f0f0f0", icon_image=None):
    popup_width = 200
    popup_height = 200
    popup = tk.Toplevel(master)
    popup.title(f"Set VPN Credentials - '{tab_name}'")
    popup.geometry(f"{popup_width}x{popup_height}")
    popup.resizable(False, False)
    popup.configure(background=bg_color)
    center_window(master, popup, popup_width, popup_height)
    popup.grab_set()
    popup.wm_attributes('-topmost', True)

    if icon_image:
        popup.iconphoto(False, icon_image)

    try:
        key_icon = ImageTk.PhotoImage(Image.open("assets/key_icon.png").resize((16, 16)))
        sso_icon = ImageTk.PhotoImage(Image.open("assets/google_icon.png").resize((16, 16)))
        save_icon = ImageTk.PhotoImage(Image.open("assets/save_logo.png").resize((24, 24)))
        cancel_icon = ImageTk.PhotoImage(Image.open("assets/cancel_icon.png").resize((24, 24)))
    except Exception:
        key_icon = sso_icon = save_icon = cancel_icon = None

    use_sso = tk.BooleanVar(value=False)

    # --- Layout using grid ---
    container = ttk.Frame(popup, padding=(10, 10))
    container.grid(row=0, column=0, sticky="nsew")
    popup.columnconfigure(0, weight=1)
    popup.rowconfigure(0, weight=1)

    # Header
    ttk.Label(container, text="Authentication Method", font=('Segoe UI', 10, 'bold')).grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 4))

    icon_label = ttk.Label(container, image=key_icon)
    icon_label.grid(row=1, column=0, sticky='w')

    switch = ttk.Checkbutton(container, text="Use Google SSO", variable=use_sso, command=lambda: animate_transition())
    switch.grid(row=1, column=1, sticky='w')

    # Frame holder with grid layout
    frame_holder = ttk.Frame(container)
    frame_holder.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(10, 5))
    frame_holder.grid_propagate(False)
    container.columnconfigure(0, weight=1)
    container.columnconfigure(1, weight=1)
    frame_holder.columnconfigure(0, weight=1)

    #frame_holder.configure(width=popup_width - 40, height=80)  # Fit tightly in small popup
    frame_holder.configure(height=80)

    # Auth Frame
    auth_frame = ttk.Frame(frame_holder)
    auth_frame.columnconfigure(0, weight=1)
    ttk.Label(auth_frame, text="VPN Server URL:").grid(row=0, column=0, sticky='w')
    url_entry_auth = ttk.Entry(auth_frame, width=42)
    url_entry_auth.insert(0, current_url)
    url_entry_auth.grid(row=1, column=0, sticky='we', pady=(0, 5))
    ttk.Label(auth_frame, text="Authentication Key:").grid(row=2, column=0, sticky='w')
    key_entry = ttk.Entry(auth_frame, width=42)
    key_entry.insert(0, current_key)
    key_entry.grid(row=3, column=0, sticky='we')

    # SSO Frame
    sso_frame = ttk.Frame(frame_holder)
    sso_frame.columnconfigure(0, weight=1)
    ttk.Label(sso_frame, text="VPN Server URL:").grid(row=0, column=0, sticky='w')
    url_entry_sso = ttk.Entry(sso_frame)
    #url_entry_sso = ttk.Entry(sso_frame, width=45)
    url_entry_sso.insert(0, current_url)
    url_entry_sso.grid(row=1, column=0, sticky='we', pady=(0, 5))
    ttk.Label(sso_frame, text="A browser will open for Google SSO login.", foreground="gray").grid(row=2, column=0, sticky='w')

    # Place the frames using .place (still for animation)
    auth_frame.place(x=0, y=0, relwidth=1, relheight=1)
    sso_frame.place(x=popup_width, y=0, relwidth=1, relheight=1)

    # Buttons
    button_frame = ttk.Frame(container)
    button_frame.grid(row=3, column=0, columnspan=2, pady=(10, 5))  # Top and bottom padding

    # Center align buttons inside their frame
    button_frame.columnconfigure((0, 1), weight=1)

    #btn_cancel = ttk.Button(button_frame, text="Cancel", command=popup.destroy, style='ActionButton.TButton')
    #btn_cancel.grid(row=0, column=0, padx=(0, 15), sticky="e")

    btn_cancel = ttk.Button(
        button_frame,
        image=cancel_icon,
        text="",
        command=popup.destroy,
        style='ActionButton.TButton'
    )
    btn_cancel.image = cancel_icon
    btn_cancel.grid(row=0, column=0, padx=(0, 15), sticky="e")

    #btn_save = ttk.Button(button_frame, text="Save", command=lambda: save(), style='ActionButton.TButton')
    btn_save = ttk.Button(
        button_frame,
        image=save_icon,
        text="",  # No text
        command=lambda: save(),
        style='ActionButton.TButton'
    )
    btn_save.image = save_icon  # Prevent garbage collection

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

        tooltip = tk.Toplevel(popup)  # Use `popup` as master instead of `widget`
        tooltip.withdraw()
        tooltip.overrideredirect(True)
        tooltip.attributes("-topmost", True)  # Ensure it stays on top of all windows

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

    # After creating btn_save
    add_tooltip(btn_save, "Save credentials")
    add_tooltip(btn_cancel, "Cancel")

    def save():
        url = url_entry_sso.get().strip() if use_sso.get() else url_entry_auth.get().strip()
        key = "" if use_sso.get() else key_entry.get().strip()

        if not url:
            messagebox.showwarning("Missing Data", "VPN URL is required.")
            return

        mode = "google" if use_sso.get() else "auth_key"
        save_callback(url, key, mode)
        popup.destroy()
        master.lift()
        messagebox.showinfo("Saved", f"Credentials saved for '{tab_name}'.")

    popup.bind("<Return>", lambda e: save())
    popup.bind("<Escape>", lambda e: popup.destroy())
