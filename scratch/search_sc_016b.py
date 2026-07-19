import json
import os
import psycopg2

sc_id = "016b1e9e-61d1-49d8-903b-6d1897b2e398"

# 1. Search in JSON
store_path = os.path.join("backend", "database", "project_store.json")
if os.path.exists(store_path):
    with open(store_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    scenarios = data.get("scenarios", {})
    if sc_id in scenarios:
        print(f"JSON: Found scenario {sc_id}:")
        print(json.dumps(scenarios[sc_id], indent=2))
    else:
        print(f"JSON: Scenario {sc_id} not found.")
else:
    print("JSON file not found.")

# 2. Search in PostgreSQL
try:
    conn = psycopg2.connect(
        host="127.0.0.1",
        port=5432,
        database="Agentic_ai",
        user="postgres",
        password="hanish13"
    )
    cur = conn.cursor()
    cur.execute("SELECT * FROM scenarios WHERE id = %s", (sc_id,))
    row = cur.fetchone()
    if row:
        print(f"PostgreSQL: Found scenario {sc_id}: {row}")
    else:
        print(f"PostgreSQL: Scenario {sc_id} not found.")
    cur.close()
    conn.close()
except Exception as e:
    print(f"PostgreSQL query failed: {e}")
