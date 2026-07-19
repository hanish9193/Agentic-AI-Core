import os

app_js_path = os.path.join("frontend", "js", "app.js")

with open(app_js_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    # Search for tab switching or page switching logic
    if 'switchpage' in line.lower() or 'nav' in line.lower() or 'showtab' in line.lower() or 'click' in line.lower() and 'tab' in line.lower():
        print(f"Line {idx+1}: {line.strip()}")
        # Print surrounding context
        start = max(0, idx - 4)
        end = min(len(lines), idx + 8)
        for j in range(start, end):
            print(f"  {j+1}: {lines[j].strip()}")
        print("-" * 50)
