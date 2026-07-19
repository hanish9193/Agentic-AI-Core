import json
import os

store_path = os.path.join("backend", "database", "project_store.json")

if os.path.exists(store_path):
    with open(store_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    projects = data.get("projects", [])
    for p in projects:
        print(f"Project: {p.get('id')} | Name: {p.get('name')}")
        print(f"  target_username: {p.get('target_username')}")
        print(f"  target_password_enc: {p.get('target_password_enc')}")
        print(f"  target_password: {p.get('target_password')}")
        print("-" * 50)
else:
    print("project_store.json not found.")
