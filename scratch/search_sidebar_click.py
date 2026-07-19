with open('frontend/js/app.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if 'sidebar-nav' in line or 'nav-item' in line or 'click' in line and 'item' in line:
        if idx > 3200:
            print(f"Line {idx+1}: {line.strip()}")
            # Print surrounding context
            start = max(0, idx - 4)
            end = min(len(lines), idx + 25)
            for j in range(start, end):
                print(f"  {j+1}: {lines[j].strip()}")
            print("-" * 50)
            break
