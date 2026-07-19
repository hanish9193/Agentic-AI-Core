with open('frontend/js/app.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'api/status' in line or 'status' in line:
        if 'fetch' in line or 'axios' in line or 'ajax' in line or 'url' in line:
            print(f"Line {idx+1}: {line.strip()}")
