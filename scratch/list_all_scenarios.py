import json
import os

store_path = os.path.join("backend", "database", "project_store.json")
with open(store_path, "r", encoding="utf-8") as f:
    data = json.load(f)

scenarios = data.get("scenarios", {})
print(f"Total scenarios: {len(scenarios)}")
for s_id, s in list(scenarios.items())[:30]:
    print(f"ID: {s_id} | Title: {s.get('scenario_name')}")
