import json

with open("backend/database/project_store.json", "r", encoding="utf-8") as f:
    data = json.load(f)

scs = data.get("scenarios", {})
print(f"Total Scenarios: {len(scs)}")
for s_id, s in list(scs.items()):
    print(f"ID: {s_id}")
    print(f"  Name: {s.get('scenario_name')}")
    print(f"  Confidence: {s.get('confidence')}")
    print(f"  Priority: {s.get('priority')}")
