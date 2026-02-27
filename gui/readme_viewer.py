# gui/readme_viewer.py
import os
import markdown
import webview
import multiprocessing

def _launch_readme_window(html_content):
    """
    Launch the webview in a dedicated process.
    Window size is set here: width=1000, height=800.
    """
    window = webview.create_window(
        "README - TAILSCALE VPN Client", 
        html=html_content, 
        width=800, 
        height=600,
        resizable=True
    )
    webview.start()

class ReadmeViewer:
    def __init__(self, parent=None):
        self.show_readme()

    def show_readme(self):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        path = os.path.join(base_dir, "README.md")
        
        if not os.path.exists(path):
            return

        with open(path, "r", encoding="utf-8") as f:
            md_content = f.read()

        html_body = markdown.markdown(md_content, extensions=["fenced_code", "tables"])

        # YOUR EXACT CSS + Added Fixed Close Button Styling
        full_html = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial;
                    margin: 40px;
                    margin-bottom: 100px; /* Space for button */
                    max-width: 900px;
                }}
                h1, h2, h3 {{ border-bottom: 1px solid #ddd; padding-bottom: 5px; }}
                pre {{ background: #f6f8fa; padding: 12px; border-radius: 6px; overflow-x: auto; }}
                code {{ background: #f6f8fa; padding: 3px 6px; border-radius: 4px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; }}
                
                /* Fixed Close Button Logic */
                .footer {{
                    position: fixed;
                    bottom: 0;
                    left: 0;
                    width: 100%;
                    background: white;
                    padding: 20px 0;
                    border-top: 1px solid #ddd;
                    text-align: center;
                }}
                .close-btn {{
                    background-color: #007acc;
                    color: white;
                    border: none;
                    padding: 10px 30px;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 14px;
                    font-family: sans-serif;
                }}
                .close-btn:hover {{ background-color: #005a9e; }}
            </style>
        </head>
        <body>
            {html_body}
            <div class="footer">
                <button class="close-btn" onclick="window.close()">Close README</button>
            </div>
        </body>
        </html>
        """

        p = multiprocessing.Process(target=_launch_readme_window, args=(full_html,))
        p.start()