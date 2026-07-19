with open('backend/database/db_models.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'execution' in line.lower() and 'class' in line.lower():
        print(f"Line {idx+1}: {line.strip()}")
