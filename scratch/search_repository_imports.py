with open('backend/repository/postgres_project_repository.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'import ' in line and 'TestCase' in line:
        print(f"Line {idx+1}: {line.strip()}")
