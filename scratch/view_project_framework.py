import json
import os

store_path = os.path.join("backend", "database", "project_store.json")
with open(store_path, "r", encoding="utf-8") as f:
    data = json.load(f)

projects = data.get("projects", [])
print(f"Total projects in store: {len(projects)}")

for p in projects:
    print(f"ID: {p.get('id')}")
    print(f"Name: {p.get('name')}")
    print(f"Framework: {p.get('framework')}")
    print("-" * 50)
