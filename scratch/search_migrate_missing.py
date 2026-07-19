with open('backend/database/migrate_to_postgres.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'releasedb' in line.lower() or 'testcycledb' in line.lower() or 'framework' in line.lower():
        print(f"Line {idx+1}: {line.strip()}")
