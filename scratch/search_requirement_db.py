with open('backend/database/db_models.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'class requirementdb' in line.lower():
        print(f"Line {idx+1}: {line.strip()}")
        # Print next 20 lines
        for j in range(1, 21):
            if idx + j < len(lines):
                print(f"  +{j}: {lines[idx+j].strip()}")
        break
