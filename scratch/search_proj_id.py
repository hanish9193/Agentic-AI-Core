with open('frontend/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'project-' in line.lower() or 'project_select' in line.lower():
        print(f"Line {idx+1}: {line.strip()}")
