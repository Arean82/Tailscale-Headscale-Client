import sqlite3
import os

app_dir = os.path.join(os.environ.get('APPDATA', ''), "Tailscale_VPN_Client")
db_path = os.path.join(app_dir, "traffic_stats.db")

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM traffic_data ORDER BY id DESC LIMIT 5")
    rows = cursor.fetchall()
    print("Latest 5 records in traffic_data:")
    for row in rows:
        print(row)
    conn.close()
else:
    print(f"Database not found at {db_path}")
