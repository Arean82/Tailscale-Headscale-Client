# gui/readme_viewer.py
import os
import markdown
import webview
import multiprocessing

class ReadmeAPI:
    """Official pywebview bridge to handle window destruction."""
    def __init__(self):
        self.window = None

    def close(self):
        if self.window:
            self.window.destroy()

def _launch_readme_window(html_content):
    api = ReadmeAPI()
    window = webview.create_window(
        "README - TAILSCALE VPN Client", 
        html=html_content, 
        js_api=api,
        width=800, 
        height=600
    )
    api.window = window
    webview.start()

class ReadmeViewer:
    def __init__(self, parent=None, theme="dark"):
        # If theme is "system", we need to resolve it
        if theme == "system":
            import customtkinter as ctk
            theme = ctk.get_appearance_mode().lower()
            
        self.show_readme(theme)

    def show_readme(self, theme):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        path = os.path.join(base_dir, "README.md")
        
        if not os.path.exists(path):
            return

        with open(path, "r", encoding="utf-8") as f:
            md_content = f.read()

        html_body = markdown.markdown(md_content, extensions=["fenced_code", "tables"])

        # Theme-specific colors
        if theme == "light":
            bg_color = "#ffffff"
            text_color = "#333333"
            header_color = "#000000"
            code_bg = "#f5f5f5"
            accent_color = "#007acc"
            border_color = "#dddddd"
            footer_bg = "#f0f0f0"
        else:
            bg_color = "#1a1a1a"
            text_color = "#e0e0e0"
            header_color = "#ffffff"
            code_bg = "#2d2d2d"
            accent_color = "#007acc"
            border_color = "#333333"
            footer_bg = "#252525"

        full_html = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                :root {{
                    --bg-color: {bg_color};
                    --text-color: {text_color};
                    --header-color: {header_color};
                    --code-bg: {code_bg};
                    --accent-color: {accent_color};
                    --border-color: {border_color};
                }}
                body {{
                    font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                    background-color: var(--bg-color);
                    color: var(--text-color);
                    line-height: 1.6;
                    margin: 0;
                    padding: 40px;
                    padding-bottom: 100px;
                    max-width: 800px;
                    margin-left: auto;
                    margin-right: auto;
                }}
                h1, h2, h3 {{ 
                    color: var(--header-color);
                    border-bottom: 1px solid var(--border-color); 
                    padding-bottom: 8px;
                    margin-top: 24px;
                }}
                pre {{ 
                    background: var(--code-bg); 
                    padding: 16px; 
                    border-radius: 8px; 
                    overflow-x: auto;
                    border: 1px solid var(--border-color);
                }}
                code {{ 
                    background: var(--code-bg); 
                    padding: 2px 6px; 
                    border-radius: 4px;
                    font-family: 'Consolas', monospace;
                }}
                table {{ 
                    border-collapse: collapse; 
                    width: 100%; 
                    margin: 20px 0;
                }}
                th, td {{ 
                    border: 1px solid var(--border-color); 
                    padding: 12px; 
                    text-align: left;
                }}
                th {{ background-color: {footer_bg}; }}
                blockquote {{
                    border-left: 4px solid var(--accent-color);
                    margin: 0;
                    padding-left: 20px;
                    color: #aaa;
                }}
                
                .footer {{
                    position: fixed;
                    bottom: 0;
                    left: 0;
                    width: 100%;
                    background: {footer_bg};
                    padding: 20px 0;
                    border-top: 1px solid var(--border-color);
                    text-align: center;
                    box-shadow: 0 -5px 15px rgba(0,0,0,0.3);
                }}
                .close-btn {{
                    background-color: var(--accent-color);
                    color: white;
                    border: none;
                    padding: 12px 40px;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 14px;
                    font-weight: 600;
                    transition: background 0.2s;
                }}
                .close-btn:hover {{ background-color: #005a9e; }}
            </style>
        </head>
        <body>
            <div class="content">
                {html_body}
            </div>
            <div class="footer">
                <button class="close-btn" onclick="pywebview.api.close()">Close README</button>
            </div>
        </body>
        </html>
        """

        p = multiprocessing.Process(target=_launch_readme_window, args=(full_html,))
        p.start()