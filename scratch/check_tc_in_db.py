import json
import os

store_path = os.path.join("backend", "database", "project_store.json")
with open(store_path, "r", encoding="utf-8") as f:
    data = json.load(f)

test_cases = data.get("test_cases", {})
target_id = "c414b552-5663-49aa-8829-5b7478a240a4"
if target_id in test_cases:
    print(f"Test case {target_id} FOUND in project_store.json:")
    print(json.dumps(test_cases[target_id], indent=2))
else:
    print(f"Test case {target_id} NOT found in project_store.json.")
