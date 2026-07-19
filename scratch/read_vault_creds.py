import json
import os

vault_path = os.path.join("backend", "database", "vault.json")
project_id = "b4c13430-f95f-4ea5-b0ed-a09a0b3b324c"

if os.path.exists(vault_path):
    try:
        with open(vault_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if project_id in data:
            print(f"Vault credentials for Project {project_id}:")
            print(json.dumps(data[project_id], indent=2))
        else:
            print(f"Project {project_id} not found in vault.json.")
            print("All projects in vault:", list(data.keys()))
    except Exception as e:
        print(f"Failed to read vault.json: {e}")
else:
    print("vault.json does not exist.")
