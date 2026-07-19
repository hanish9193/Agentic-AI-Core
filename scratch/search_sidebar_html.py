import os

index_html_path = os.path.join("frontend", "index.html")

with open(index_html_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'sidebar-nav' in line or 'nav-item' in line:
        print(f"Line {idx+1}: {line.strip()}")
        # Print surrounding context
        start = max(0, idx - 2)
        end = min(len(lines), idx + 12)
        for j in range(start, end):
            print(f"  {j+1}: {lines[j].strip()}")
        print("-" * 50)
