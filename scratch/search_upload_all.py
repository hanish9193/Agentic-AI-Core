with open('frontend/js/app.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'async upload' in line.lower() or 'upload' in line.lower() and 'function' in line.lower() or 'upload' in line.lower() and '(' in line.lower() and ')' in line.lower() and '{' in line.lower():
        if 'drop' not in line.lower() and 'btn' not in line.lower():
            print(f"Line {idx+1}: {line.strip()}")
