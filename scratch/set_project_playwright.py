import json
import os

store_path = os.path.join("backend", "database", "project_store.json")
with open(store_path, "r", encoding="utf-8") as f:
    data = json.load(f)

projects = data.get("projects", [])
target_id = "9752881f-0f09-4a35-a904-61745f0e2768"

updated = False
for p in projects:
    if p.get("id") == target_id:
        p["framework"] = "playwright"
        updated = True
        print(f"Project '{p.get('name')}' framework updated to 'playwright'.")

if updated:
    with open(store_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print("Project store saved successfully.")
else:
    print(f"Project with ID {target_id} not found in store.")
