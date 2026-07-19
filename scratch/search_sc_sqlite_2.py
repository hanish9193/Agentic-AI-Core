import os
import sqlite3

db_path = os.path.join("backend", "database", "local_fallback.db")
sc_id = "15c36f2d-4131-48af-bd68-cd1400ee0730"

if os.path.exists(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT * FROM scenarios WHERE id = ?", (sc_id,))
        row = cur.fetchone()
        if row:
            print(f"SQLite: Found scenario {sc_id}: {row}")
        else:
            print(f"SQLite: Scenario {sc_id} not found.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"SQLite query failed: {e}")
else:
    print("local_fallback.db does not exist.")
