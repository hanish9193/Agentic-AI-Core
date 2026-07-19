import json
import os

store_path = os.path.join("backend", "database", "project_store.json")
with open(store_path, "r", encoding="utf-8") as f:
    data = json.load(f)

test_cases = data.get("test_cases", {})
for tc_id, tc in test_cases.items():
    if "Valid Credentials" in tc.get("title", ""):
        print(f"ID: {tc_id}")
        print(f"Title: {tc.get('title')}")
        print(f"Playwright Script:\n{tc.get('playwright_script')}")
        print("=" * 50)
