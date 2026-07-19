with open('backend/database/migrate_to_postgres.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'def normalize_val' in line:
        print(f"Line {idx+1}: {line.strip()}")
        # Print next 15 lines
        for j in range(1, 16):
            if idx + j < len(lines):
                print(f"  +{j}: {lines[idx+j].strip()}")
