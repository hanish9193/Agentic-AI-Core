import json
import os

vault_path = os.path.join("backend", "database", "vault.json")
project_id = "b4c13430-f95f-4ea5-b0ed-a09a0b3b324c"

if os.path.exists(vault_path):
    with open(vault_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"Raw vault entry for {project_id}:")
    print(data.get(project_id))
else:
    print("vault.json not found")
