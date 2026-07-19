import json
import os
import psycopg2

tc_id = "c2bec44c-89f4-4334-956e-dc7bf2bcd37b"

# 1. Search in JSON
store_path = os.path.join("backend", "database", "project_store.json")
if os.path.exists(store_path):
    with open(store_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    test_cases = data.get("test_cases", {})
    if tc_id in test_cases:
        print(f"JSON: Found test case {tc_id}:")
        print(json.dumps(test_cases[tc_id], indent=2))
    else:
        print(f"JSON: Test case {tc_id} not found.")
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
    cur.execute("SELECT * FROM test_cases WHERE id = %s", (tc_id,))
    row = cur.fetchone()
    if row:
        print(f"PostgreSQL: Found test case {tc_id}: {row}")
    else:
        print(f"PostgreSQL: Test case {tc_id} not found.")
    cur.close()
    conn.close()
except Exception as e:
    print(f"PostgreSQL query failed: {e}")
