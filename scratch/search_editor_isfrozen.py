with open('backend/playwrightt/app/page.tsx', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'isfrozen' in line.lower():
        print(f"Line {idx+1}: {line.strip()}")
