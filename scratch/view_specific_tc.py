import json
import os

store_path = os.path.join("backend", "database", "project_store.json")
with open(store_path, "r", encoding="utf-8") as f:
    data = json.load(f)

test_cases = data.get("test_cases", {})
target_id = "ab3c07cb-5fde-4627-81ac-cf94c6d4d57e"
if target_id in test_cases:
    print(json.dumps(test_cases[target_id], indent=2))
else:
    print("Test case not found.")
