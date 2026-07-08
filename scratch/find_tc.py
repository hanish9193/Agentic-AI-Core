import json
from pathlib import Path

store_path = Path("backend/database/project_store.json")
with open(store_path, "r", encoding="utf-8") as f:
    data = json.load(f)

test_cases = data.get("test_cases", {})
print("Number of test cases on disk:", len(test_cases))
print("Test case IDs on disk:", list(test_cases.keys()))

# Also check execution results test case IDs
execution_results = data.get("execution_results", {})
executed_tc_ids = set(ex.get("test_case_id") for ex in execution_results.values())
print("Test case IDs referenced in execution results:", executed_tc_ids)
