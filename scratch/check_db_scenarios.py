import json
import os
import psycopg2

store_path = os.path.join("backend", "database", "project_store.json")
json_scenarios = {}
if os.path.exists(store_path):
    with open(store_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    json_scenarios = data.get("scenarios", {})
    print(f"JSON Scenarios Count: {len(json_scenarios)}")
else:
    print("project_store.json not found.")

try:
    conn = psycopg2.connect(
        host="127.0.0.1",
        port=5432,
        database="Agentic_ai",
        user="postgres",
        password="hanish13"
    )
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM scenarios")
    pg_count = cur.fetchone()[0]
    print(f"PostgreSQL Scenarios Count: {pg_count}")
    
    # Check if a specific scenario exists in PG
    test_scenario_id = "15c36f2d-4131-48af-bd68-cd1400ee0730"
    cur.execute("SELECT id, scenario_name, approved FROM scenarios WHERE id = %s", (test_scenario_id,))
    row = cur.fetchone()
    if row:
        print(f"Scenario {test_scenario_id} FOUND in PG: {row[1]}, Approved: {row[2]}")
    else:
        print(f"Scenario {test_scenario_id} NOT FOUND in PG.")
        
    cur.close()
    conn.close()
except Exception as e:
    print(f"PostgreSQL connection/query failed: {e}")
