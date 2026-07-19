import json
import os

store_path = os.path.join("backend", "database", "project_store.json")
with open(store_path, "r", encoding="utf-8") as f:
    data = json.load(f)

projects = data.get("projects", [])
found = False
for p in projects:
    if p.get("id") == "b4c13430-f95f-4ea5-b0ed-a09a0b3b324c":
        print("Found project:")
        print(json.dumps(p, indent=2))
        found = True
        break

if not found:
    print("Project not found in project_store.json")
