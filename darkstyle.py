# darkstyle.py
import tkinter.ttk as ttk

def setup_dark_styles(theme):
    bgcolor = theme.get("bgcolor", "#2e2e2e")  # dark gray
    fgcolor = theme.get("fgcolor", "white")

    style = ttk.Style()
    style.theme_use('default')

    # General TButton style
    style.configure("TButton",
                    font=('Segoe UI', 9, 'bold'),
                    padding=6,
                    relief="flat",
                    background=bgcolor,
                    foreground=fgcolor
                    )
    style.map("TButton",
              background=[('active', '#444444'), ('!disabled', bgcolor), ('disabled', '#555555')],
              foreground=[('active', fgcolor), ('!disabled', fgcolor), ('disabled', '#888888')]
              )

    # Connect Button (green-ish)
    style.configure("Connect.TButton", background='#4CAF50', foreground='white')
    style.map("Connect.TButton",
              background=[('active', '#45a049'), ('!disabled', '#4CAF50'), ('disabled', '#2e7d32')],
              foreground=[('active', 'white'), ('!disabled', 'white'), ('disabled', '#a5d6a7')]
              )

    # Disconnect Button (red-ish)
    style.configure("Disconnect.TButton", background='#f44336', foreground='white')
    style.map("Disconnect.TButton",
              background=[('active', '#da190b'), ('!disabled', '#f44336'), ('disabled', '#b71c1c')],
              foreground=[('active', 'white'), ('!disabled', 'white'), ('disabled', '#ef9a9a')]
              )

    # Logout Button (orange-ish)
    style.configure("Logout.TButton", background='#FF9800', foreground='white')
    style.map("Logout.TButton",
              background=[('active', '#fb8c00'), ('!disabled', '#FF9800'), ('disabled', '#ef6c00')],
              foreground=[('active', 'white'), ('!disabled', 'white'), ('disabled', '#ffcc80')]
              )

    # Click Button
    style.configure("ClickButton.TButton",
                    font=('Segoe UI', 7, 'normal'),
                    padding=4,
                    relief="raised",
                    background="#505050",
                    foreground="#ffffff",
                    borderwidth=1
                    )
    style.map("ClickButton.TButton",
              background=[('active', '#707070'), ('pressed', '#303030')],
              foreground=[('active', 'white'), ('pressed', 'white')],
              relief=[('pressed', 'sunken')]
              )

    # Action Button (for Add/Remove Profile)
    style.configure("ActionButton.TButton",
                    font=('Segoe UI', 8, 'bold'),
                    padding=6,
                    relief="raised",
                    background="#666666",
                    foreground="white",
                    borderwidth=1
                    )
    style.map("ActionButton.TButton",
              background=[('active', '#888888'), ('pressed', '#555555'), ('!disabled', "#666666"), ('disabled', '#444444')],
              foreground=[('active', 'white'), ('pressed', 'white'), ('!disabled', 'white'), ('disabled', '#999999')],
              relief=[('pressed', 'sunken'), ('disabled', 'flat')]
              )

    # Entry widget style
    style.configure("TEntry",
                    fieldbackground="#444444",
                    foreground="white",
                    relief="sunken"
                    )
    style.map("TEntry",
              fieldbackground=[('disabled', '#333333')]
              )

    # Label style
    style.configure("TLabel",
                    background=bgcolor,
                    foreground=fgcolor
                    )

    # Notebook style (tabs container)
    style.configure("TNotebook", background=bgcolor, borderwidth=0)
    style.layout("TNotebook", [("TNotebook.client", {"sticky": "nswe"})])

    # Notebook tabs style
    style.configure("TNotebook.Tab",
                    background=bgcolor,
                    foreground=fgcolor,
                    padding=[6, 3],
                    font=('Segoe UI', 9, 'bold'),
                    borderwidth=0,
                    relief="flat",
                    focuscolor="none"
                    )
    style.map("TNotebook.Tab",
              background=[("selected", '#505050'), ("active", '#606060'), ("!disabled", bgcolor), ("disabled", '#2e2e2e')],
              foreground=[("selected", fgcolor), ("active", fgcolor), ("!disabled", fgcolor), ("disabled", '#666666')]
              )

    return style
