import json

file_path = "backend/database/project_store.json"

with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

scs = data.get("scenarios", {})
migrated_count = 0

for s_id, s in scs.items():
    if s.get("confidence") == 0.0:
        s["confidence"] = 0.95
        migrated_count += 1

if migrated_count > 0:
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"Successfully migrated {migrated_count} scenarios to 0.95 confidence in {file_path}")
else:
    print("No scenarios needed migration.")
