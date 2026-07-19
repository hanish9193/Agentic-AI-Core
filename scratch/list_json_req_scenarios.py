import json
import os

req_id = "66362e04-5a1e-481e-9319-b616a3684967"
store_path = os.path.join("backend", "database", "project_store.json")

if os.path.exists(store_path):
    with open(store_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    scenarios = data.get("scenarios", {})
    count = 0
    print("Scenarios in JSON for Requirement:")
    print("=" * 80)
    for sc_id, sc in scenarios.items():
        if sc.get("requirement_id") == req_id:
            count += 1
            print(f"ID: {sc_id} | Name: {sc.get('scenario_name')}")
    print("=" * 80)
    print(f"Total in JSON: {count}")
else:
    print("project_store.json not found.")
