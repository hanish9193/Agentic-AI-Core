import json
import os

store_path = os.path.join("backend", "database", "project_store.json")
with open(store_path, "r", encoding="utf-8") as f:
    data = json.load(f)

print("Root keys:", list(data.keys()))

projects = data.get("projects", [])
if projects:
    print("\nFirst Project:")
    print(json.dumps(projects[0], indent=2))

test_cases = data.get("test_cases", {})
if test_cases:
    first_tc_id = list(test_cases.keys())[0]
    print("\nFirst Test Case:")
    print(json.dumps(test_cases[first_tc_id], indent=2))
