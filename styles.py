# styles.py

import sys
import tkinter.ttk as ttk

def setup_styles(theme):
    bgcolor = theme.get("bgcolor", "#d9d9d9")
    fgcolor = theme.get("fgcolor", "black")

    style = ttk.Style()
    style.theme_use('default')

    # General TButton style (flat for most buttons)
    style.configure("TButton",
                    font=('Segoe UI', 9, 'bold'),
                    padding=6,
                    relief="flat",
                    background=bgcolor,
                    foreground='black'
                    )
    style.map("TButton",
              background=[('active', '#c9c9c9'), ('!disabled', bgcolor), ('disabled', '#cccccc')],
              foreground=[('active', 'black'), ('!disabled', 'black'), ('disabled', '#888888')]
              )

    # Specific button styles for visual distinction (Connect, Disconnect, Logout)
    style.configure("Connect.TButton", background='#4CAF50', foreground='white')
    style.map("Connect.TButton",
              background=[('active', '#45a049'), ('!disabled', '#4CAF50'), ('disabled', '#a5d6a7')],
              foreground=[('active', 'white'), ('!disabled', 'white'), ('disabled', '#ffffff')]
              )

    style.configure("Disconnect.TButton", background='#f44336', foreground='white')
    style.map("Disconnect.TButton",
              background=[('active', '#da190b'), ('!disabled', '#f44336'), ('disabled', '#ef9a9a')],
              foreground=[('active', 'white'), ('!disabled', 'white'), ('disabled', '#ffffff')]
              )

    style.configure("Logout.TButton", background='#FF9800', foreground='white')
    style.map("Logout.TButton",
              background=[('active', '#fb8c00'), ('!disabled', '#FF9800'), ('disabled', '#ffcc80')],
              foreground=[('active', 'white'), ('!disabled', 'white'), ('disabled', '#ffffff')]
              )

    # New style Click Button
    style.configure("ClickButton.TButton",
                    font=('Segoe UI', 7, 'normal'),
                    padding=4,
                    relief="raised",
                    background="#d0eaff",
                    foreground="#003366",
                    borderwidth=1
                    )
    style.map("ClickButton.TButton",
              background=[('active', '#707070'), ('pressed', '#505050')],
              foreground=[('active', 'white'), ('pressed', 'white')],
              relief=[('pressed', 'sunken')]
              )

    # New style for "Add New Profile" and "Remove Current Profile" buttons
    style.configure("ActionButton.TButton",
                    font=('Segoe UI', 8, 'bold'),
                    padding=6,
                    relief="raised",
                    background="#a0a0a0",
                    foreground="black",
                    borderwidth=1
                    )
    style.map("ActionButton.TButton",
              background=[('active', '#707070'), ('pressed', '#505050'), ('!disabled', "#a0a0a0"), ('disabled', '#cccccc')],
              foreground=[('active', 'white'), ('pressed', 'white'), ('!disabled', 'black'), ('disabled', '#888888')],
              relief=[('pressed', 'sunken'), ('disabled', 'flat')]
              )

    # TEntry style
    style.configure("TEntry",
                    fieldbackground="white",
                    foreground="black",
                    relief="sunken"
                    )
    # Add disabled state for TEntry background
    style.map("TEntry",
              fieldbackground=[('disabled', '#e0e0e0')]
              )

    # TLabel style
    style.configure("TLabel",
                    background=bgcolor,
                    foreground="black"
                    )

    # Configure the TNotebook widget itself
    style.configure("TNotebook", background=bgcolor, borderwidth=0)
    style.layout("TNotebook", [("TNotebook.client", {"sticky": "nswe"})])

    # Configure the individual tabs within the TNotebook
    style.configure("TNotebook.Tab",
                    background=bgcolor,
                    foreground='black',
                    padding=[6, 3],
                    font=('Segoe UI', 9, 'bold'),
                    borderwidth=0,
                    relief="flat",
                    focuscolor="none"
                    )
    # Map colors for different states of a TNotebook.Tab
    style.map("TNotebook.Tab",
              background=[("selected", '#c9c9c9'), ("active", '#e0e0e0'), ("!disabled", bgcolor), ("disabled", '#f0f0f0')],
              foreground=[("selected", 'black'), ("active", 'black'), ("!disabled", 'black'), ("disabled", '#a0a0a0')]
              )

    return style
