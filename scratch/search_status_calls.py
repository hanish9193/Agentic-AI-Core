with open('backend/playwrightt/app/page.tsx', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if '/api/status' in line:
        print(f"Line {idx+1}: {line.strip()}")
