import json

with open("backend/database/project_store.json", "r", encoding="utf-8") as f:
    data = json.load(f)

scenarios = data.get("scenarios", {})
target_id = "15c36f2d-4131-48af-bd68-cd1400ee0730"
if target_id in scenarios:
    print(f"Scenario {target_id} FOUND in JSON:")
    print(scenarios[target_id])
else:
    print(f"Scenario {target_id} NOT FOUND in JSON.")
