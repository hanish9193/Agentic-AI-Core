import json
import os

store_path = os.path.join("backend", "database", "project_store.json")
with open(store_path, "r", encoding="utf-8") as f:
    data = json.load(f)

test_cases = data.get("test_cases", {})

# 1. No Location Selected
if "c414b552-5663-49aa-8829-5b7478a240a4" in test_cases:
    test_cases["c414b552-5663-49aa-8829-5b7478a240a4"]["scenario_id"] = "62abbeaa-adfa-4ea3-a5bd-b87ea1810c5b"
    print("Assigned valid scenario to No Location Selected testcase.")

# 2. Valid Credentials Login
if "9ffdd15a-a59d-43ab-a49c-1c4c4f697d51" in test_cases:
    test_cases["9ffdd15a-a59d-43ab-a49c-1c4c4f697d51"]["scenario_id"] = "2463fe31-8357-4b5f-b784-b679a961d6ce"
    print("Assigned valid scenario to Valid Credentials Login testcase.")

with open(store_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
print("Database updated and saved successfully.")
