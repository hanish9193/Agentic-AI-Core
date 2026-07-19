import json
import os

store_path = os.path.join("backend", "database", "project_store.json")
with open(store_path, "r", encoding="utf-8") as f:
    data = json.load(f)

def clean_nul_recursively(obj):
    if isinstance(obj, dict):
        return {k: clean_nul_recursively(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nul_recursively(item) for item in obj]
    elif isinstance(obj, str):
        return obj.replace("\u0000", "").replace("\x00", "")
    else:
        return obj

cleaned_data = clean_nul_recursively(data)

with open(store_path, "w", encoding="utf-8") as f:
    json.dump(cleaned_data, f, indent=2)

print("Database cleaned of all NUL characters successfully.")
