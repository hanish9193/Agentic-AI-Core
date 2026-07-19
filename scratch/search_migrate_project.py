with open('backend/database/migrate_to_postgres.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'projectdb' in line.lower():
        print(f"Line {idx+1}: {line.strip()}")
        # Print next 10 lines
        for j in range(1, 11):
            if idx + j < len(lines):
                print(f"  +{j}: {lines[idx+j].strip()}")
