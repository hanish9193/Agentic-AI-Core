import json
import os

store_path = os.path.join("backend", "database", "project_store.json")
with open(store_path, "r", encoding="utf-8") as f:
    data = json.load(f)

test_cases = data.get("test_cases", {})
target_id = "3cbdf0e8-9d67-40bb-a1d7-7858362bc436"

if target_id in test_cases:
    print("Found test case:")
    print(json.dumps(test_cases[target_id], indent=2))
else:
    print(f"Test case {target_id} NOT found in project_store.json.")
