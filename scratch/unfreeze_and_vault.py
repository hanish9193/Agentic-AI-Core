import sys
import os
import json

# Add project root to sys.path so we can import backend packages
sys.path.append(os.getcwd())

from backend.services.vault_service import VaultService

# 1. Update Vault credentials
vs = VaultService()
target_projects = [
    "9752881f-0f09-4a35-a904-61745f0e2768",
    "b4c13430-f95f-4ea5-b0ed-a09a0b3b324c"
]

for pid in target_projects:
    vs.set_credentials(pid, "ADACTINFORQA", "3U0515")
    print(f"Vault updated for project: {pid} with new credentials (ADACTINFORQA / 3U0515).")

# 2. Update database project_store.json to unfreeze the editor
store_path = os.path.join("backend", "database", "project_store.json")
with open(store_path, "r", encoding="utf-8") as f:
    data = json.load(f)

test_cases = data.get("test_cases", {})
target_testcases = [
    "c414b552-5663-49aa-8829-5b7478a240a4", # No Location Selected
    "9ffdd15a-a59d-43ab-a49c-1c4c4f697d51", # Valid Credentials Login
    "ab3c07cb-5fde-4627-81ac-cf94c6d4d57e"  # Invalid Password Error
]

for tc_id in target_testcases:
    if tc_id in test_cases:
        tc = test_cases[tc_id]
        tc["is_frozen"] = False
        tc["evaluation_status"] = "draft"
        print(f"Unfrozen test case: {tc_id} ({tc.get('title')})")

with open(store_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print("Database project_store.json saved successfully.")
