import os

index_html_path = os.path.join("frontend", "index.html")

with open(index_html_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'view-panel' in line or 'id=' in line and 'view' in line:
        print(f"Line {idx+1}: {line.strip()}")
