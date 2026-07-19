with open('frontend/js/app.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'nav-item' in line:
        print(f"Line {idx+1}: {line.strip()}")
