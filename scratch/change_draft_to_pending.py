import json
import os
import psycopg2

# 1. Update project_store.json
store_path = os.path.join("backend", "database", "project_store.json")
if os.path.exists(store_path):
    with open(store_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    test_cases = data.get("test_cases", {})
    updated_json_count = 0
    for tc_id, tc in test_cases.items():
        if tc.get("evaluation_status") == "draft":
            tc["evaluation_status"] = "pending"
            updated_json_count += 1

    with open(store_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Updated {updated_json_count} test cases in project_store.json.")

# 2. Update PostgreSQL database
try:
    conn = psycopg2.connect(
        host="127.0.0.1",
        port=5432,
        database="Agentic_ai",
        user="postgres",
        password="hanish13"
    )
    cur = conn.cursor()
    cur.execute("UPDATE test_cases SET evaluation_status = 'pending' WHERE evaluation_status = 'draft'")
    updated_pg_count = cur.rowcount
    conn.commit()
    print(f"Updated {updated_pg_count} test cases in PostgreSQL 'Agentic_ai' database.")
    cur.close()
    conn.close()
except Exception as e:
    print(f"PostgreSQL update failed: {e}")
