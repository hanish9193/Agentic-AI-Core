import json
import os

store_path = os.path.join("backend", "database", "project_store.json")
with open(store_path, "r", encoding="utf-8") as f:
    data = json.load(f)

scenarios = data.get("scenarios", {})
for s_id, s in scenarios.items():
    name = s.get("scenario_name", "").lower()
    if "search" in name or "location" in name:
        print(f"ID: {s_id} | Title: {s.get('scenario_name')}")
