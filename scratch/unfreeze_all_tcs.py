import json
import os

store_path = os.path.join("backend", "database", "project_store.json")
with open(store_path, "r", encoding="utf-8") as f:
    data = json.load(f)

test_cases = data.get("test_cases", {})
print(f"Total test cases to unfreeze: {len(test_cases)}")

unfrozen_count = 0
for tc_id, tc in test_cases.items():
    # If it is approved or frozen, reset it to draft / unfrozen
    tc["is_frozen"] = False
    tc["evaluation_status"] = "draft"
    unfrozen_count += 1

with open(store_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print(f"Successfully unfrozen {unfrozen_count} test cases in the database.")
