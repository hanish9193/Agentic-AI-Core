with open('backend/database/migrate_to_postgres.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'scenario_id' in line:
        print(f"Line {idx+1}: {line.strip()}")
