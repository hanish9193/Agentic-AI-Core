import json
import os

store_path = os.path.join("backend", "database", "project_store.json")
with open(store_path, "r", encoding="utf-8") as f:
    data = json.load(f)

test_cases = data.get("test_cases", {})
print(f"Total test cases: {len(test_cases)}")
for tc_id, tc in test_cases.items():
    print(f"ID: {tc_id} | Project: {tc.get('project_id')} | Title: {tc.get('title')}")
