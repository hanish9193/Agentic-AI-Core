with open('backend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'token' in line or 'login' in line or 'auth' in line:
        print(f"Line {idx+1}: {line.strip()}")
