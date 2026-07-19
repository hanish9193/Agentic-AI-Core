import json
import os

store_path = os.path.join("backend", "database", "project_store.json")
with open(store_path, "r", encoding="utf-8") as f:
    data = json.load(f)

test_cases = data.get("test_cases", {})
for tc_id, tc in test_cases.items():
    if "Invalid Password" in tc.get("title", "") or tc_id == "c414b552-5663-49aa-8829-5b7478a240a4":
        print(f"ID: {tc_id}")
        print(f"Title: {tc.get('title')}")
        print(f"Steps: {tc.get('steps')}")
        print(f"Expected Result: {tc.get('expected_result')}")
        print(f"Playwright Script:\n{tc.get('playwright_script')}")
        print("=" * 50)
