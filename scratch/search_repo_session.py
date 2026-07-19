with open('backend/repository/postgres_project_repository.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'self.session' in line or 'session =' in line or 'db_session' in line:
        if idx < 60:
            print(f"Line {idx+1}: {line.strip()}")
